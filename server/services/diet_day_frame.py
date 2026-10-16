"""The day around the meals: when to eat, the wake-up and bedtime drinks, the spice
guide and the dosha tips.

These were fixed tables keyed by dosha alone, and nothing screened them. Every Vata
patient was told to drink golden milk at bedtime — the vegan and the dairy-allergic
included — and every Kapha patient to start the day with honey, ginger and lemon,
the diabetic, the Jain and the acidity patient included, on the same screen as meals
that had been screened food by food. The spice guide recommended hing to coeliacs and
fenugreek seed in pregnancy. And the meal times were the dosha's, whatever eating
window the patient had declared: a 16:8 answer reached the model as "adjust meal
timing accordingly", in a plan with no field for a time, beside a 7 AM breakfast and
a bedtime milk.

Now each drink, spice and tip names the food ids it stands for, and is shown only if
every one of them is on the patient's screened food list (`diet_allowed_foods`) — the
same list the meals are composed from, so the card and the plate cannot disagree. A
drink that fails falls to the next candidate; a spice or tip that fails is withheld
with its reason. The drinks are counted into every day's nutrition, because a glass
of milk at bedtime is ~100 kcal the day totals did not include.

Authored, not clinically reviewed.
"""
from __future__ import annotations

from services import diet_nutrition as dn

# ── Eating windows ───────────────────────────────────────────────────────────
# (opens, closes, {slot: time}). The window closes early in the evening because
# Ayurveda's own advice is an early, light dinner; a 16:8 that ran noon to eight
# would put the largest gap across the morning, when Agni is meant to be fed.
_WINDOWS = {
    "12:12": ("7:30 AM", "7:30 PM", {
        "breakfast": "7:30–8:30 AM",
        "lunch": "12:30–1:30 PM — the main meal",
        "snack": "4:00–4:30 PM",
        "dinner": "6:30–7:30 PM — finish by 7:30",
    }),
    "14:10": ("9:00 AM", "7:00 PM", {
        "breakfast": "9:00–9:30 AM — your first meal",
        "lunch": "1:00–1:30 PM — the main meal",
        "snack": "4:00–4:30 PM",
        "dinner": "6:15–7:00 PM — finish by 7:00",
    }),
    "16:8": ("10:00 AM", "6:00 PM", {
        "breakfast": "10:00–10:30 AM — your first meal",
        "lunch": "1:00–1:30 PM — the main meal",
        "snack": "3:30–4:00 PM",
        "dinner": "5:30–6:00 PM — finish by 6:00",
    }),
}
# A twelve-hour overnight gap is an ordinary night, not a fast; only the longer
# windows are withheld from the groups that are not fasted.
_ORDINARY_WINDOW = "12:12"

_DOSHA_TIMES = {
    "vata": {
        "breakfast": "7:00–8:00 AM — warm, cooked; before Vata peaks at 10 AM",
        "lunch": "12:00–1:00 PM — largest meal at solar peak",
        "snack": "4:00–5:00 PM — small nourishing snack before Vata's evening rise",
        "dinner": "6:30–7:30 PM — warm, light; at least 2 hrs before sleep",
        "general_note": "Regularity is the single most important Vata prescription. "
                        "Eat at the same time every day.",
    },
    "pitta": {
        "breakfast": "7:30–8:30 AM — moderate, cooling breakfast",
        "lunch": "12:00–1:00 PM — substantial; Pitta digestion peaks at midday",
        "snack": "3:00–4:00 PM — small and cooling",
        "dinner": "7:00–8:00 PM — light, early; prevents overnight heat buildup",
        "general_note": "Never skip lunch — Pitta Agni is strongest and must be fed at midday.",
    },
    "kapha": {
        "breakfast": "8:00–9:00 AM — light; only as much as you are hungry for",
        "lunch": "12:30–1:30 PM — main meal; spiced, warm, light grains and legumes",
        "snack": "4:00–5:00 PM — small, or skip it if you are not hungry",
        "dinner": "6:00–7:00 PM — very light, early; nothing heavy after dark",
        "general_note": "Less is more for Kapha. Never eat out of boredom or habit.",
    },
}

