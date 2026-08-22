"""Panchakarma phase sequencing — the calendar and the card must be one plan.

Every phase used to be laid out by repeating pool[0] on each of its days. That
produced a schedule that contradicted the summary printed directly above it: a card
reading "Yoga Basti (8-Basti Schedule) — 3 Niruha + 5 Anuvasana" over a calendar
delivering 8 Niruha and 4 Anuvasana, and a staged Samsarjana Krama rendered as
eight identical days of its own name.

The assertions here are relationships, not fixed numbers, so retuning the phase
split or the load model cannot quietly falsify them.
"""
import pytest

from services.panchakarma_engine import (
    _basti_sequence,
    generate_panchakarma_plan,
    pk_protocols,
)

GOALS = ["detox", "rejuvenation", "stress_relief", "seasonal_cleanse", "specific_condition"]
DOSHAS = ["vata", "pitta", "kapha"]


def _profile(**over):
    base = dict(
        id="t", age=45, dominant_dosha="vata", vikriti_dominant="vata",
        fitness_level="intermediate", medical_history=[],
        ama_indicator="none", ojas_level="medium", digestion_quality="moderate",
    )
    base.update(over)
    return base


def _prefs(**over):
    base = dict(
        setting="clinic", available_time_days=21, detox_experience="experienced",
        access_to_ayurvedic_herbs="yes", diet_adherence_ability="strict",
        self_care_time_per_day="1 hour", panchakarma_goal="detox",
    )
    base.update(over)
    return base


def _phase_days(plan, needle):
    return [d for d in plan["daily_schedule"] if needle in d["phase"]]


# ── Basti ─────────────────────────────────────────────────────────────────────

def test_the_generated_basti_rule_reproduces_the_authored_schedule():
    """Yoga Basti's day-by-day pattern is authored in the KB; Kala and Karma Basti
    give totals only. Rather than hand-writing two more patterns, the rule is
    derived — and checked against the one pattern that IS authored, so the rule can
    never drift from the source it claims to generalise."""
    authored = pk_protocols["pradhana_karma"]["basti"]["subtypes"]["yoga_basti"]["schedule"]
    generated = _basti_sequence("yoga_basti", len(authored), pk_protocols)
    assert [s["type"] for s in generated] == [d["type"] for d in authored]


@pytest.mark.parametrize("subtype,total,niruha", [
    ("yoga_basti", 8, 3), ("kala_basti", 16, 6), ("karma_basti", 30, 12),
])
def test_each_basti_subtype_delivers_the_counts_it_advertises(subtype, total, niruha):
    """The KB states the split in each subtype's own description."""
    seq = _basti_sequence(subtype, total, pk_protocols)
    assert len(seq) == total
    assert sum(1 for s in seq if s["type"] == "niruha") == niruha


def test_a_basti_course_starts_and_ends_on_oil():
    """Anuvasana before and after Niruha is the classical safeguard: Niruha alone is
    Lekhana and Vata rises without the Sneha around it."""
    for subtype, total in [("yoga_basti", 8), ("kala_basti", 16), ("karma_basti", 30)]:
        seq = _basti_sequence(subtype, total, pk_protocols)
        assert seq[0]["type"] == "anuvasana"
        assert seq[-1]["type"] == "anuvasana"


def test_no_two_niruha_days_run_back_to_back():
    """Consecutive decoction enemas are the depleting pattern the alternation exists
    to prevent — and are exactly what repeating pool[0] produced, for as many days
    as the phase was long."""
    for subtype, total in [("yoga_basti", 8), ("kala_basti", 16), ("karma_basti", 30)]:
        seq = [s["type"] for s in _basti_sequence(subtype, total, pk_protocols)]
        assert not any(a == b == "niruha" for a, b in zip(seq, seq[1:])), f"{subtype}: {seq}"


def test_the_basti_card_and_the_basti_calendar_agree():
    """The card said "3 Niruha + 5 Anuvasana"; the calendar delivered 8 and 4."""
    plan = generate_panchakarma_plan(_profile(), _prefs())
    card = plan["clinical_decisions"]["basti_subtype"]
    assert card, "a Vata plan should reach Basti"

    days = _phase_days(plan, "Pradhana")
    assert card["days"] == len(days) == plan["phase_breakdown"]["pradhana_karma_days"]

    delivered_niruha = sum(
        1 for d in days for t in d["therapies"] if "Niruha" in t["name"]
    )
    claimed_niruha = int(card["note"].split()[0])
    assert delivered_niruha == claimed_niruha


