"""`F` — one authored food, written the way a nighantu entry is written.

Defaults carry the common case so a spec line says only what is true of THIS food,
and the defaults are the conservative ones: a food is not vegan until someone says
so, and it is not a common allergen until someone says so.

There is deliberately no default for rasa, guna, virya, vipaka, dosha or ritu. Those
are the six fields `seed_diet_foods.py` supplied from a category table, and a default
here would reintroduce exactly the thing this library exists to remove — a food that
carries a value nobody chose for it.
"""

from diet_library import schema


def F(name, *, id=None, category, prep_state, rasa, guna, virya, vipaka, dosha,
      ritu, nutrition, ref, varga, meal=("lunch", "dinner"), prep_minutes=10,
      diet_types=("vegetarian",), vegan=False, allergen=False,
      prabhava=None, pathya_for=(), apathya_for=(), viruddha_with=()):
    """One food in one preparation state.

    `dosha` is a (vata, pitta, kapha) triple on the -2..+2 scale. `prabhava` is the
    specific action that licenses a departure from the rasa rule — state it and the
    row is admitted with its reason attached; omit it and `schema.validate` refuses
    the row rather than letting a silent contradiction into the corpus.

    `id` defaults to a slug of the name plus the prep state, because the same
    ingredient in two states is two rows and they must not collide: Ardraka and
    Shunthi are `ginger_fresh` and `ginger_dry`, not one `ginger`.
    """
    vata, pitta, kapha = dosha
    slug = id or _slug(name, prep_state)
    food = {
        "id": slug,
        "name": name,
        "category": category,
        "prep_state": prep_state,
        "rasa": tuple(rasa),
        "guna": tuple(guna),
        "virya": virya,
        "vipaka": vipaka,
        "prabhava": prabhava,
        "dosha_effect": {"vata": vata, "pitta": pitta, "kapha": kapha},
        "ritu": tuple(ritu),
        "nutrition": dict(nutrition),
        "nighantu_ref": {"text": ref, "varga": varga},
        "meal_suitable": tuple(meal),
        "prep_time_minutes": prep_minutes,
        "dietary_type": tuple(diet_types),
        "vegan": vegan,
        "common_allergen": allergen,
        "pathya_for": tuple(pathya_for),
        "apathya_for": tuple(apathya_for),
        "viruddha_with": tuple(viruddha_with),
        "reviewed": False,
    }
    schema.validate(food)
    return food


def N(calories, protein_g, carbs_g, fat_g, fiber_g, *, source):
    """Macros per 100 g, with the source that says so.

    A source is required rather than defaulted. 109 of the 150 rows in the file this
    replaces carry a per-category constant with nothing recording that they do, which
    is why 27 vegetables report identical calories and nobody noticed.
    """
    return {"calories": float(calories), "protein_g": float(protein_g),
            "carbs_g": float(carbs_g), "fat_g": float(fat_g),
            "fiber_g": float(fiber_g), "source": source}


def _slug(name: str, prep_state: str) -> str:
    # A parenthetical gloss is for the reader — "Shunthi (Dry Ginger)" — and has no
    # business in an id. Most rows pass `id=` explicitly anyway, to keep the same key
    # the current library uses so the migration maps one-to-one.
    head = name.split("(")[0]
    base = "".join(c if c.isalnum() else "_" for c in head.lower()).strip("_")
    while "__" in base:
        base = base.replace("__", "_")
    # `prepared` is the unmarked state — a spice is just itself — so it does not
    # earn a suffix. Everything else does, because the state is part of the identity.
    return base if prep_state == "prepared" else f"{base}_{prep_state}"