# ── Drinks ───────────────────────────────────────────────────────────────────
# Candidates in order of preference; the first whose every component is on the
# patient's screened list is given. `kind` marks what a rule other than the screen
# reads: "milk" is never added to a kidney plan (protein and phosphorus, as the
# mineral sides), and a "sweet" one is not given to a diabetic, whose brief asks for
# no honey or dried fruit even where the classical texts allow Madhu.
def _drink(name, recipe, components, kind=()):
    return {"name": name, "recipe": recipe, "components": components, "kind": set(kind)}


_WATER = [{"food": "water", "grams": 250}]

_WAKE_UP = {
    "vata": [
        _drink("Warm cumin water", "A glass of warm water with a pinch of roasted cumin, sipped slowly.",
               [*_WATER, {"food": "cumin_jeera", "grams": 1}]),
        _drink("Warm water with dry ginger", "A pinch of dry ginger (saunth) stirred into warm water.",
               [*_WATER, {"food": "ginger_dry_saunth", "grams": 1}]),
    ],
    "pitta": [
        _drink("Water with soaked raisins", "Ten raisins soaked overnight; drink the water and eat the raisins.",
               [*_WATER, {"food": "raisins", "grams": 10}], ("sweet",)),
        _drink("Coriander-seed water", "A teaspoon of coriander seeds soaked overnight, strained.",
               [*_WATER, {"food": "coriander_dhania", "grams": 2}]),
    ],
    "kapha": [
        _drink("Warm water with honey, ginger and lemon",
               "Grated ginger and a squeeze of lemon in warm — never hot — water; honey stirred in "
               "once it has cooled to drinking warmth.",
               [*_WATER, {"food": "honey", "grams": 7}, {"food": "ginger", "grams": 3},
                {"food": "lemon_juice", "grams": 5}], ("sweet",)),
        _drink("Warm water with dry ginger", "A pinch of dry ginger (saunth) stirred into warm water.",
               [*_WATER, {"food": "ginger_dry_saunth", "grams": 1}]),
    ],
}
_PLAIN_WATER = _drink("Warm water", "A glass of warm water, sipped slowly.", _WATER)

_MILK_SPICES = {
    "vata": ([{"food": "turmeric", "grams": 1}, {"food": "cardamom_elaichi", "grams": 0.5}],
             "with turmeric and cardamom", "Warmed with a pinch of turmeric and cardamom."),
    "pitta": ([{"food": "cardamom_elaichi", "grams": 0.5}, {"food": "fennel_saunf", "grams": 1}],
              "with cardamom and fennel",
              "Boiled with cardamom and fennel, then left to cool to room temperature."),
}


def _milk_drinks(dosha: str) -> list[dict]:
    spices, phrase, recipe = _MILK_SPICES[dosha]
    adj = "Warm" if dosha == "vata" else "Cool"
    return [_drink(f"{adj} {label} {phrase}", recipe,
                   [{"food": fid, "grams": 150}, *spices], ("milk",))
            for fid, label in (("milk_full_fat", "milk"), ("soy_milk", "soy milk"),
                               ("almond_milk", "almond milk"), ("oat_milk", "oat milk"))]


_BEDTIME = {
    "vata": _milk_drinks("vata"),
    "pitta": [*_milk_drinks("pitta"),
              _drink("Fennel water", "A teaspoon of fennel seeds steeped in warm water, strained.",
                     [{"food": "water", "grams": 200}, {"food": "fennel_saunf", "grams": 2}])],
    "kapha": [
        _drink("Dry ginger and cinnamon tea", "Dry ginger and a little cinnamon simmered in water; "
               "no milk, no sugar.",
               [{"food": "water", "grams": 200}, {"food": "ginger_dry_saunth", "grams": 1},
                {"food": "cinnamon_dalchini", "grams": 0.5}]),
        _drink("Tulsi tea", "A cup of tulsi tea, no milk or sugar.", [{"food": "tulsi_tea", "grams": 200}]),
    ],
}

