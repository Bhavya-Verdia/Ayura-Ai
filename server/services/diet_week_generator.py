"""The LLM diet plan, generated week by week from the patient's own food list.

What this replaces, measured on sixteen live persona plans:

* One 16k-token call returned all four weeks, and only week 1 in full — weeks 2-4
  were meal names, so 21 of 28 days had no portion and no nutrition at all.
* About one call in five came back without its `weeks` array and the WHOLE plan
  fell to the rule engine, which missed the protein floor on 26 of 28 days.
* Every number was the model's estimate, written to fit the budget.
* Meals that broke the patient's own constraints shipped with a note on them.

Now: four week calls and one overview call run in parallel. Each week is full detail
— every meal a list of COMPONENTS from the patient's screened food list, with grams —
validated on arrival and retried alone if it fails. Nutrition is computed from the
components (`diet_nutrition`). Every meal is scanned, and a meal a scan flags is
rewritten by one targeted repair call or, failing that, replaced with a safe meal
composed from the allowed list. Portions are then scaled to the day's energy target,
and the text follows the grams.
"""
from __future__ import annotations

import asyncio
import json
import math
import random
from datetime import datetime, timezone

from ai.llm_client import llm_client
from core.logger import logger
from services import diet_nutrition as dn

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
SLOTS = ("breakfast", "lunch", "snack", "dinner")
DRINK = "special_drink"
_WEEK_TOKENS = 12000
_OVERVIEW_TOKENS = 3000
_REPAIR_TOKENS = 6000
# A day is scaled toward target only within these bounds; past them it is short of
# FOOD, not of portion, and is reported rather than inflated.
_MIN_FACTOR, _MAX_FACTOR = 0.7, 1.45

SYSTEM_PROMPT = """\
You are a senior Vaidya (BAMS, MD Ayurveda) working with a registered dietitian. You \
write precise, home-cookable Indian vegetarian meal plans for one patient.

Non-negotiable:
1. Every meal and drink is built ONLY from the food ids in the patient's ALLOWED FOODS \
list, as `components` with grams. Grams are of the food in the state its row states \
([cooked] rice, [dry] flour, ...). Seasonings in the list may be used in small amounts.
2. Never name a food in a meal name or description that is not among its components.
3. Size portions so each meal lands near its kcal budget, using the per-100 g figures \
given. The app computes the nutrition from your grams — do not state calories.
4. Real dish names a home cook recognises, and variety: no dish more than twice a week.
5. Every meal has a short Ayurvedic rationale (Rasa, Guna, Virya, Vipaka) for this patient.
6. Respect the therapeutic phase of the week, the patient's Agni and every condition.

Respond ONLY with valid JSON. No markdown, no commentary."""

_MEAL_SHAPE = ('{"meal_name": "string", "description": "one sentence: what it is and how it '
               'is made", "components": [{"food": "allowed food id", "grams": 0}], '
               '"ayurvedic_note": "1-2 sentences"}')
_DRINK_SHAPE = ('{"name": "string", "when": "string", "recipe": "one sentence", '
                '"rationale": "string", "components": [{"food": "allowed food id", "grams": 0}]}')

WEEK_PROMPT = """\
{brief}

ALLOWED FOODS for this patient (id — name [state] kcal and protein per 100 g). Use no other food:
{foods}

Write WEEK {week} of the plan. Therapeutic phase: "{phase}".
This week's staples, so the four weeks differ: {staples}.{fasting}

Per-meal kcal budget: breakfast ~{b} | lunch ~{l} | snack ~{s} | dinner ~{d}. \
Protein at least {protein} g per day. Carbohydrate about {carbs} g per day. Fat about \
{fat} g per day in total — ghee or oil 1-2 tsp (5-10 g) per main meal, not more.{carb_rule}
Salt: list it as a component ("salt", grams) in every savoury meal — about {salt_g} g a day \
in all; the plan's sodium is counted from it.{micro_rule}
Real portions: at most 2 katori (300 g) of cooked rice or grain, or 3 roti, per meal; at most \
2 katori of any one vegetable; at most 40 g nuts. For a high energy target, use denser foods \
(roti, paratha, poha, paneer or tofu, a glass of milk or plant milk, nuts) — never a mountain of rice.

Return exactly:
{{"week_number": {week}, "phase_description": "1-2 sentences on this week's focus",
 "days": {{"Monday": {{"theme": "2-3 words", "breakfast": {meal}, "lunch": {meal}, "snack": {meal},
  "dinner": {meal}, "special_drink": {drink}}}, "Tuesday": {{...}}, "Wednesday": {{...}},
  "Thursday": {{...}}, "Friday": {{...}}, "Saturday": {{...}}, "Sunday": {{...}}}}}}
All seven days, every slot filled."""

OVERVIEW_PROMPT = """\
{brief}

ALLOWED FOODS for this patient: {food_names}

Write the plan's guidance. Recommend only foods from the allowed list.
Return exactly:
{{"plan_title": "personalised title", "plan_description": "2-3 sentences: clinical rationale",
 "pathya_apathya": {{"pathya": ["allowed food — 1 sentence reason"], "apathya": ["food or practice to avoid — reason"],
  "viruddha_ahara_warnings": ["combination — classical reason"], "classical_reference": "string"}},
 "condition_coaching": "2-3 sentences specific to the conditions",
 "hydration_guidance": "string", "fasting_guidance": "string or empty",
 "seasonal_note": "string or empty", "ahar_vidhi": "2-3 eating rules for this Agni and Dosha",
 "motivational_note": "1 sentence"}}"""

REPAIR_PROMPT = """\
{brief}

ALLOWED FOODS for this patient (use no other):
{foods}

These meals broke a rule for this patient. Rewrite each one, same slot and similar kcal,
using only allowed foods. Reasons are given.
{items}

Return exactly: {{"meals": [{{"key": "the key given", "meal": {meal}}}]}}
For a special_drink key, "meal" has the drink shape: {drink}"""


# ── LLM plumbing ─────────────────────────────────────────────────────────────

async def _ask(prompt: str, max_tokens: int, validate, attempts: int = 2):
    """One prompt, parsed and validated; retried once on any failure."""
    last = None
    for attempt in range(attempts):
        try:
            raw = await llm_client.generate(prompt=prompt, system_prompt=SYSTEM_PROMPT,
                                            json_mode=True, max_tokens=max_tokens)
            data = json.loads(raw)
            return validate(data)
        except Exception as e:  # noqa: BLE001 — logged, retried, then reported
            last = e
            logger.warning(f"diet week generation attempt {attempt + 1} failed: {e}")
    raise RuntimeError(f"diet generation failed after {attempts} attempts: {last}")


