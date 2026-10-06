"""The diet plan's nutrition, computed rather than estimated.

Every number a plan showed used to be the model's own estimate, written to fit the
budget it was given: a pregnant patient's breakfast of "4 medium idli + 2 tbsp
chutney" carried 540 kcal, where those foods come to about 300. The days landed
within a few kcal of target because the model wrote the figure to match the target,
not because the meals did. And only week one had any figures at all.

A meal is now a list of COMPONENTS — `{"food": id, "grams": n}` — and its nutrition
is the sum over components of the per-100 g values in two tables:

* the authored food library (`data/knowledge_base/diet_foods.json`, 150 dravyas,
  each with its own source), which holds most of what a plan is built from;
* `EXTRAS` below: what Indian cooking adds that the library does not schedule as a
  food in its own right — sugar and jaggery, flours and batters, the cooking oils
  people actually use, a few staples (ragi, bhindi, baingan) and the near-zero
  seasonings. Each row states its source. Values marked `estimate` are prepared
  dishes with no single published composition; they are the ones to check first.

Grams are of the food AS ITS ROW DESCRIBES IT: the library's rice and dal rows are
cooked weights, `wheat_flour_atta` is raw flour. The brief says so beside every id.

Portion text is generated from the components, so the household measure on screen
and the figure beside it can no longer disagree — the reconciler scales grams, and
both follow.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

_LIB_PATH = Path(__file__).resolve().parents[1] / "data" / "knowledge_base" / "diet_foods.json"

# id: (name, kcal, protein, carbs, fat, fibre, source, flags)
# flags: "nonveg-free" foods are all vegetarian; `animal` marks non-vegan; allergen
# tags name the declared-allergy vocabulary the row belongs to.
_E = {
    # ── sweeteners ──
    "sugar": ("Sugar", 387, 0.0, 100.0, 0.0, 0.0, "USDA FDC 169655", ()),
    "jaggery": ("Jaggery (gur)", 383, 0.4, 95.0, 0.1, 0.0, "estimate (USDA panela / raw cane sugar)", ()),
    "honey": ("Honey", 304, 0.3, 82.4, 0.0, 0.2, "USDA FDC 169640", ("animal",)),
    "raisins": ("Raisins (kishmish)", 299, 3.1, 79.2, 0.5, 3.7, "USDA FDC 168165", ()),
    # ── flours, batters and grain products ──
    "wheat_flour_atta": ("Whole wheat flour (atta), raw", 340, 13.2, 72.0, 2.5, 10.7, "USDA FDC 168944", ("gluten",)),
    "maida": ("Refined wheat flour (maida), raw", 364, 10.3, 76.3, 1.0, 2.7, "USDA FDC 168936", ("gluten",)),
    "ragi_flour": ("Ragi (finger millet) flour, raw", 321, 7.2, 66.8, 1.9, 11.2, "IFCT 2017", ()),
    "jowar_flour": ("Jowar (sorghum) flour, raw", 334, 10.0, 67.7, 1.7, 9.7, "IFCT 2017", ()),
    "bajra_flour": ("Bajra (pearl millet) flour, raw", 348, 11.0, 61.8, 5.4, 11.5, "IFCT 2017", ()),
    "rice_raw": ("Rice, raw", 365, 7.1, 80.0, 0.7, 1.3, "USDA FDC 168877", ()),
    "vermicelli": ("Vermicelli (semiya), dry", 371, 13.0, 74.7, 1.5, 3.2, "USDA FDC 169736 (durum pasta)", ("gluten",)),
    "sattu": ("Sattu (roasted gram flour)", 369, 22.0, 58.0, 5.2, 10.0, "IFCT 2017 (roasted Bengal gram)", ()),
    "idli": ("Idli, steamed", 140, 4.5, 29.0, 0.5, 1.2, "estimate (rice-urad batter, steamed)", ()),
    "dosa": ("Plain dosa", 165, 3.9, 27.0, 4.4, 1.0, "estimate (rice-urad batter, 1 tsp oil per dosa)", ()),
    "sambar": ("Sambar", 55, 2.8, 8.0, 1.5, 2.2, "estimate (toor dal and vegetables)", ()),
    "coconut_chutney": ("Coconut chutney", 190, 2.5, 7.5, 17.0, 4.5, "estimate (fresh coconut, roasted gram)", ()),
    # ── cooking oils people actually use ──
    "groundnut_oil": ("Groundnut oil", 884, 0.0, 0.0, 100.0, 0.0, "USDA FDC 171410", ("peanuts",)),
    "sunflower_oil": ("Sunflower oil", 884, 0.0, 0.0, 100.0, 0.0, "USDA FDC 172864", ()),
    "rice_bran_oil": ("Rice bran oil", 884, 0.0, 0.0, 100.0, 0.0, "USDA FDC 171028", ()),
    # ── vegetables the library does not hold ──
    "okra_bhindi": ("Okra (bhindi)", 33, 1.9, 7.5, 0.2, 3.2, "USDA FDC 169260", ()),
    "brinjal_baingan": ("Brinjal (baingan)", 25, 1.0, 5.9, 0.2, 3.0, "USDA FDC 169228", ()),
    "tinda": ("Tinda (round gourd)", 21, 1.4, 3.4, 0.2, 1.8, "IFCT 2017", ()),
    "parwal": ("Parwal (pointed gourd)", 20, 2.0, 2.2, 0.3, 3.0, "IFCT 2017", ()),
    "green_chilli": ("Green chilli", 40, 2.0, 9.5, 0.2, 1.5, "USDA FDC 168576", ()),
    "lemon_juice": ("Lemon juice", 22, 0.4, 6.9, 0.2, 0.3, "USDA FDC 167747", ()),
    # ── seasonings: present in nearly every meal, near-zero at the amounts used ──
    "salt": ("Salt", 0, 0.0, 0.0, 0.0, 0.0, "USDA FDC 173468", ()),
    "rock_salt": ("Rock salt (saindhava)", 0, 0.0, 0.0, 0.0, 0.0, "USDA FDC 173468", ()),
    "mustard_seeds": ("Mustard seeds", 508, 26.1, 28.1, 36.2, 12.2, "USDA FDC 172235", ("mustard",)),
    # Compounded hing is usually cut with wheat flour — a classic hidden gluten.
    "hing": ("Asafoetida (hing)", 297, 4.0, 67.8, 1.1, 4.1, "estimate (compounded hing)", ("gluten",)),
    "curry_leaves": ("Curry leaves", 108, 6.1, 18.7, 1.0, 6.4, "IFCT 2017", ()),
    "coriander_leaves": ("Coriander leaves", 23, 2.1, 3.7, 0.5, 2.8, "USDA FDC 169997", ()),
    "mint_leaves": ("Mint leaves", 70, 3.8, 14.9, 0.9, 8.0, "USDA FDC 173475", ()),
    "tamarind": ("Tamarind pulp", 239, 2.8, 62.5, 0.6, 5.1, "USDA FDC 168168", ()),
    "red_chilli_powder": ("Red chilli powder", 282, 13.5, 49.7, 14.3, 34.8, "USDA FDC 171319", ()),
    "garam_masala": ("Garam masala", 379, 13.0, 50.0, 15.0, 25.0, "estimate (whole-spice blend)", ()),
    "water": ("Water", 0, 0.0, 0.0, 0.0, 0.0, "—", ()),
}

EXTRAS = {k: {"id": k, "name": v[0], "category": "extra",
              "nutrition_per_100g": {"calories": v[1], "protein_g": v[2], "carbs_g": v[3],
                                     "fat_g": v[4], "fiber_g": v[5]},
              "nutrition_source": v[6], "vegan": "animal" not in v[7],
              "allergens": [t for t in v[7] if t != "animal"]}
          for k, v in _E.items()}

# Seasonings whose grams a meal may state loosely; they never count toward the
# share of a meal that is "quantified".
SEASONINGS = {"salt", "rock_salt", "mustard_seeds", "hing", "curry_leaves",
              "coriander_leaves", "mint_leaves", "green_chilli", "red_chilli_powder",
              "garam_masala", "water", "turmeric", "cumin_jeera", "coriander_dhania",
              "fennel_saunf", "cardamom_elaichi", "cinnamon_dalchini", "black_pepper",
              "ginger_dry_saunth", "fenugreek_seeds_methi", "ajwain", "lemon_juice"}


@lru_cache(maxsize=1)
def _library() -> dict:
    data = json.loads(_LIB_PATH.read_text())
    foods = data if isinstance(data, list) else data.get("foods", [])
    return {f["id"]: f for f in foods}


def food(food_id: str) -> dict | None:
    return _library().get(food_id) or EXTRAS.get(food_id)


def all_ids() -> set:
    return set(_library()) | set(EXTRAS)


# ── Household measures ───────────────────────────────────────────────────────
# What the grams are called in an Indian kitchen. A katori of cooked dal or rice is
# ~150 g; a phulka ~35 g, a roti ~40 g; a teaspoon of oil or ghee 5 g. Shown beside the
# grams, never instead of them.
_UNIT_BY_ID = {
    "roti_whole_wheat": ("roti", 40), "paratha": ("paratha", 80),
    "bread_whole_wheat": ("slice", 30), "idli": ("idli", 40), "dosa": ("dosa", 90),
    "banana": ("banana", 118), "apple": ("apple", 150), "orange": ("orange", 130),
    "guava": ("guava", 100), "pear": ("pear", 170), "kiwi": ("kiwi", 70),
    "dates": ("date", 8), "figs": ("fig", 20), "almonds": ("almond", 1.2),
    "walnuts": ("walnut half", 2.5), "cashews": ("cashew", 1.5),
    "pistachios": ("pistachio", 0.7), "amla": ("amla", 30), "chikoo_sapota": ("chikoo", 100),
    "mosambi_sweet_lime": ("sweet lime", 150), "mango": ("mango", 200),
}
_ROTI_FLOURS = {"wheat_flour_atta", "jowar_flour", "bajra_flour"}
_SPOON_IDS = {"ghee", "ghee_oil", "sesame_oil", "coconut_oil", "mustard_oil", "olive_oil",
              "groundnut_oil", "sunflower_oil", "rice_bran_oil", "butter", "sugar",
              "jaggery", "honey", "flax_seeds", "chia_seeds", "sesame_seeds_til", "raisins"}
_KATORI_CATEGORIES = {"grain", "legume", "vegetable", "dairy"}


def _fmt(n: float) -> str:
    return f"{n:.2f}".rstrip("0").rstrip(".")


# Drunk, so measured in ml (1 ml ~ 1 g at these densities) and named by the glass.
_LIQUIDS = {"milk_full_fat", "buttermilk_chaas", "lassi", "almond_milk", "soy_milk",
            "oat_milk", "flax_milk", "coconut_milk", "coconut_water", "green_tea",
            "tulsi_tea", "ginger_tea", "lemon_water", "whey"}


def household(food_id: str, grams: float) -> str | None:
    """'1 katori', '2 roti', '1 tsp' — the measure a cook uses, or None."""
    if grams <= 0:
        return None
    if food_id in _LIQUIDS:
        glasses = grams / 200.0
        return f"{_fmt(round(glasses * 4) / 4)} glass" if glasses >= 0.5 else None
    if food_id in _UNIT_BY_ID:
        unit, each = _UNIT_BY_ID[food_id]
        count = grams / each
        if count >= 0.75:
            # Small pieces are counted whole — nobody eats 8.5 almonds.
            whole = round(count) if each < 5 else round(count * 2) / 2
            return f"{_fmt(whole)} {unit}{'' if whole == 1 or unit.endswith('s') else 's'}"
        return None
    if food_id in _ROTI_FLOURS:
        # Flour is weighed by nobody at the table; ~30 g makes one roti or bhakri.
        rotis = grams / 30.0
        return f"about {_fmt(max(1, round(rotis)))} roti" + ("s" if round(rotis) > 1 else "")
    if food_id in _SPOON_IDS:
        tsp = grams / 5.0
        if tsp >= 3:
            return f"{_fmt(round(tsp / 3 * 2) / 2)} tbsp"
        return f"{_fmt(max(0.5, round(tsp * 2) / 2))} tsp"
    f = food(food_id) or {}
    if f.get("category") in _KATORI_CATEGORIES and grams >= 60:
        return f"{_fmt(round(grams / 150 * 4) / 4)} katori"
    return None


# ── Computation ──────────────────────────────────────────────────────────────

_KEYS = ("calories", "protein_g", "carbs_g", "fat_g", "fiber_g")

# What each component does in a meal, for balancing a day without changing its dishes.
_ROLE_BY_EXTRA = {
    "wheat_flour_atta": "grain", "maida": "grain", "ragi_flour": "grain", "rice_raw": "grain",
    "jowar_flour": "grain", "bajra_flour": "grain",
    "vermicelli": "grain", "idli": "grain", "dosa": "grain", "sattu": "protein",
    "sambar": "protein", "sugar": "sweet", "jaggery": "sweet", "honey": "sweet",
    "raisins": "sweet",
}
_ROLE_BY_CATEGORY = {"grain": "grain", "legume": "protein", "vegan_protein": "protein",
                     "dairy": "protein", "vegetable": "vegetable", "fruit": "fruit",
                     "nut_seed": "nut", "oil": "fat", "spice": "seasoning",
                     "beverage": "drink"}


def role(food_id: str) -> str:
    if food_id in ADDED_FATS or food_id in ("cream",):
        return "fat"
    if food_id in SEASONINGS:
        return "seasoning"
    if food_id in _ROLE_BY_EXTRA:
        return _ROLE_BY_EXTRA[food_id]
    if food_id in ("dates", "figs", "grapes", "chikoo_sapota", "mango"):
        return "sweet_fruit"
    f = food(food_id) or {}
    return _ROLE_BY_CATEGORY.get(f.get("category"), "other")


# Fat added in cooking — the one component a cook changes without changing the dish.
ADDED_FATS = {"ghee", "ghee_oil", "butter", "sesame_oil", "coconut_oil", "mustard_oil",
              "olive_oil", "groundnut_oil", "sunflower_oil", "rice_bran_oil"}


def components_of(meal: dict) -> list[dict]:
    comps = meal.get("components") if isinstance(meal, dict) else None
    out = []
    for c in comps or []:
        if not isinstance(c, dict):
            continue
        fid = str(c.get("food") or c.get("food_id") or "").strip()
        try:
            grams = float(c.get("grams") or 0)
        except (TypeError, ValueError):
            grams = 0.0
        if fid and grams > 0:
            out.append({"food": fid, "grams": round(grams, 1)})
    return out


def compute(components: list[dict]) -> dict:
    """Nutrition of a list of components, and which ids could not be found."""
    total = dict.fromkeys(_KEYS, 0.0)
    unknown = []
    for c in components:
        f = food(c["food"])
        if not f:
            unknown.append(c["food"])
            continue
        per = f.get("nutrition_per_100g") or {}
        for k in _KEYS:
            total[k] += float(per.get(k) or 0) * c["grams"] / 100.0
    out = {"calories": round(total["calories"]), "protein_g": round(total["protein_g"], 1),
           "carbs_g": round(total["carbs_g"], 1), "fat_g": round(total["fat_g"], 1),
           "fiber_g": round(total["fiber_g"], 1)}
    return {"nutrition": out, "unknown": unknown}


def name_of(food_id: str) -> str:
    f = food(food_id) or {}
    return f.get("name") or food_id.replace("_", " ").title()


# What one meal can realistically hold of a single food, in grams as the row states
# it. Beyond these the plate stops being a meal anyone eats: the solver was free to
# write 2.75 katori of rice at one sitting, and 199 grain portions across sixteen
# plans exceeded 2 katori.
_RAW_FLOURS = {"wheat_flour_atta", "maida", "ragi_flour", "jowar_flour", "bajra_flour",
               "rice_raw", "vermicelli", "sattu", "chickpea_flour_besan", "rice_flakes"}


def meal_cap(food_id: str, scale: float = 1.0) -> float:
    """A realistic single-meal portion of one food, scaled for a high energy target —
    a 3700 kcal athlete is served a bigger plate, and capping them at an ordinary
    one left 23 of 28 days short of target."""
    return _base_cap(food_id) * max(1.0, min(1.6, scale))


def _base_cap(food_id: str) -> float:
    r = role(food_id)
    if food_id in _RAW_FLOURS:
        return 120
    if food_id in ("paratha", "roti_whole_wheat", "bread_whole_wheat"):
        return 200
    if food_id in ("idli", "dosa"):
        return 300
    if food_id in ("paneer", "tofu_firm", "vegan_paneer_tofu", "tempeh", "soya_chunks"):
        return 150 if food_id != "tofu_firm" else 200
    if food_id in _LIQUIDS:
        return 400
    return {"grain": 300, "protein": 250, "vegetable": 300, "fruit": 250,
            "sweet_fruit": 120, "nut": 40, "fat": 25, "sweet": 15}.get(r, 400)


def portion_text(components: list[dict]) -> str:
    """'Moong Dal 150 g (1 katori) · Ghee 5 g (1 tsp)' — main items first, seasonings
    left out: the patient measures the food, not the salt. A drink made only of
    seasonings (coriander-seed water) is described by them instead of by nothing."""
    if components and all(c["food"] in SEASONINGS for c in components):
        water = next((c["grams"] for c in components if c["food"] == "water"), 200)
        steeped = " · ".join(f"{name_of(c['food'])} {_fmt(round(c['grams']))} g"
                             for c in components if c["food"] != "water")
        return f"{steeped} in a glass of water ({_fmt(round(water))} ml)" if steeped \
            else f"A glass of water ({_fmt(round(water))} ml)"
    parts = []
    for c in sorted(components, key=lambda c: -c["grams"]):
        if c["food"] in SEASONINGS:
            continue
        hh = household(c["food"], c["grams"])
        unit = "ml" if c["food"] in _LIQUIDS else "g"
        g = _fmt(round(c["grams"]))
        label = name_of(c["food"]) if c["food"] in EXTRAS else _short(name_of(c["food"]))
        parts.append(f"{label} {g} {unit}" + (f" ({hh})" if hh else ""))
    return " · ".join(parts)


def _short(name: str) -> str:
    """'Mudga (Moong Dal, Yellow)' -> 'Moong Dal, Yellow' — the English the library
    puts in brackets is what a reader shopping for it recognises."""
    m = re.search(r"\(([^)]+)\)", name)
    return m.group(1) if m else name


def scale(components: list[dict], factor: float) -> list[dict]:
    """Every component scaled except seasonings, rounded to what a cook can measure."""
    out = []
    for c in components:
        if c["food"] in SEASONINGS:
            out.append(dict(c))
            continue
        g = c["grams"] * factor
        step = 1 if g < 20 else 5
        out.append({"food": c["food"], "grams": max(step, round(g / step) * step)})
    return out


def apply_to_meal(meal: dict) -> dict:
    """Stamp a meal's computed nutrition and portion text from its components.

    `macros_approx` keeps its name — `DietView`, the export and the reconciler read
    it — but is now computed, and `nutrition_basis` says so."""
    comps = components_of(meal)
    if not comps:
        return meal
    result = compute(comps)
    meal["components"] = comps
    meal["macros_approx"] = result["nutrition"]
    meal["portion"] = portion_text(comps) or meal.get("portion")
    meal["nutrition_basis"] = "computed" if not result["unknown"] else "partial"
    if result["unknown"]:
        meal["unknown_components"] = result["unknown"]
    return meal