_SWEET = {"honey", "jaggery", "dates", "raisins", "figs"}

# ── Spice guide ──────────────────────────────────────────────────────────────
# `use` names no food but the spice: "in warm milk or chai" was the line a vegan read.
_SPICES = {
    "vata": [
        ("Ginger", "Ardraka", "ginger", "Fresh, grated into cooked meals and warm drinks — kindles Agni, warms Vata"),
        ("Cumin", "Jeeraka", "cumin_jeera", "Toasted, in dal and rice — grounds Vata, aids digestion"),
        ("Cardamom", "Ela", "cardamom_elaichi", "In warm drinks and sweets — eases bloating, calms the mind"),
        ("Ajwain", "Yavani", "ajwain", "In the tadka for dals and vegetables — a strong carminative for Vata bloating"),
        ("Asafoetida", "Hingu", "hing", "A tiny pinch in the tadka — prevents Vata gas; the most important Vata spice"),
    ],
    "pitta": [
        ("Coriander", "Dhanyaka", "coriander_dhania", "Fresh or as seed — the best Pitta-pacifying spice; use liberally"),
        ("Fennel", "Shatapushpa", "fennel_saunf", "After meals, or steeped as a light infusion — cooling, aids digestion"),
        ("Cardamom", "Ela", "cardamom_elaichi", "In cooling drinks and desserts — sweet, cooling"),
        ("Turmeric", "Haridra", "turmeric", "In all cooking — anti-inflammatory; use moderately (mildly heating)"),
        ("Saffron", "Kumkuma", None, "A few strands in a warm drink — cooling and nourishing"),
    ],
    "kapha": [
        ("Black Pepper", "Maricha", "black_pepper", "In all meals — stimulates sluggish Kapha Agni, burns Ama"),
        ("Dry Ginger", "Shunthi", "ginger_dry_saunth", "Powder in food and warm drinks — Kapha's number-one spice"),
        ("Turmeric", "Haridra", "turmeric", "Generous amounts — reduces Kapha mucus and inflammation"),
        ("Cinnamon", "Tvak", "cinnamon_dalchini", "In warm drinks and porridge — warms and stimulates Kapha metabolism"),
        ("Fenugreek", "Methika", "fenugreek_seeds_methi", "Seeds soaked or sprouted, in dal — the best Kapha fat-burning seed"),
    ],
}
_HING_GLUTEN = ("Use a hing labelled gluten-free: most hing sold in India is compounded "
                "with wheat flour.")

# ── Tips ─────────────────────────────────────────────────────────────────────
# Each sentence with the foods it recommends; a sentence with alternatives takes the
# first whose foods are all allowed, and a sentence that only says what to avoid
# names nothing to check.
_TIPS = {
    "vata": [
        [("Favour warm, cooked, oily and grounding foods.", ())],
        [("Use ghee generously.", ("ghee",)), ("Use sesame oil generously.", ("sesame_oil",))],
        [("Eat at consistent times — regularity is the single most important Vata prescription.", ())],
        [("Avoid cold drinks, raw salads and dry snacks.", ())],
    ],
    "pitta": [
        [("Favour cooling, mildly spiced, lightly sweet foods.", ())],
        [("Include coconut, coriander and fennel liberally.", ("coconut", "coriander_dhania", "fennel_saunf")),
         ("Include coriander and fennel liberally.", ("coriander_dhania", "fennel_saunf"))],
        [("Never skip lunch — your Agni is strongest at midday.", ())],
        [("Avoid excess chilli, garlic, onion, vinegar and fermented foods.", ())],
    ],
    "kapha": [
        [("Favour light, warm, pungent and spiced foods.", ())],
        [("Prefer a little honey over sugar.", ("honey",))],
        [("Keep breakfast light if you are not genuinely hungry.", ())],
        [("Avoid heavy dairy, cold foods, sweets, and eating after 7 PM.", ())],
    ],
}