def _canon_day(name) -> str | None:
    key = str(name or "").strip().lower()[:3]
    return next((d for d in DAYS if d.lower()[:3] == key), None)


def _validate_week(week_no: int):
    def check(data):
        if isinstance(data, dict) and "days" not in data:
            # Some providers wrap the object; unwrap one level before failing.
            inner = next((v for v in data.values() if isinstance(v, dict) and "days" in v), None)
            data = inner or data
        days_in = (data or {}).get("days")
        if not isinstance(days_in, dict):
            raise ValueError("week has no 'days' object")
        days = {}
        for name, day in days_in.items():
            canon = _canon_day(name)
            if canon and isinstance(day, dict):
                days[canon] = day
        missing = [d for d in DAYS if d not in days]
        if missing:
            raise ValueError(f"week {week_no} missing {missing}")
        for d, day in days.items():
            for slot in SLOTS:
                meal = day.get(slot)
                if not isinstance(meal, dict) or not dn.components_of(meal):
                    raise ValueError(f"week {week_no} {d} {slot} has no components")
        return {"week_number": week_no,
                "phase_description": str(data.get("phase_description") or ""),
                "days": days}
    return check


def _validate_repair(data):
    if not isinstance(data, dict) or not isinstance(data.get("meals"), list):
        raise ValueError("repair returned no meals")
    return data


def _validate_overview(data):
    if not isinstance(data, dict) or not data.get("plan_title"):
        raise ValueError("overview missing plan_title")
    return data


# ── Variety ──────────────────────────────────────────────────────────────────

def _salt_budget(energy: dict) -> str:
    limit = ((energy.get("nutrient_targets") or {}).get("sodium_mg") or {}).get("max") or 2000
    # Foods themselves carry roughly 400 mg; the rest is the cook's salt (~388 mg/g).
    return f"{max(1.5, round((limit - 400) / 388, 1))}"


def _micro_rule(energy: dict) -> str:
    """Where the day's iron, calcium and folate come from, for the groups whose need
    a plain plate misses: pregnancy, anaemia-prone women and girls, and the old."""
    nt = energy.get("nutrient_targets") or {}
    iron, calcium = (nt.get("iron_mg") or {}).get("min"), (nt.get("calcium_mg") or {}).get("min")
    bits = []
    if iron and iron >= 27:
        bits.append(f"iron about {iron} mg a day: ragi, bajra, poha, greens (methi, palak, "
                    "drumstick leaves), dates, jaggery in place of sugar, sesame; a vitamin C "
                    "food (amla, guava, lemon) at the same meal; no tea within an hour")
    if calcium and calcium >= 1000:
        bits.append(f"calcium about {calcium} mg a day: ragi, milk, curd, paneer, sesame, "
                    "methi leaves")
    return ("\nMINERALS — " + "; ".join(bits) + ".") if bits else ""


def _carb_rule(energy: dict) -> str:
    """The plate rules portion scaling cannot reach afterwards. A day built on rice
    and dal is carbohydrate in both, and a vegetarian day's protein comes from its
    grains and vegetables as well as its dal — only the composition changes either."""
    nt = energy.get("nutrient_targets") or {}
    rules = ""
    p_max = (nt.get("protein_g") or {}).get("max")
    if p_max:
        rules += (f"\nKIDNEY PLATE: protein at most {p_max} g for the whole day. Dal or other "
                  "pulse at most one small katori (100 g cooked) per day in total; no paneer, "
                  "tofu, soya or sprouts; energy from grains, low-potassium vegetables and "
                  "2-3 tsp ghee or oil per main meal (fat carries the energy protein cannot).")
    if (nt.get("added_sugar_g") or {}).get("max") != 0:
        return rules
    return rules + ("\nDIABETES PLATE: per main meal at most 1 katori (150 g) cooked grain or 2 "
            "phulka, with a protein food (dal, paneer, tofu, curd, sprouts) and at least "
            "1 katori of non-starchy vegetable; no sweet fruit at dinner; snacks protein- "
            "or nut-based rather than fruit alone. No sugar, jaggery, honey or dried fruit.")


def _staples(allowed: list[dict], week: int) -> str:
    """Two grains and two pulses featured per week, rotated through the allowed list,
    so four weeks generated in parallel do not all centre on the same khichdi."""
    # Everyday Indian staples first, in the order a household rotates them; the
    # unfamiliar grains and pulses come after, as occasional extras. Alphabetical
    # order put quinoa and amaranth at the centre of whole weeks.
    familiar = ["roti_whole_wheat", "basmati_rice", "millet_jowar", "brown_rice", "poha",
                "millet_bajra", "daliya", "ragi_flour", "oats", "upma_rava", "idli",
                "white_rice", "barley", "paratha", "dosa", "jowar_flour", "bajra_flour",
                "moong_dal_yellow", "toor_dal", "masoor_dal", "chana_dal", "moong_dal_green",
                "rajma", "chhole", "urad_dal", "paneer", "black_eyed_peas", "green_peas",
                "sprouted_moong", "tofu_firm", "soy_milk", "soya_chunks"]
    rank = {fid: i for i, fid in enumerate(familiar)}
    key = lambda f: (rank.get(f["id"], 100), f["id"])  # noqa: E731
    grains = sorted((f for f in allowed if dn.role(f["id"]) == "grain"), key=key)
    pulses = sorted((f for f in allowed if f.get("category") in ("legume", "vegan_protein")
                     or f["id"] == "paneer"), key=key)

    def pick(rows, n):
        if not rows:
            return []
        start = ((week - 1) * n) % len(rows)
        return [rows[(start + i) % len(rows)] for i in range(min(n, len(rows)))]
    names = [f"{f['id']} ({dn._short(f.get('name') or f['id'])})"
             for f in pick(grains, 2) + pick(pulses, 2)]
    return ", ".join(names) or "any allowed grains and pulses"


# ── Assembly, scanning and repair ────────────────────────────────────────────

def _finish_meal(meal: dict) -> dict:
    meal = dict(meal)
    comps = dn.components_of(meal)
    meal["components"] = comps
    return dn.apply_to_meal(meal)


