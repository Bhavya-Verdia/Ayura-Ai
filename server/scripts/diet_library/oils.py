"""The five oils.

`seed_diet_foods.py` gives the whole `oil` category one profile — `rasa: ["sweet"],
virya: heating, guna: heavy, dosha: (-1, +1, +1)` — with sesame and mustard picked out
by name for a virya override. Coconut oil is shita virya and Pitta's oil of choice; the
category default made it heating, which inverts the reason it is given.

`ghee_oil` and `ghee` are two ids for one dravya. That duplication is inherited from
the generator's category lists — ghee appears in both `dairy` and `oil` — and it is
carried forward unchanged here so the migration maps one-to-one. It should collapse to
one row when the library is complete; see the note on `ghee` in `dairy.py`.

AUTHORED, NOT CLINICALLY REVIEWED. Macros from USDA FoodData Central.
"""

from diet_library.schema import ALL_RITU
from diet_library.spec import F, N

_OIL = dict(category="oil", prep_state="prepared", meal=("lunch", "dinner"),
            prep_minutes=1, ref="bhavaprakasha", varga="Taila")

_FAT = dict(protein_g=0.0, carbs_g=0.0, fiber_g=0.0)

OILS = [
    F("Tila Taila (Sesame Oil)", id="sesame_oil",
      rasa=("madhura", "tikta", "kashaya"), guna=("guru", "snigdha", "tikshna"),
      virya="ushna", vipaka="katu",
      prabhava="Pitta-vardhaka despite a rasa set that is entirely Pitta-pacifying — "
               "the ushna virya governs here, which is why Tila Taila is the Vata oil "
               "and not the Pitta one.",
      dosha=(-2, 1, 1), ritu=("shishira", "hemanta", "varsha"),
      pathya_for=("constipation", "amavata", "arsha"),
      apathya_for=("acidity", "psoriasis"),
      diet_types=("vegetarian", "vegan"), vegan=True,
      nutrition=N(884, fat_g=100.0, source="usda", **_FAT), **_OIL),

    F("Narikela Taila (Coconut Oil)", id="coconut_oil",
      rasa=("madhura",), guna=("guru", "snigdha", "manda"), virya="shita",
      vipaka="madhura",
      dosha=(-1, -2, 1), ritu=("grishma", "sharad"),
      pathya_for=("acidity", "psoriasis", "migraine"),
      apathya_for=("obesity", "high_cholesterol"),
      diet_types=("vegetarian", "vegan"), vegan=True,
      nutrition=N(862, fat_g=100.0, source="usda", **_FAT), **_OIL),

    F("Sarshapa Taila (Mustard Oil)", id="mustard_oil",
      rasa=("katu", "tikta"), guna=("laghu", "snigdha", "tikshna"),
      virya="ushna", vipaka="katu",
      prabhava="Vata-hara despite katu-tikta rasa: it is a sneha, and the oleating "
               "quality reaches Vata where the rasa alone would raise it. Classically "
               "kapha-vata hara and decidedly Pitta-vardhaka.",
      dosha=(-1, 2, -2), ritu=("shishira", "hemanta", "vasanta"),
      pathya_for=("obesity", "hypothyroid"),
      apathya_for=("acidity", "psoriasis", "migraine"),
      diet_types=("vegetarian", "vegan"), vegan=True,
      nutrition=N(884, fat_g=100.0, source="usda", **_FAT), **_OIL),

    F("Goghrita (Cow's Ghee)", id="ghee_oil",
      rasa=("madhura",), guna=("guru", "snigdha", "mridu"), virya="shita",
      vipaka="madhura",
      prabhava="Agni-deepana while being snigdha and guru — the classical exception "
               "that makes Ghrita the one fat given to a weak Agni rather than "
               "withheld from it (Charaka Sutrasthana 13). Vata-Pitta hara, "
               "Ojas-vardhaka.",
      dosha=(-2, -2, 1), ritu=ALL_RITU,
      pathya_for=("constipation", "acidity", "anemia", "migraine"),
      apathya_for=("obesity", "high_cholesterol", "fatty_liver"),
      nutrition=N(900, fat_g=99.5, source="usda", **_FAT), **_OIL),

    F("Olive Oil", id="olive_oil",
      rasa=("madhura", "kashaya"), guna=("guru", "snigdha"), virya="shita",
      vipaka="madhura",
      dosha=(-1, -1, 1), ritu=("grishma", "sharad"),
      pathya_for=("high_cholesterol", "hypertension"),
      apathya_for=("obesity",),
      diet_types=("vegetarian", "vegan"), vegan=True,
      nutrition=N(884, fat_g=100.0, source="usda", **_FAT),
      **{**_OIL, "ref": "modern_extrapolated",
         "varga": "No classical entry. Reasoned from Taila Varga as a madhura-kashaya "
                  "sneha of shita virya — nearest to Narikela Taila in guna, milder in "
                  "its Kapha effect. Extrapolated, not cited."}),
]
