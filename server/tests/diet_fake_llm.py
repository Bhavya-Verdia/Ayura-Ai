"""A stand-in for the LLM on the diet path: answers each prompt kind with valid JSON
built from foods the prompt allows, so the week-by-week generator can be tested
without a model. `bad` puts a named food into chosen meals to exercise the repair."""
import json
import re

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def _allowed(prompt: str) -> list[str]:
    block = prompt.split("ALLOWED FOODS", 1)[1] if "ALLOWED FOODS" in prompt else ""
    return re.findall(r"^\s{2}([a-z0-9_]+) — ", block, re.M)


def _pick(ids, *wanted):
    return next((w for w in wanted if w in ids), ids[0])


def _meal(ids, kind):
    grain = _pick(ids, "brown_rice", "millet_jowar", "quinoa", "poha", "oats")
    pulse = _pick(ids, "moong_dal_yellow", "toor_dal", "masoor_dal", "chhole")
    veg = _pick(ids, "bottle_gourd", "pumpkin", "carrot", "cabbage")
    fat = _pick(ids, "sesame_oil", "sunflower_oil", "olive_oil")
    fruit = _pick(ids, "apple", "papaya", "guava", "pear")
    nut = _pick(ids, "almonds", "walnuts", "pumpkin_seeds", "fox_nuts_makhana")
    comps = {"breakfast": [(grain, 200), (fruit, 100), (nut, 15)],
             "lunch": [(grain, 200), (pulse, 180), (veg, 150), (fat, 6)],
             "snack": [(fruit, 150), (nut, 20)],
             "dinner": [(grain, 180), (pulse, 150), (veg, 150), (fat, 6)]}[kind]
    return {"meal_name": f"{kind} plate", "description": "plain", "ayurvedic_note": "ok",
            "components": [{"food": f, "grams": g} for f, g in comps]}


def _drink(ids):
    bev = _pick(ids, "tulsi_tea", "ginger_tea", "lemon_water", "water")
    return {"name": "warm drink", "when": "morning", "recipe": "steep", "rationale": "ok",
            "components": [{"food": bev, "grams": 200}]}


def make_fake(calls: list, bad: dict | None = None, fail_weeks: set | None = None,
              repair_food: str | None = None):
    """`bad`: {(week, day, slot): food_id} injected on the FIRST week call only."""
    bad = bad or {}
    fail_weeks = set(fail_weeks or ())
    seen_weeks: set = set()

    async def fake(prompt, system_prompt=None, json_mode=True, max_tokens=None, **_):
        calls.append(prompt)
        ids = _allowed(prompt) or ["brown_rice"]
        m = re.search(r"Write WEEK (\d)", prompt)
        if m:
            w = int(m.group(1))
            if w in fail_weeks:
                fail_weeks.discard(w)
                return json.dumps({"oops": True})
            days = {}
            for d in DAYS:
                day = {"theme": "steady", **{s: _meal(ids, s) for s in
                                             ("breakfast", "lunch", "snack", "dinner")},
                       "special_drink": _drink(ids)}
                for (bw, bd, bs), food in bad.items():
                    if bw == w and bd == d and w not in seen_weeks:
                        day[bs]["components"].append({"food": food, "grams": 20})
                        day[bs]["meal_name"] += f" with {food}"
                days[d] = day
            seen_weeks.add(w)
            return json.dumps({"week_number": w, "phase_description": "x", "days": days})
        if "broke a rule" in prompt:
            keys = re.findall(r'key "([^"]+)"', prompt)
            meals = []
            for k in keys:
                meal = _meal(ids, "lunch")
                if repair_food:
                    meal["components"].append({"food": repair_food, "grams": 10})
                meals.append({"key": k, "meal": meal})
            return json.dumps({"meals": meals})
        return json.dumps({"plan_title": "Plan", "plan_description": "d",
                           "pathya_apathya": {"pathya": [], "apathya": []}})
    return fake