def _off_list(meal: dict, allowed_ids: set) -> list[str]:
    return [c["food"] for c in dn.components_of(meal) if c["food"] not in allowed_ids]


def _units(weeks: list[dict]):
    for w in weeks:
        for d in DAYS:
            day = w["daily_plan"].get(d)
            if not isinstance(day, dict):
                continue
            for slot in SLOTS + (DRINK,):
                if isinstance(day.get(slot), dict):
                    yield w["week_number"], d, slot, day


def _scan(plan: dict, allergies, intolerances, dietary_type, conditions, extra_terms,
          pregnant) -> dict[tuple, list[str]]:
    """{(week, day, slot): [reasons]} from the same three scans the plan ships with."""
    from services.ahara_safety import (apply_ahara_safety, apply_condition_food_safety,
                                       apply_dietary_type_safety)
    probe = {"diet_weeks": json.loads(json.dumps(plan["diet_weeks"]))}
    probe = apply_ahara_safety(probe, allergies, intolerances)
    probe = apply_dietary_type_safety(probe, dietary_type)
    probe = apply_condition_food_safety(probe, conditions, extra_terms=extra_terms,
                                        pregnant=pregnant)
    found: dict[tuple, list[str]] = {}
    for key in ("safety_alerts", "dietary_type_alerts", "condition_safety_alerts",
                "viruddha_ahara_detected"):
        for a in probe.get(key) or []:
            wk = str(a.get("week", "")).replace("Week ", "")
            try:
                k = (int(wk), a.get("day"), a.get("meal_slot"))
            except ValueError:
                continue
            found.setdefault(k, []).append(a.get("message") or key)
    return found


def _safe_meal(slot: str, allowed: list[dict], budget: int, rng: random.Random) -> dict:
    """A plain, safe meal composed from the allowed list — the last resort when a
    flagged meal cannot be repaired. Plain on purpose: it is correct, not inspired."""
    by = {}
    for f in allowed:
        by.setdefault(f.get("category"), []).append(f)

    def one(cat, grams):
        rows = by.get(cat) or []
        return {"food": rng.choice(rows)["id"], "grams": grams} if rows else None

    if slot == DRINK:
        parts = [one("beverage", 200) or {"food": "water", "grams": 250}]
        drink = {"name": dn._short(dn.name_of(parts[0]["food"])), "when": "Mid-morning",
                 "recipe": "Served warm.", "rationale": "A simple drink from your allowed list.",
                 "components": parts}
        return _finish_meal(drink)
    if slot == "snack":
        parts = [one("fruit", 120), one("nut_seed", 15)]
    elif slot == "breakfast":
        parts = [one("grain", 180), one("fruit", 100), one("nut_seed", 10)]
    else:
        parts = [one("grain", 180), one("legume", 150), one("vegetable", 150),
                 one("oil", 5), {"food": "salt", "grams": _COOK_SALT_G}]
    parts = [p for p in parts if p]
    meal = {"meal_name": " with ".join(dn._short(dn.name_of(p["food"])) for p in parts[:3]),
            "description": "A simple plate built from your allowed foods.",
            "ayurvedic_note": "Chosen from foods screened for your conditions and allergies.",
            "components": parts, "substituted": True}
    meal = _finish_meal(meal)
    kcal = meal["macros_approx"]["calories"] or 1
    if budget:
        meal["components"] = dn.scale(meal["components"], max(0.5, min(2.0, budget / kcal)))
        meal = _finish_meal(meal)
    return meal


def _slot_kcal(meal) -> float:
    return float(((meal or {}).get("macros_approx") or {}).get("calories") or 0)


def _fixed(meal: dict, c: dict) -> bool:
    """A side added for a mineral keeps the portion it was added at. The solver
    trimmed a glass of milk to 130 ml and ragi malt to 13 g along with the rest of
    the plate, taking back most of what it was added for."""
    return c["food"] in (meal.get("mineral_sides") or ())


def _rescale(meal: dict, factor: float) -> None:
    comps = dn.components_of(meal)
    fixed = [c for c in comps if _fixed(meal, c)]
    meal["components"] = dn.scale([c for c in comps if not _fixed(meal, c)], factor) + fixed
    _finish_meal_inplace(meal)


_COUNTED = SLOTS + (DRINK,)

# How far each kind of component may move from what the model wrote. Grains and
# protein foods are where a cook adjusts a plate; added fat and sweet things move
# down more freely than up; seasonings never move.
_ROLE_BOUNDS = {
    "grain": (0.5, 1.6), "protein": (0.6, 2.0), "vegetable": (0.6, 1.6),
    "fruit": (0.6, 1.5), "sweet_fruit": (0.4, 1.3), "nut": (0.5, 1.6),
    "fat": (0.3, 1.3), "sweet": (0.0, 1.0), "drink": (0.7, 1.3), "other": (0.8, 1.2),
    "fixed": (1.0, 1.0),
}
_NUTRIENTS = ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g")


def _role_matrix(day: dict) -> dict:
    """{role: {nutrient: amount}} — what each kind of component contributes today."""
    out: dict = {}
    for s in _COUNTED:
        meal = day.get(s) or {}
        for c in meal.get("components") or []:
            r = "fixed" if _fixed(meal, c) else dn.role(c["food"])
            if r == "seasoning":
                continue
            per = (dn.food(c["food"]) or {}).get("nutrition_per_100g") or {}
            row = out.setdefault(r if r in _ROLE_BOUNDS else "other", dict.fromkeys(_NUTRIENTS, 0.0))
            for k in _NUTRIENTS:
                row[k] += float(per.get(k) or 0) * c["grams"] / 100
    return out