def test_each_basti_day_names_its_own_procedure():
    """One pinned action repeated across the course told the patient nothing about
    which of the two procedures they were due on a given day."""
    plan = generate_panchakarma_plan(_profile(), _prefs())
    names = {t["name"] for d in _phase_days(plan, "Pradhana") for t in d["therapies"]}
    assert any("Niruha" in n for n in names)
    assert any("Anuvasana" in n for n in names)


# ── Samsarjana Krama ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("dosha", DOSHAS)
def test_every_samsarjana_stage_reaches_a_day(dosha):
    """The grading is the entire clinical content of Samsarjana Krama. The engine
    computed the stages and then scheduled a row named "Strict Samsarjana Krama"
    identically on every day of the phase — the one form that carries none of it."""
    plan = generate_panchakarma_plan(
        _profile(dominant_dosha=dosha, vikriti_dominant=dosha), _prefs())
    expected = {s["stage"] for s in plan["samsarjana_krama"]}
    if not expected:
        return
    delivered = {
        int(t["id"].rsplit("_", 1)[1])
        for d in plan["daily_schedule"] for t in d["therapies"]
        if t["id"].startswith("samsarjana_stage_")
    }
    assert delivered == expected


def test_the_samsarjana_stages_are_in_order():
    """Peya before Vilepi before Yusha. Agni is at its weakest immediately after
    Shodhana, and the order is what makes the ladder a ladder."""
    plan = generate_panchakarma_plan(_profile(dominant_dosha="pitta", vikriti_dominant="pitta"), _prefs())
    seen = [
        int(t["id"].rsplit("_", 1)[1])
        for d in plan["daily_schedule"] for t in d["therapies"]
        if t["id"].startswith("samsarjana_stage_")
    ]
    assert seen == sorted(seen)


def test_a_karma_that_empties_nothing_gets_no_re_entry_ladder():
    """Samsarjana Krama rekindles an Agni left weak by an emptied Koshtha. Nasya
    empties none, and the post-Virechana ladder used to be the catch-all — so a
    patient whose Virechana was withheld for low Ojas was handed a re-entry opening
    with "replaces fluids lost in purgation", for a purgation they had specifically
    not undergone, on a hypocaloric ladder, for depletion."""
    plan = generate_panchakarma_plan(_profile(dominant_dosha="pitta", vikriti_dominant="pitta",
                                              ojas_level="low"), _prefs())
    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] in {"nasya", "basti_matra"}
    text = " ".join(
        str(t.get("pradhana_notes", "")) + t["name"]
        for d in plan["daily_schedule"] for t in d["therapies"]
    ).lower()
    assert "purgation" not in text


# ── Purvakarma ────────────────────────────────────────────────────────────────

def test_purvakarma_is_snehana_and_swedana_every_day():
    """The phase is defined by the pair — Swedana opens the Srotas the oil has
    loosened. Taking pool[0] and pool[1] gave the two highest-scoring rows, which
    for a Vata patient were both Abhyanga: two oil massages and no sudation, in the
    phase whose definition is the pair."""
    plan = generate_panchakarma_plan(_profile(), _prefs())
    for day in _phase_days(plan, "Purvakarma"):
        names = " ".join(t["name"] for t in day["therapies"]).lower()
        assert "abhyanga" in names, f"day {day['day']} has no oleation"
        assert "steam" in names or "sweda" in names, f"day {day['day']} has no sudation"


def test_the_snehapana_dose_escalates_across_purvakarma():
    """The ladder runs 30 → 60 → 90 → 120ml and steps back on the last day. It lived
    in a summary block while every Purvakarma day on the calendar read the same, so
    the day a patient was on told them nothing about the dose they were due."""
    plan = generate_panchakarma_plan(_profile(), _prefs())
    doses = [d["snehapana"]["dose_ml"] for d in _phase_days(plan, "Purvakarma") if d.get("snehapana")]
    assert len(doses) >= 3
    assert doses[1] > doses[0], "the dose must escalate, not repeat"
    assert max(doses) >= doses[0] * 2