# ── Rules ────────────────────────────────────────────────────────────────────

def if_window(user_profile: dict, diet_prefs: dict) -> tuple[str | None, str | None]:
    """(the eating window that applies, why a declared one does not)."""
    from services.diet_brief_builder import eating_window_withheld_reason, no_fasting_group

    w = (diet_prefs or {}).get("intermittent_fasting") or "no"
    if w not in _WINDOWS:
        return None, None
    # A child is given no window at all, as the brief says, not even an ordinary one:
    # a plan that showed "your 12:12 window" beside "no fasting" would contradict itself.
    if w == _ORDINARY_WINDOW and no_fasting_group(user_profile, diet_prefs) != "child":
        return w, None
    why = eating_window_withheld_reason(user_profile, diet_prefs)
    if why:
        return None, (f"Your {w} eating window is not applied: {why}. Meals are at ordinary "
                      "times, with a normal overnight gap.")
    return w, None


def window_brief_line(user_profile: dict, diet_prefs: dict) -> str:
    """The eating window as the model is told it: the hours and each meal's time, or
    that the declared window is withheld and why."""
    window, notice = if_window(user_profile, diet_prefs)
    if not window:
        return f"NO EATING WINDOW: {notice} Keep regular meal times every day."
    opens, closes, slots = _WINDOWS[window]
    times = "; ".join(f"{s} {t.split(' — ')[0]}" for s, t in slots.items())
    return (f"EATING WINDOW {window}: every meal and snack between {opens} and {closes} "
            f"({times}). Nothing with calories outside it — the daily drink is taken inside "
            f"the window, and dinner is the last thing eaten.")


def _ok(components, allowed_ids: set) -> bool:
    return all(c["food"] in allowed_ids for c in components)


def _pick_drink(candidates, allowed_ids, *, diabetic, renal, zero_kcal
                ) -> tuple[dict | None, list[dict]]:
    """(the first candidate this patient may have, the ones before it the food
    screen removed). Candidates passed over for another rule — a diabetic's honey,
    a kidney plan's milk, a calorie inside a fasting window — are not reported as
    withheld: nothing about the patient's food list ruled them out."""
    screened_out = []
    for d in candidates:
        if not _ok(d["components"], allowed_ids):
            screened_out.append(d)
            continue
        if diabetic and ("sweet" in d["kind"] or _SWEET & {c["food"] for c in d["components"]}):
            continue
        if renal and "milk" in d["kind"]:
            continue
        if zero_kcal and _kcal(d) >= 5:
            continue
        return d, screened_out
    return None, screened_out


def _kcal(drink: dict) -> float:
    return float(dn.compute(drink["components"])["nutrition"].get("calories") or 0)


def _ritual(slot: str, when: str, drink: dict) -> dict:
    meal = {"slot": slot, "name": drink["name"], "when": when, "recipe": drink["recipe"],
            "components": [dict(c) for c in drink["components"]]}
    return dn.apply_to_meal(meal)


def _gluten_free(user_profile, diet_prefs) -> bool:
    from services.diet_brief_builder import diet_allergies, diet_conditions

    return ("gluten" in {str(a).lower() for a in diet_allergies(user_profile, diet_prefs)}
            or any(c in ("celiac", "coeliac", "celiac_disease")
                   for c in diet_conditions(user_profile, diet_prefs)))