def _objective(x: dict, A: dict, energy: dict, diabetic: bool) -> float:
    tot = dict.fromkeys(_NUTRIENTS, 0.0)
    for r, row in A.items():
        for k in _NUTRIENTS:
            tot[k] += row[k] * x[r]
    nt = energy.get("nutrient_targets") or {}
    T = energy["target_calories"]
    p_floor = energy.get("protein_floor_g") or 1
    p_target = energy.get("protein_target_g") or p_floor
    c_t = (nt.get("carbs_g") or {}).get("target") or tot["carbs_g"] or 1
    f_t = (nt.get("fat_g") or {}).get("target") or tot["fat_g"] or 1
    err = (tot["calories"] - T) / T
    # Inside the band, energy is one target among several; outside it the day has
    # failed, and that must outweigh keeping every portion where the model put it.
    cost = 12 * err ** 2 + 150 * max(0.0, abs(err) - 0.08) ** 2
    cost += 18 * max(0.0, (p_floor - tot["protein_g"]) / p_floor) ** 2
    cost += 1 * ((tot["protein_g"] - p_target) / p_target) ** 2
    p_max = (nt.get("protein_g") or {}).get("max")
    if p_max:
        # A ceiling, not a preference: kidney disease (KDIGO 2020).
        cost += 20 * max(0.0, (tot["protein_g"] - p_max) / p_max) ** 2
    if diabetic:
        # AVAILABLE carbohydrate — total less fibre — is what reaches the blood. A
        # diabetic day of moong, millet and vegetables carried 71 g of fibre and read
        # as 16% over target on total carbohydrate; penalising that pushes a plan
        # toward refined grain, which is the opposite of the advice (ADA 2024).
        available = tot["carbs_g"] - tot["fiber_g"]
        cost += 8 * max(0.0, (available - c_t) / c_t) ** 2
    else:
        cost += 2 * max(0.0, abs(tot["carbs_g"] - c_t) / c_t - 0.15) ** 2
    cost += 3 * max(0.0, (tot["fat_g"] - f_t) / f_t - 0.10) ** 2
    # Fibre minimum. A constipated 78-year-old's day came to 18.5 g against 25.
    fib_min = (nt.get("fibre_g") or {}).get("min")
    if fib_min:
        cost += 4 * max(0.0, (fib_min - tot["fiber_g"]) / fib_min) ** 2
    cost += 1 * max(0.0, (f_t - tot["fat_g"]) / f_t - 0.25) ** 2
    cost += 0.2 * sum((v - 1) ** 2 for v in x.values())
    return cost


def _cap_scale(energy: dict) -> float:
    return energy["target_calories"] / 2200.0


def _role_ceilings(day: dict, scale: float = 1.0) -> dict:
    """The largest factor each role can take before some meal's portion of one of its
    foods passes `meal_cap` — a plate a person would actually be served."""
    out: dict = {}
    for s in _COUNTED:
        meal = day.get(s) or {}
        for c in meal.get("components") or []:
            r = dn.role(c["food"])
            if r == "seasoning" or not c["grams"] or _fixed(meal, c):
                continue
            r = r if r in _ROLE_BOUNDS else "other"
            out[r] = min(out.get(r, 9.9), dn.meal_cap(c["food"], scale) / c["grams"])
    return out


def _clip_to_caps(day: dict, scale: float = 1.0) -> bool:
    clipped = False
    for s in _COUNTED:
        meal = day.get(s)
        if not isinstance(meal, dict):
            continue
        changed = False
        for c in meal.get("components") or []:
            cap = dn.meal_cap(c["food"], scale)
            if dn.role(c["food"]) != "seasoning" and not _fixed(meal, c) and c["grams"] > cap:
                c["grams"] = cap
                changed = True
        if changed:
            _finish_meal_inplace(meal)
            clipped = True
    return clipped


def _optimise_factors(A: dict, energy: dict, diabetic: bool, ceilings: dict | None = None) -> dict:
    """Projected gradient descent over one factor per role. Nine variables at most,
    so a few hundred finite-difference steps settle in milliseconds."""
    x = {r: 1.0 for r in A}
    bounds = dict(_ROLE_BOUNDS)
    if ((energy.get("nutrient_targets") or {}).get("protein_g") or {}).get("max"):
        # Under a protein ceiling the protein foods may come well down and the
        # energy they carried is made up in fat, as a renal diet does.
        bounds.update(protein=(0.3, 1.2), fat=(0.3, 2.2), grain=(0.5, 1.4))
    for r, cap in (ceilings or {}).items():
        lo, hi = bounds.get(r, (0.8, 1.2))
        # A portion already over the cap may come down to it; nothing goes up past it.
        bounds[r] = (min(lo, cap), max(min(hi, cap), min(lo, cap)))
    step, h = 0.05, 1e-4

    def project(v: dict) -> dict:
        return {r: min(bounds.get(r, (0.8, 1.2))[1], max(bounds.get(r, (0.8, 1.2))[0], v[r]))
                for r in v}

    cost = _objective(x, A, energy, diabetic)
    for _ in range(300):
        grad = {}
        for r in x:
            x[r] += h
            grad[r] = (_objective(x, A, energy, diabetic) - cost) / h
            x[r] -= h
        # Backtracking: a step is taken only if it lowers the cost. With the steep
        # out-of-band term a fixed step overshot to 3866 kcal on a 2160 target.
        while step > 1e-5:
            cand = project({r: x[r] - step * grad[r] for r in x})
            c = _objective(cand, A, energy, diabetic)
            if c < cost - 1e-9:
                x, cost = cand, c
                step *= 1.5
                break
            step /= 2
        else:
            break
    return x


def _apply_factors(day: dict, x: dict) -> None:
    for s in _COUNTED:
        meal = day.get(s)
        if not isinstance(meal, dict) or not meal.get("components"):
            continue
        for c in meal["components"]:
            r = dn.role(c["food"])
            if r == "seasoning" or _fixed(meal, c):
                continue
            f = x.get(r if r in _ROLE_BOUNDS else "other", 1.0)
            g = c["grams"] * f
            step = 1 if g < 20 else 5
            c["grams"] = max(1, round(g / step) * step) if f > 0 else 0
        meal["components"] = [c for c in meal["components"] if c["grams"] > 0]
        _finish_meal_inplace(meal)


_FASTING_SHARE = 0.6


def _fasting_energy(energy: dict) -> dict:
    t = int(round(energy["target_calories"] * _FASTING_SHARE))
    nt = dict(energy.get("nutrient_targets") or {})
    if nt.get("fat_g"):
        nt["fat_g"] = {**nt["fat_g"], "target": round(nt["fat_g"]["target"] * _FASTING_SHARE)}
    if nt.get("carbs_g"):
        nt["carbs_g"] = {**nt["carbs_g"], "target": round(nt["carbs_g"]["target"] * _FASTING_SHARE)}
    # The band is asymmetric (30-70%): a Phalahar day under 60% is a stricter fast, not a
    # failure; over 70% it is no longer a fasting day.
    full = energy["target_calories"]
    return {**energy, "target_calories": t,
            "band": (int(full * 0.30), int(full * 0.70)),
            "protein_floor_g": round((energy.get("protein_floor_g") or 0) * _FASTING_SHARE),
            "protein_target_g": round((energy.get("protein_target_g") or 0) * _FASTING_SHARE),
            "meal_budget": {k: round(v * _FASTING_SHARE) for k, v in energy["meal_budget"].items()},
            "nutrient_targets": nt}