def test_the_time_budget_never_breaks_the_purvakarma_pair():
    """A 15-minute budget dropping Swedana leaves half a procedure — the same defect
    the pair exists to prevent, reintroduced by a preference filter."""
    for budget in ("15 min", "30 min", "1 hour", "2+ hours"):
        plan = generate_panchakarma_plan(
            _profile(), _prefs(setting="home", self_care_time_per_day=budget))
        for day in _phase_days(plan, "Purvakarma"):
            names = " ".join(t["name"] for t in day["therapies"]).lower()
            assert "abhyanga" in names and ("steam" in names or "sweda" in names), \
                f"{budget} broke the pair on day {day['day']}"


def test_the_time_budget_changes_what_a_day_contains():
    """`self_care_time_per_day` is "time available daily for therapies" and was
    applied per-therapy, so a 30-minute budget admitted four 15-minute therapies.
    Every self-care row is 15 minutes or less, so no budget ever excluded anything
    and the question could not change a plan whatever the answer."""
    def day_one(budget):
        plan = generate_panchakarma_plan(
            _profile(), _prefs(setting="home", self_care_time_per_day=budget))
        return len(plan["daily_schedule"][0]["therapies"])

    assert day_one("2+ hours") > day_one("15 min")


# ── Goal ──────────────────────────────────────────────────────────────────────

def test_each_goal_produces_a_different_plan():
    """`panchakarma_goal` was offered in the UI, validated by the schema, echoed
    into `user_summary`, and read by no engine code."""
    import hashlib
    import json

    signatures = {}
    for goal in GOALS:
        plan = generate_panchakarma_plan(
            _profile(dominant_dosha="pitta", vikriti_dominant="pitta"), _prefs(panchakarma_goal=goal))
        plan.pop("plan_id", None)
        plan.pop("generated_at", None)
        blob = json.dumps(plan, sort_keys=True, default=str)
        signatures.setdefault(hashlib.md5(blob.encode()).hexdigest(), []).append(goal)

    collisions = [g for g in signatures.values() if len(g) > 1]
    assert not collisions, f"goals producing identical plans: {collisions}"


def test_stress_relief_leads_with_the_manovaha_therapies():
    """Shirodhara is Murdha Taila and the therapy for Manovaha Srotas; Udvartana is
    Ruksha and raises Vata, which is what an anxious Manas least needs."""
    plan = generate_panchakarma_plan(
        _profile(dominant_dosha="pitta", vikriti_dominant="pitta"),
        _prefs(panchakarma_goal="stress_relief"))
    names = " ".join(
        t["name"] for d in plan["daily_schedule"] for t in d["therapies"]).lower()
    assert "shirodhara" in names

    baseline = generate_panchakarma_plan(
        _profile(dominant_dosha="pitta", vikriti_dominant="pitta"),
        _prefs(panchakarma_goal="detox"))
    def count(p, needle):
        return sum(needle in t["name"].lower()
                   for d in p["daily_schedule"] for t in d["therapies"])
    assert count(plan, "shirodhara") > count(baseline, "shirodhara")


def test_a_seasonal_cleanse_follows_the_ritu_not_the_vikriti():
    """That is what a seasonal cleanse means — Doshas accumulate on a seasonal cycle
    and are expelled on one. Any other goal keeps the Vikriti mapping."""
    profile = _profile(dominant_dosha="pitta", vikriti_dominant="pitta")
    seasonal = generate_panchakarma_plan(profile, _prefs(panchakarma_goal="seasonal_cleanse"))
    vikriti = generate_panchakarma_plan(profile, _prefs(panchakarma_goal="detox"))

    ritu_karma = seasonal["clinical_decisions"]["ritu_context"].get("primary_shodhana")
    chosen = seasonal["clinical_decisions"]["pradhana_karma_selected"]["primary"]

    # Either it took the season's Karma, or it explained why it could not.
    if chosen != ritu_karma:
        notes = " ".join(seasonal["clinical_decisions"]["goal"]["notes"]).lower()
        assert "home form" in notes or chosen != vikriti["clinical_decisions"]["pradhana_karma_selected"]["primary"]


