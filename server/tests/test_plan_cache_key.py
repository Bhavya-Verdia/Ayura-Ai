"""The plan cache key is an allowlist, and it was missing most of what decides a plan.

`_check_plan_cache` hashes a hand-written dict of "relevant" profile fields. Its own
comment says a newly wired field is invisible until named there — and seven of the
eight profile edits that change a diet plan did not bust it:

    medical_history += diabetes      served the pre-diagnosis plan
    weight 70 -> 58 kg               target moves 2240 -> 2070, cache unchanged
    activity -> sedentary            target moves 2240 -> 1730, cache unchanged
    age 35 -> 17                     paediatric equation, cache unchanged
    gender -> other                  sex-neutral equation, cache unchanged
    agni -> manda                    whole brief changes, cache unchanged
    season -> grishma                Ritucharya changes, cache unchanged

`medical_history` is the single largest input to any plan this app makes, and it was
not in the key at all.
"""

import hashlib
import json

import pytest

from routes.plan_runner import _check_plan_cache
from services.panchakarma_engine import _menstruation_active


def _key(profile, prefs):
    """Rebuild the hash from the live source, so this test cannot drift from it."""
    import inspect

    src = inspect.getsource(_check_plan_cache)
    body = src[src.index("relevant_data = {"):src.index("pref_hash = hashlib")]
    loc = {"user_profile": profile, "feature_prefs": prefs,
           "_menstruation_active": _menstruation_active}
    exec(body, {"sorted": sorted, "str": str, "round": round, "float": float}, loc)
    return hashlib.sha256(
        json.dumps(loc["relevant_data"], sort_keys=True).encode()).hexdigest()


_BASE = {
    "dominant_dosha": "vata", "vikriti_dominant": "vata", "agni_type": "sama",
    "age": 35, "gender": "female", "height_cm": 162, "weight_kg": 70,
    "activity_level": "moderate", "bmi_category": "overweight",
    "medical_history": [], "current_season": "varsha", "allergies": [],
    "current_symptoms": [], "injuries_or_limitations": [],
}
_PREFS = {"dietary_type": "vegetarian", "diet_goal": "general_wellness",
          "gut_health_issue": "healthy"}


@pytest.mark.parametrize("label,delta", [
    ("a new diagnosis", {"medical_history": ["diabetes"]}),
    ("a second diagnosis", {"medical_history": ["diabetes", "hypertension"]}),
    ("a new medication", {"current_medications": ["metformin"]}),
    ("real weight loss", {"weight_kg": 58, "bmi_category": "normal"}),
    ("a desk job", {"activity_level": "sedentary"}),
    ("turning 18", {"age": 17}),
    ("sex recorded differently", {"gender": "other"}),
    ("height corrected", {"height_cm": 170}),
    ("Agni reassessed", {"agni_type": "manda"}),
    ("Ama appearing", {"ama_indicator": "high"}),
    ("Ojas dropping", {"ojas_level": "low"}),
    ("Koshtha recorded", {"koshtha": "krura"}),
    ("the season turning", {"current_season": "grishma"}),
    ("a new allergy", {"allergies": ["peanuts"]}),
    ("the goal changing", {"goal": "weight_loss"}),
])
def test_a_change_that_changes_the_plan_busts_the_cache(label, delta):
    assert _key({**_BASE, **delta}, _PREFS) != _key(_BASE, _PREFS), label


def test_feature_preferences_still_bust_it():
    assert _key(_BASE, {**_PREFS, "gut_health_issue": "acidity"}) != _key(_BASE, _PREFS)


def test_daily_weight_noise_does_not_bill_an_llm_call():
    """`weight_kg` is the one field a user changes daily. The energy target moves
    ~10-15 kcal per kilo — well inside the plan's own +/-10% acceptance band — so
    keying on the raw value regenerates every plan on every weigh-in for a difference
    nobody could see. It is bucketed to 2 kg, the same principle as
    `menstruation_active`: key on the state that changes the answer, not the reading.

    Bucketing has boundaries, so a sub-bucket change busts *sometimes*. What must hold
    is that it cannot bust more often than the bucket width implies.
    """
    busts = sum(
        _key({**_BASE, "weight_kg": 70 + d / 10}, _PREFS) != _key(_BASE, _PREFS)
        for d in range(0, 20)          # 70.0 .. 71.9 kg, in 100 g steps
    )
    assert busts <= 10, f"{busts}/20 sub-2kg readings busted the cache"
    # And an identical reading never busts.
    assert _key({**_BASE, "weight_kg": 70.0}, _PREFS) == _key(_BASE, _PREFS)


def test_a_real_weight_change_always_busts():
    for kg in (60, 65, 75, 80):
        assert _key({**_BASE, "weight_kg": kg}, _PREFS) != _key(_BASE, _PREFS), kg


def test_the_key_names_every_profile_field_the_diet_brief_reads():
    """The drift guard. `build_brief` and `energy_target` are where a profile field
    becomes part of the plan; anything they read and the key does not name is a stale
    plan waiting to be served."""
    import inspect

    from services import diet_brief_builder, diet_energy

    read = set()
    for mod in (diet_brief_builder, diet_energy):
        src = inspect.getsource(mod)
        import re
        read |= set(re.findall(r'user_profile\.get\("([a-z_]+)"\)', src))

    key_src = inspect.getsource(_check_plan_cache)
    # Fields deliberately absent, with the reason.
    exempt = {
        "name", "full_name",      # cosmetic — appears in the brief's header only
        "id", "_id",              # identity, not clinical state
        "weight_kg",              # present as `weight_bucket`
        "medical_history",        # present as `conditions`
        "activity_level",         # present as `activity`
        "pregnancy_or_nursing",   # present as `pregnancy`
        "dominant_dosha", "vikriti_dominant",   # present as `dosha` / `vikriti`
        "agni_type", "ama_indicator", "ojas_level",   # present as agni / ama / ojas
        "current_medications",    # present as `medications`
    }
    missing = sorted(f for f in read - exempt if f'"{f}"' not in key_src)
    assert not missing, (
        f"the diet path reads {missing} and the cache key does not name them — "
        f"a change to any of these serves the previous plan"
    )