def _reconcile_day(day: dict, energy: dict) -> dict:
    """Bring the day to its targets: each meal toward its own budget first, then one
    factor per kind of food, solved for energy, protein, carbohydrate and fat together.

    The model composes to a kcal budget and lets the macros fall where they fall — a
    diabetic's day reached 339 g of carbohydrate against 230, days ran under the
    protein floor, and one day was 41% fat. Moving grams between the grain, the dal
    and the ghee on the same plate is how a dietitian corrects that; the dishes are
    unchanged. Fasting days are exempt: Upavasa is the therapy."""
    before = _day_totals(day)["calories"]
    if not before:
        return {"factor": 1.0, "before": 0, "after": 0}
    if day.get("is_fasting"):
        # Upavasa is the therapy, so a fasting day is held LIGHT rather than exempt:
        # exempt, a "fasting" Monday came to 1955 kcal and 144 g of fat from
        # coconut-milk bowls. About 60% of the day's energy, the same macro rules.
        energy = _fasting_energy(energy)
    budget = energy["meal_budget"]
    for s in SLOTS:
        meal, kcal = day.get(s), _slot_kcal(day.get(s))
        if isinstance(meal, dict) and kcal and budget.get(s):
            f = max(0.6, min(1.6, budget[s] / kcal))
            if abs(f - 1) > 0.08:
                _rescale(meal, f)
    diabetic = ((energy.get("nutrient_targets") or {}).get("added_sugar_g") or {}).get("max") == 0
    factors = {}
    for _ in range(3):
        scale = _cap_scale(energy)
        step_factors = _optimise_factors(_role_matrix(day), energy, diabetic,
                                         _role_ceilings(day, scale))
        _apply_factors(day, step_factors)
        for r, v in step_factors.items():
            factors[r] = factors.get(r, 1.0) * v
        # A portion the model wrote past what one plate holds is cut to it, and the
        # solver runs again so other foods can make up the energy if they have room.
        if not _clip_to_caps(day, scale):
            break
    _trim_salt(day, energy)
    after = _day_totals(day)["calories"]
    return {"factor": round(after / before, 2), "before": round(before), "after": round(after),
            "role_factors": {r: round(v, 2) for r, v in factors.items() if abs(v - 1) > 0.02}}


_SALTS = ("salt", "rock_salt")
_MIN_SALT_PER_MEAL = 0.5
# Salt in a home-cooked savoury main meal, before any trimming to the day's limit.
_COOK_SALT_G = 1.5


def _trim_salt(day: dict, energy: dict) -> None:
    """Hold the day under its sodium limit by trimming the salt added in cooking —
    in an Indian kitchen almost all of it comes from there, and it is the one
    component that changes no dish. Never below half a gram in a savoury meal."""
    limit = ((energy.get("nutrient_targets") or {}).get("sodium_mg") or {}).get("max")
    if not limit:
        return
    sodium = _day_totals(day)["sodium_mg"]
    per_g = (dn.micronutrients().get("salt") or {}).get("sodium_mg", 38758) / 100.0
    salts = [(s, c) for s in _COUNTED for c in ((day.get(s) or {}).get("components") or [])
             if c["food"] in _SALTS]
    salt_g = sum(c["grams"] for _, c in salts)
    if sodium <= limit or not salt_g:
        return
    keep = max(0.0, (salt_g - (sodium - limit) / per_g) / salt_g)
    for s in {s for s, _ in salts}:
        for c in day[s]["components"]:
            if c["food"] in _SALTS:
                # Down to the tenth of a gram: rounding to nearest put
                # days 2-24 mg over the limit the trim exists to hold.
                c["grams"] = max(_MIN_SALT_PER_MEAL, math.floor(c["grams"] * keep * 10) / 10)
        _finish_meal_inplace(day[s])


# ── Minerals ─────────────────────────────────────────────────────────────────
# What a dietitian adds when a day is short of calcium, iron or potassium: an
# ordinary side, in the meal it is usually eaten with. Scaling portions cannot fix
# a shortfall like this — it is composition — and measured on 60 profiles calcium
# was met on almost no day for most patients before this step.
# (food, grams, slot, how it reads on the plate)
_MINERAL_SIDES = (
    ("curd_yogurt", 150, "lunch", "a katori of curd"),
    ("buttermilk_chaas", 200, "lunch", "a glass of chaas"),
    ("milk_full_fat", 200, "breakfast", "a glass of milk"),
    ("soy_milk", 200, "breakfast", "a glass of soy milk"),
    ("almond_milk", 200, "breakfast", "a glass of almond milk"),
    ("tofu_firm", 80, "dinner", "a side of tofu"),
    ("paneer", 40, "dinner", "a little paneer"),
    ("sesame_seeds_til", 10, "snack", "a spoon of roasted til"),
    ("ragi_flour", 30, "snack", "a cup of ragi malt"),
    ("methi_fenugreek_leaves", 60, "lunch", "a side of methi saag"),
    ("cluster_beans_gavar", 80, "dinner", "a side of gavar"),
    ("pumpkin_seeds", 10, "snack", "a spoon of pumpkin seeds"),
    ("amla", 40, "snack", "an amla"),
    ("banana", 100, "snack", "a banana"),
    ("coconut_water", 200, "snack", "a glass of coconut water"),
)
_MINERAL_KEYS = ("calcium_mg", "iron_mg", "potassium_mg")
# Spinach calcium is bound to oxalate and barely absorbed; it is counted in the
# totals, as the tables do, but never chosen to supply calcium.
_POOR_CALCIUM = {"spinach", "palak"}
_MAX_SIDES_PER_DAY = 3


def _mineral_gaps(day: dict, energy: dict) -> dict:
    nt = energy.get("nutrient_targets") or {}
    tot = _day_totals(day)
    gaps = {}
    for k in _MINERAL_KEYS:
        lo = (nt.get(k) or {}).get("min")
        if lo and tot.get(k, 0) < lo:
            gaps[k] = (lo - tot[k], lo)
    return gaps