def test_a_seasonal_cleanse_at_home_is_not_scheduled_for_bloodletting():
    """Grishma's seasonal indication is Raktamokshana, which has no home form. A goal
    must not become the reason a home user is scheduled for leech therapy."""
    import unittest.mock as mock

    import services.panchakarma_engine as engine

    with mock.patch.object(engine, "_current_ritu", lambda: "grishma"):
        plan = engine.generate_panchakarma_plan(
            _profile(dominant_dosha="pitta", vikriti_dominant="pitta"),
            _prefs(setting="home", panchakarma_goal="seasonal_cleanse"))
    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] != "raktamokshana"
    text = " ".join(
        t["name"] for d in plan["daily_schedule"] for t in d["therapies"]).lower()
    assert "raktamokshana" not in text and "bloodletting" not in text


def test_the_goal_never_overrides_a_safety_gate():
    """A goal is a preference. It reorders what is already allowed; it cannot
    reinstate what a contraindication removed."""
    for goal in GOALS:
        plan = generate_panchakarma_plan(
            _profile(age=78, ama_indicator="high", medical_history=["anemia"]),
            _prefs(panchakarma_goal=goal))
        assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "shamana"
        assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] is None


# ── Whole-plan consistency ────────────────────────────────────────────────────

@pytest.mark.parametrize("days", [3, 5, 7, 10, 14, 21])
@pytest.mark.parametrize("dosha", DOSHAS)
@pytest.mark.parametrize("setting", ["home", "clinic"])
def test_the_phase_strip_and_the_calendar_are_the_same_plan(days, dosha, setting):
    plan = generate_panchakarma_plan(
        _profile(dominant_dosha=dosha, vikriti_dominant=dosha),
        _prefs(available_time_days=days, setting=setting))
    pb = plan["phase_breakdown"]

    assert sum(p["days"] for p in pb["phases"]) == pb["total_days"]
    assert len(plan["daily_schedule"]) == pb["total_days"]
    assert [d["day"] for d in plan["daily_schedule"]] == list(range(1, pb["total_days"] + 1))
    assert all(d["therapies"] for d in plan["daily_schedule"])
    if pb["total_days"] != days:
        assert pb["duration_notice"], f"{days}d silently became {pb['total_days']}d"


# ── Snehana adequacy ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("dosha", DOSHAS)
@pytest.mark.parametrize("days", [5, 7, 10, 14, 21])
def test_the_snehapana_ladder_always_climbs_then_steps_down(dosha, days):
    """The KB's day 7 reads "Reduce dose on final day" — 120ml halved to 60. Slicing
    the first N entries of the seven-day ladder dropped that step for every shorter
    course, handing the patient from a climbing dose straight into the Karma."""
    plan = generate_panchakarma_plan(
        _profile(dominant_dosha=dosha, vikriti_dominant=dosha),
        _prefs(available_time_days=days))
    doses = [d["snehapana"]["dose_ml"] for d in plan["daily_schedule"] if d.get("snehapana")]
    if len(doses) < 2:
        return
    assert doses[1] > doses[0], f"{doses} does not escalate"
    if len(doses) >= 3:
        assert doses[-1] < max(doses), f"{doses} has no final-day reduction"
        # A two-day course has no plateau to step down from; forcing one there
        # flattened the ladder to 30ml twice, which is not oleation at all.
        assert len(set(doses)) > 1


def test_a_short_snehana_says_so_and_says_what_to_do_about_it():
    """Snehapana is titrated to Samyak Snigdha lakshana, not to a day count.
    `purvakarma_classical_snehana_days` reported the classical figure as a bare
    number beside a phase half its length — a card reading 7 above a 2-day
    schedule — and inadequate Snehana before Shodhana is the textbook cause of
    post-Shodhana complications."""
    plan = generate_panchakarma_plan(_profile(), _prefs(available_time_days=7))
    adequacy = plan["snehana_protocol"]["adequacy"]

    assert adequacy["truncated"] is True
    assert adequacy["scheduled_days"] < adequacy["classical_days"]
    assert adequacy["signs"], "the signs are what the patient judges by"
    assert str(adequacy["classical_days"]) in adequacy["instruction"]
    assert any("SNEHANA SHORTER THAN CLASSICAL" in w
               for w in plan["clinical_decisions"]["safety_warnings"])


def test_a_full_length_snehana_still_points_at_the_signs():
    """Even at classical length the calendar is not the criterion."""
    plan = generate_panchakarma_plan(_profile(), _prefs(available_time_days=21))
    adequacy = plan["snehana_protocol"]["adequacy"]
    assert adequacy["truncated"] is False
    assert "signs" in adequacy["instruction"].lower()
    assert adequacy["signs"]