def day_frame(user_profile: dict, diet_prefs: dict, allowed_ids: set, energy: dict,
              excluded: dict | None = None) -> dict:
    """{meal_timing, rituals, spice_guide, ayurvedic_tips, withheld_guidance}."""
    dosha = (user_profile.get("dominant_dosha") or "vata").lower()
    dosha = dosha if dosha in _DOSHA_TIMES else "vata"
    excluded = excluded or {}
    nt = energy.get("nutrient_targets") or {}
    diabetic = (nt.get("added_sugar_g") or {}).get("max") == 0
    renal = bool((nt.get("protein_g") or {}).get("max"))
    window, window_notice = if_window(user_profile, diet_prefs)
    withheld: list[dict] = []

    def why(ids) -> str:
        return next((excluded[i] for i in ids if i in excluded), "not on your food list")

    # Meal times.
    timing = dict(_DOSHA_TIMES[dosha])
    if window:
        opens, closes, slots = _WINDOWS[window]
        timing.update(slots)
        timing["eating_window"] = f"{opens} – {closes}"
        timing["general_note"] = (
            f"Your {window} eating window: everything is eaten between {opens} and {closes}. "
            f"Outside it, water only — the wake-up drink below has no calories, so it does "
            f"not break the overnight fast. {_DOSHA_TIMES[dosha]['general_note']}")
    if window_notice:
        timing["window_notice"] = window_notice

    # Drinks.
    rituals = []

    def report(screened_out):
        for d in screened_out:
            ids = [c["food"] for c in d["components"] if c["food"] not in allowed_ids]
            withheld.append({"item": d["name"], "source": "daily drinks", "reason": why(ids)})

    wake, out = _pick_drink(_WAKE_UP[dosha], allowed_ids, diabetic=diabetic, renal=renal,
                            zero_kcal=bool(window))
    report(out)
    wake = wake or _PLAIN_WATER
    rituals.append(_ritual("wake_up", "On waking, before anything else", wake))
    timing["wake_up_drink"] = f"{wake['name']} — {wake['recipe']}"
    timing["bedtime_drink"] = None
    if window:
        timing["after_window"] = f"Nothing but water after {_WINDOWS[window][1]}."
    else:
        bed, out = _pick_drink(_BEDTIME[dosha], allowed_ids, diabetic=diabetic, renal=renal,
                               zero_kcal=False)
        report(out)
        if bed:
            rituals.append(_ritual("bedtime", "About an hour before sleep", bed))
            timing["bedtime_drink"] = f"{bed['name']} — {bed['recipe']}"

    # Spices.
    spices = []
    gluten_free = _gluten_free(user_profile, diet_prefs)
    for name, sanskrit, fid, use in _SPICES[dosha]:
        if fid and fid not in allowed_ids:
            withheld.append({"item": name, "source": "spice guide", "reason": why([fid])})
            continue
        row = {"name": name, "sanskrit": sanskrit, "use": use}
        if fid == "hing" and gluten_free:
            row["note"] = _HING_GLUTEN
        spices.append(row)

    # Tips.
    sentences = []
    for options in _TIPS[dosha]:
        chosen = next((s for s, ids in options
                       if all(i in allowed_ids for i in ids)
                       and not (diabetic and _SWEET & set(ids))), None)
        if chosen:
            sentences.append(chosen)
            continue
        s, ids = options[0]
        withheld.append({"item": s, "source": "dosha tips",
                         "reason": ("no added sweeteners with diabetes"
                                    if diabetic and _SWEET & set(ids) else why(ids))})

    return {"meal_timing": timing, "rituals": rituals, "spice_guide": spices,
            "ayurvedic_tips": " ".join(sentences), "withheld_guidance": withheld,
            "eating_window": window}


def ritual_totals(rituals: list[dict]) -> dict:
    """The drinks' nutrition, summed — added to every day's totals."""
    tot: dict = {}
    for r in rituals or []:
        for k, v in (r.get("macros_approx") or {}).items():
            if isinstance(v, (int, float)):
                tot[k] = tot.get(k, 0.0) + float(v)
    return tot