def _add_mineral_sides(day: dict, energy: dict, allowed_ids: set) -> list[str]:
    """Add up to three ordinary sides to a day short of calcium, iron or potassium,
    chosen from the patient's screened foods. A side that would make its meal a
    Viruddha combination (milk beside banana or sour fruit) is passed over."""
    from services.ahara_safety import scan_meal_for_viruddha

    added: list[str] = []
    table = dn.micronutrients()
    for _ in range(_MAX_SIDES_PER_DAY):
        gaps = _mineral_gaps(day, energy)
        if not gaps:
            break
        present = {c["food"] for s in _COUNTED for c in ((day.get(s) or {}).get("components") or [])}
        best, best_score = None, 0.08
        for fid, grams, slot, phrase in _MINERAL_SIDES:
            meal = day.get(slot)
            if fid not in allowed_ids or fid in present or not isinstance(meal, dict):
                continue
            row, kcal = table.get(fid) or {}, (dn.food(fid) or {}).get("nutrition_per_100g", {})
            score = 0.0
            for k, (short, target) in gaps.items():
                if k == "calcium_mg" and fid in _POOR_CALCIUM:
                    continue
                gain = (row.get(k) or 0) * grams / 100
                score += min(gain, short) / target
            score /= 1 + (kcal.get("calories") or 0) * grams / 100 / 150
            if score <= best_score:
                continue
            trial = {**meal, "components": [*meal["components"], {"food": fid, "grams": grams}]}
            if len(scan_meal_for_viruddha(trial, slot)) > len(scan_meal_for_viruddha(meal, slot)):
                continue
            best, best_score = (fid, grams, slot, phrase), score
        if not best:
            break
        fid, grams, slot, phrase = best
        meal = day[slot]
        meal["components"].append({"food": fid, "grams": grams})
        meal["meal_name"] = f"{meal.get('meal_name') or ''} + {phrase}".strip(" +")
        meal.setdefault("mineral_sides", []).append(fid)
        _finish_meal_inplace(meal)
        added.append(fid)
    return added


def _finish_meal_inplace(meal: dict) -> None:
    meal.update(_finish_meal(meal))


def _day_totals(day: dict) -> dict:
    """The day's nutrition, including the daily drink — a 220 kcal glass of milk was
    left out of every total — and its minerals and folate."""
    tot = dict.fromkeys(("calories", "protein_g", "carbs_g", "fat_g", "fiber_g") + dn.MICROS, 0.0)
    for s in SLOTS + (DRINK,):
        m = (day.get(s) or {}).get("macros_approx") or {}
        for k in tot:
            tot[k] += float(m.get(k) or 0)
    return {k: round(v, 1) for k, v in tot.items()}


def _micro_report(weeks: list[dict], energy: dict, fasting: set) -> dict:
    """Average per day against each mineral target, and on how many days it is met.
    A food with no data is named, so a short figure is not read as a measured one."""
    nt = energy.get("nutrient_targets") or {}
    days = [w["daily_plan"][d] for w in weeks for d in DAYS
            if d in w["daily_plan"] and not w["daily_plan"][d].get("is_fasting")]
    out: dict = {}
    for key in dn.MICROS:
        vals = [d.get("day_totals", {}).get(key, 0.0) for d in days]
        if not vals:
            continue
        row = {"average": round(sum(vals) / len(vals), 1)}
        t = nt.get(key) or {}
        if t.get("max") is not None:
            row["max"] = t["max"]
            row["days_over"] = sum(1 for v in vals if v > t["max"])
        if t.get("min") is not None:
            row["min"] = t["min"]
            row["days_met"] = sum(1 for v in vals if v >= t["min"])
        out[key] = row
    unmeasured = sorted({f for w in weeks for d in w["daily_plan"].values()
                         for s in _COUNTED for f in ((d.get(s) or {}).get("micros_unmeasured") or [])})
    out["unmeasured_foods"] = unmeasured
    out["days_counted"] = len(days)
    out["notices"] = _mineral_notices(out)
    return out


# Ordinary food reaches an iron requirement of 27-32 mg, or calcium of 1200 mg
# without dairy, only with difficulty; that is why India's programmes supplement
# (Anaemia Mukt Bharat for iron and folic acid). Where the plan's food falls short
# the patient is told so, and told who decides about a tablet.
_MINERAL_ADVICE = {
    "iron_mg": ("iron", "Ask your doctor whether you need an iron-folic acid tablet, and "
                "have your haemoglobin checked. Eat a vitamin C food (amla, guava, lemon) "
                "with your meals, and keep tea and coffee an hour away from them."),
    "calcium_mg": ("calcium", "Ask your doctor whether you need a calcium and vitamin D "
                   "supplement."),
}


def _mineral_notices(report: dict) -> list[str]:
    notes = []
    for key, (label, advice) in _MINERAL_ADVICE.items():
        row = report.get(key) or {}
        lo, avg = row.get("min"), row.get("average")
        if lo and avg is not None and avg < 0.9 * lo:
            notes.append(f"The food in this plan gives about {round(avg)} mg of {label} a "
                         f"day; you need about {lo} mg. {advice}")
    return notes


def finalise_weeks(weeks: list[dict], energy: dict, fasting: set,
                   allowed_ids: set | None = None) -> dict:
    """Bring every day to its targets and report what was reached. Shared by the LLM
    path and the rule-engine fallback, so a fallback plan is held to the same numbers."""
    # A renal plan is held to a protein ceiling and, by the clinician, to phosphorus
    # and potassium; dairy and seeds are the wrong thing to add to it.
    renal = bool(((energy.get("nutrient_targets") or {}).get("protein_g") or {}).get("max"))
    # Energy: scale each day toward target, then report.
    days_report, below_protein = [], []
    for w in weeks:
        for d in DAYS:
            day = w["daily_plan"][d]
            if allowed_ids and not renal and not day.get("is_fasting"):
                # Sides first, so the solver sizes the whole plate to the energy band;
                # then once more for what the solver's trimming took back.
                _add_mineral_sides(day, energy, allowed_ids)
                _reconcile_day(day, energy)
                _add_mineral_sides(day, energy, allowed_ids)
            r = _reconcile_day(day, energy)
            day["day_totals"] = _day_totals(day)
            days_report.append({"week": w["week_number"], "day": d, **r,
                                "protein_g": day["day_totals"]["protein_g"]})
            if not day.get("is_fasting") and day["day_totals"]["protein_g"] < energy["protein_floor_g"]:
                below_protein.append(f"Week {w['week_number']} {d}")

    lo, hi = energy["band"]
    measured = [r for r in days_report if r["after"]]
    reconciliation = {
        "checked": True, "method": "computed_from_components",
        "target_kcal": energy["target_calories"], "band_kcal": [lo, hi],
        "days_quantified": len(measured), "days_unquantified": 28 - len(measured),
        "days_adjusted": sum(1 for r in days_report if r["factor"] != 1.0),
        "days_in_band": sum(1 for r in measured
                            if (lambda b: b[0] <= r["after"] <= b[1])(
                                _fasting_energy(energy)["band"] if r["day"] in fasting else (lo, hi))),
        # Kept under its old name for the screen: these days are held light, at about
        # 60% of the target, rather than brought up to it.
        "fasting_days_exempt": sum(1 for w in weeks for d in DAYS
                                   if w["daily_plan"][d].get("is_fasting")),
        "fasting_day_target_kcal": _fasting_energy(energy)["target_calories"],
        "protein_floor_g": energy["protein_floor_g"],
        "days_below_protein_floor": below_protein,
        "days": days_report,
        "micronutrients": _micro_report(weeks, energy, fasting),
    }
    # Some combinations of targets cannot all be met with ordinary foods — a renal
    # protein ceiling beside a high energy need is the usual one. A plan that misses
    # on most days says so, rather than reading as checked.
    missed = len(measured) - reconciliation["days_in_band"]
    if missed > 7 or len(below_protein) > 7:
        reconciliation["targets_unmet_notice"] = (
            "Your targets could not all be met with ordinary foods on most days"
            + (" — a kidney protein limit beside your energy need usually needs specialised "
               "low-protein products. Please work with a renal dietitian."
               if ((energy.get("nutrient_targets") or {}).get("protein_g") or {}).get("max")
               else ". Please review this plan with a dietitian."))
    return reconciliation


# ── Entry point ──────────────────────────────────────────────────────────────

async def generate_week_by_week(user_profile: dict, diet_prefs: dict, brief: str,
                                arc: dict, energy: dict, extra_terms: dict) -> dict:
    """The plan body: diet_weeks (all 28 days in full), overview prose, and reports.

    Raises if the plan cannot be produced, so the caller can fall back."""
    from services.diet_allowed_foods import allowed_foods, food_list_for_prompt
    from services.diet_brief_builder import (diet_allergies, diet_conditions,
                                             fasting_days_for)

    screen = allowed_foods(user_profile, diet_prefs, extra_terms=extra_terms)
    allowed = screen["allowed"]
    allowed_ids = {f["id"] for f in allowed}
    foods_text = food_list_for_prompt(allowed)
    mb = energy["meal_budget"]
    fasting = {d.capitalize() for d in (fasting_days_for(user_profile, diet_prefs) or [])}
    fasting_line = (f"\nFasting days: {', '.join(sorted(fasting))} — Phalahar only (fruit, "
                    "milk or plant milk, nuts, makhana, sabudana if allowed); light and "
                    "deliberately below the energy budget." if fasting else "")

    def week_prompt(w):
        phase = next((x["phase"] for x in arc["weeks"] if x["week_number"] == w), "")
        return WEEK_PROMPT.format(
            brief=brief, foods=foods_text, week=w, phase=phase, staples=_staples(allowed, w),
            fasting=fasting_line, b=mb["breakfast"], l=mb["lunch"], s=mb["snack"],
            d=mb["dinner"], protein=energy["protein_floor_g"], meal=_MEAL_SHAPE,
            fat=(energy.get("nutrient_targets") or {}).get("fat_g", {}).get("target", "~30% of energy"),
            carbs=(energy.get("nutrient_targets") or {}).get("carbs_g", {}).get("target", "~55% of energy"),
            carb_rule=_carb_rule(energy),
            salt_g=_salt_budget(energy), micro_rule=_micro_rule(energy),
            drink=_DRINK_SHAPE)

    overview_prompt = OVERVIEW_PROMPT.format(
        brief=brief, food_names=", ".join(dn._short(f.get("name") or f["id"]) for f in allowed))
    results = await asyncio.gather(
        *(_ask(week_prompt(w), _WEEK_TOKENS, _validate_week(w)) for w in (1, 2, 3, 4)),
        _ask(overview_prompt, _OVERVIEW_TOKENS, _validate_overview),
        return_exceptions=True)
    weeks_raw, overview = results[:4], results[4]
    failed = [i + 1 for i, r in enumerate(weeks_raw) if isinstance(r, Exception)]
    if len(failed) >= 3:
        raise RuntimeError(f"weeks {failed} could not be generated")
    # One or two weeks failing twice no longer costs the whole plan: those weeks are
    # composed by the rule engine from the same screened list and brought to the same
    # targets below. A breastfeeding mother's whole plan fell to the rule engine
    # because one week of four came back malformed twice.
    engine_weeks: dict = {}
    if failed:
        from services.diet_plan_engine import generate_diet_plan
        raw_engine = generate_diet_plan(user_profile, diet_prefs, extra_terms=extra_terms)
        ew, _ = _engine_weeks(raw_engine, allowed_ids)
        engine_weeks = {w["week_number"]: w for w in ew}
        logger.warning(f"diet weeks {failed} composed by the rule engine after two failures")
    if isinstance(overview, Exception):
        logger.warning(f"diet overview failed, plan continues without it: {overview}")
        overview = {}

    # Assemble every week in full and compute every meal.
    weeks = []
    for i, wr in enumerate(weeks_raw):
        if isinstance(wr, Exception):
            ew = dict(engine_weeks[i + 1])
            ew["phase"] = next((x["phase"] for x in arc["weeks"] if x["week_number"] == i + 1),
                               ew.get("phase", ""))
            ew["composed_by"] = "rule_engine"
            for d in DAYS:
                ew["daily_plan"].setdefault(d, {})["is_fasting"] = d in fasting
            weeks.append(ew)
            continue
        w = wr["week_number"]
        phase = next((x["phase"] for x in arc["weeks"] if x["week_number"] == w), "")
        daily = {}
        for d in DAYS:
            day = dict(wr["days"][d])
            for slot in SLOTS + (DRINK,):
                if isinstance(day.get(slot), dict):
                    day[slot] = _finish_meal(day[slot])
            day["is_fasting"] = d in fasting
            daily[d] = day
        weeks.append({"week_number": w, "phase": phase,
                      "phase_description": wr["phase_description"], "daily_plan": daily})
    plan = {"diet_weeks": weeks}

    # Scan, then repair what the scans or the allowed list rejected.
    allergies = diet_allergies(user_profile, diet_prefs)
    intolerances = diet_prefs.get("food_intolerances") or []
    dtype = diet_prefs.get("dietary_type")
    conditions = diet_conditions(user_profile, diet_prefs)
    pregnant = bool(user_profile.get("pregnancy_or_nursing"))

    def problems():
        found = _scan(plan, allergies, intolerances, dtype, conditions, extra_terms, pregnant)
        for w, d, slot, day in _units(weeks):
            off = _off_list(day[slot], allowed_ids)
            if off:
                found.setdefault((w, d, slot), []).append(
                    f"uses foods not on the allowed list: {', '.join(off)}")
        return found

    report = {"flagged_initially": 0, "repaired": 0, "substituted": 0}
    found = problems()
    report["flagged_initially"] = len(found)
    if found:
        items, keys = [], {}
        for i, ((w, d, slot), reasons) in enumerate(sorted(found.items())):
            key = f"m{i}"
            keys[key] = (w, d, slot)
            meal = weeks[w - 1]["daily_plan"][d][slot]
            budget = mb.get(slot, 0) if slot != DRINK else 0
            items.append(f'- key "{key}": week {w} {d} {slot} (~{budget} kcal) — '
                         f'"{meal.get("meal_name") or meal.get("name")}" — '
                         f'{"; ".join(reasons)[:300]}')
        try:
            fixed = await _ask(REPAIR_PROMPT.format(
                brief=brief, foods=foods_text, items="\n".join(items), meal=_MEAL_SHAPE,
                drink=_DRINK_SHAPE), _REPAIR_TOKENS, _validate_repair)
            for entry in fixed["meals"]:
                where = keys.get(str(entry.get("key")))
                meal = entry.get("meal")
                if where and isinstance(meal, dict) and dn.components_of(meal):
                    w, d, slot = where
                    weeks[w - 1]["daily_plan"][d][slot] = _finish_meal(meal)
                    report["repaired"] += 1
        except Exception as e:  # noqa: BLE001 — substitution below still guarantees safety
            logger.warning(f"diet repair call failed: {e}")
        rng = random.Random(str(user_profile.get("id") or "anon"))
        for (w, d, slot) in problems():
            weeks[w - 1]["daily_plan"][d][slot] = _safe_meal(
                slot, allowed, mb.get(slot, 0) if slot != DRINK else 0, rng)
            report["substituted"] += 1

    reconciliation = finalise_weeks(weeks, energy, fasting, allowed_ids)
    distinct = {(m.get("meal_name") or "").lower() for _, _, s, day in _units(weeks)
                if s in SLOTS for m in [day[s]]}
    report["weeks_from_rule_engine"] = failed
    return {
        "diet_weeks": weeks,
        "overview": overview,
        "energy_reconciliation": reconciliation,
        "composition_report": {**report, "distinct_meals": len(distinct),
                               "allowed_foods": len(allowed),
                               "excluded_foods": screen["excluded"]},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def engine_plan_to_weeks(raw: dict, energy: dict, allowed_ids: set | None = None) -> dict:
    """The rule engine's food lists as the same component meals the LLM path writes,
    brought to the same targets. Its meals were lists of foods with a portion each,
    and they missed the protein floor on 26 of 28 days."""
    weeks, fasting = _engine_weeks(raw, allowed_ids)
    return {"diet_weeks": weeks,
            "energy_reconciliation": finalise_weeks(weeks, energy, fasting, allowed_ids)}


def _engine_weeks(raw: dict, allowed_ids: set | None = None) -> tuple[list[dict], set]:
    from services.diet_plan_engine import _ITEM_PORTIONS, _PORTION

    def grams(item):
        fid = item.get("id")
        if fid in _ITEM_PORTIONS:
            return _ITEM_PORTIONS[fid][1]
        return _PORTION.get(item.get("category"), ("100g", 100))[1]

    # The engine composes without cooking fat — a day came out at 7.5 g of fat against
    # 44 — and the solver can only size a component that is there. One teaspoon of an
    # allowed fat goes into each main meal for it to size.
    allowed_fat = next((fid for fid in ("ghee", "sesame_oil", "groundnut_oil", "sunflower_oil",
                                        "mustard_oil", "coconut_oil", "olive_oil")
                        if fid in (allowed_ids or set())), None)
    weeks, fasting = [], set()
    for w in raw.get("four_week_plan") or []:
        daily = {}
        for day in w.get("days") or []:
            name = day.get("day_name")
            out = {"theme": w.get("week_theme", ""), "is_fasting": bool(day.get("is_fasting_day"))}
            if out["is_fasting"]:
                fasting.add(name)
            for slot in SLOTS:
                items = (day.get("meals") or {}).get(slot) or []
                comps = [{"food": i["id"], "grams": grams(i)} for i in items if i.get("id")]
                if not comps:
                    continue
                if allowed_fat and slot != "snack" and not out["is_fasting"] and not any(
                        dn.role(c["food"]) == "fat" for c in comps):
                    comps.append({"food": allowed_fat, "grams": 5})
                # The cook salts the dal and sabzi. Leaving it out reported a day's
                # sodium at 160 mg — a measurement of nothing. `_trim_salt` holds the
                # day to its limit afterwards.
                if slot in ("lunch", "dinner") and not out["is_fasting"] and not any(
                        c["food"] in _SALTS for c in comps):
                    comps.append({"food": "salt", "grams": _COOK_SALT_G})
                out[slot] = _finish_meal({
                    "meal_name": " with ".join(dn._short(i.get("name") or i["id"]) for i in items[:3]),
                    "description": "Composed from your screened food list.",
                    "ayurvedic_note": "", "components": comps})
            daily[name] = out
        weeks.append({"week_number": w.get("week"), "phase": w.get("week_theme", ""),
                      "phase_description": w.get("agni_note", ""), "daily_plan": daily})
    return weeks, fasting
