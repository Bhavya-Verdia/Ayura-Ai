"""The ten dairy rows.

The generator's `dairy` default is `rasa: ["sweet"], virya: cooling, vipaka: sweet,
dosha: (-1, -1, +1), agni: heavy`, with curd picked out by name for sour rasa and
heating virya — but keeping `vipaka: sweet` from the category. Dadhi has amla vipaka;
`curd_yogurt` is one of the five rows in the current library whose vipaka contradicts
its own rasa, and it could not be otherwise because Amla Vipaka is a value the
generator never writes.

The split that matters most here is Dadhi against Takra. Curd is guru, abhishyandi,
Kapha-Pitta vardhaka and the first Apathya named for Amavata; buttermilk is laghu,
ruksha, deepana and the classical Grahani medicine. They are made of the same milk and
they are opposite prescriptions. Under one `dairy` category profile they were the same
row with a different name.

`ghee` and `ghee_oil` are the same dravya under two ids, inherited from the generator's
category lists — ghee appears in both `dairy` and `oil`. Carried forward unchanged so
the migration maps one-to-one; it should collapse to one row once the library is
complete and every consumer of the old ids has been checked.

AUTHORED, NOT CLINICALLY REVIEWED. Macros from USDA FoodData Central.
"""

from diet_library.schema import ALL_RITU
from diet_library.spec import F, N

_DAIRY = dict(category="dairy", prep_state="prepared", ref="bhavaprakasha",
              varga="Dugdha", meal=("breakfast", "lunch", "dinner"), prep_minutes=2,
              allergen=True)

DAIRY = [
    F("Godugdha (Cow's Milk)", id="milk_full_fat",
      rasa=("madhura",), guna=("guru", "snigdha", "manda", "picchila"),
      virya="shita", vipaka="madhura",
      prabhava="Ojas-vardhaka and Rasayana — the action that makes milk a therapy "
               "rather than a food (Charaka Sutrasthana 27).",
      dosha=(-2, -2, 2), ritu=ALL_RITU,
      pathya_for=("acidity", "anemia", "constipation"),
      apathya_for=("obesity", "asthma", "hypothyroid", "fatty_liver"),
      viruddha_with=("curd_yogurt", "lemon_water", "banana", "fish"),
      nutrition=N(61, 3.2, 4.8, 3.3, 0.0, source="usda"), **_DAIRY),

    F("Dadhi (Curd)", id="curd_yogurt",
      rasa=("amla", "madhura"), guna=("guru", "snigdha", "picchila"),
      virya="ushna", vipaka="amla",
      dosha=(-1, 2, 2), ritu=("shishira", "hemanta"),
      pathya_for=("grahani",),
      apathya_for=("amavata", "psoriasis", "asthma", "acidity", "obesity", "anemia"),
      viruddha_with=("milk_full_fat", "banana", "fish"),
      nutrition=N(61, 3.5, 4.7, 3.3, 0.0, source="usda"), **_DAIRY),

    F("Takra (Buttermilk)", id="buttermilk_chaas",
      rasa=("amla", "kashaya"), guna=("laghu", "ruksha"), virya="ushna", vipaka="amla",
      prabhava="Grahi and deepana — the classical Grahani medicine, and the reason "
               "Takra is prescribed where Dadhi, made from the same milk, is withheld "
               "(Charaka Chikitsa 15).",
      dosha=(-1, 0, -1), ritu=ALL_RITU,
      pathya_for=("grahani", "ibs", "arsha", "obesity", "fatty_liver"),
      apathya_for=("acidity",),
      nutrition=N(40, 3.3, 4.8, 0.9, 0.0, source="usda"), **_DAIRY),

    F("Kilata (Paneer)", id="paneer",
      rasa=("madhura",), guna=("guru", "snigdha", "picchila"), virya="shita",
      vipaka="madhura",
      dosha=(-1, -1, 2), ritu=("shishira", "hemanta", "vasanta"),
      pathya_for=("anemia",),
      apathya_for=("obesity", "high_cholesterol", "hypothyroid", "asthma"),
      nutrition=N(265, 18.3, 1.2, 20.8, 0.0, source="usda"), **_DAIRY),

    F("Goghrita (Cow's Ghee)", id="ghee",
      rasa=("madhura",), guna=("guru", "snigdha", "mridu"), virya="shita",
      vipaka="madhura",
      prabhava="Agni-deepana while being snigdha and guru — the classical exception "
               "that makes Ghrita the one fat given to a weak Agni rather than withheld "
               "from it (Charaka Sutrasthana 13). Ojas-vardhaka.",
      dosha=(-2, -2, 1), ritu=ALL_RITU,
      pathya_for=("constipation", "acidity", "anemia", "migraine"),
      apathya_for=("obesity", "high_cholesterol", "fatty_liver"),
      viruddha_with=("honey",),
      nutrition=N(900, 0.0, 0.0, 99.5, 0.0, source="usda"), **_DAIRY),

    F("Navanita (Fresh Butter)", id="butter",
      rasa=("madhura", "kashaya"), guna=("guru", "snigdha", "mridu"),
      virya="shita", vipaka="madhura",
      prabhava="Fresh Navanita is deepana and grahi where aged butter is neither — "
               "the classical distinction, and why it is given in Arsha and Grahani.",
      dosha=(-2, -1, 1), ritu=("shishira", "hemanta"),
      pathya_for=("arsha", "grahani", "anemia"),
      apathya_for=("obesity", "high_cholesterol", "fatty_liver"),
      nutrition=N(717, 0.85, 0.06, 81.1, 0.0, source="usda"), **_DAIRY),

    F("Mastu (Whey)", id="whey",
      rasa=("amla", "kashaya"), guna=("laghu", "ruksha"), virya="ushna", vipaka="amla",
      prabhava="Srotoshodhaka — it clears the channels, which is why the watery part "
               "of curd is given where curd itself blocks them.",
      dosha=(-1, 0, -1), ritu=ALL_RITU,
      pathya_for=("obesity", "constipation", "fatty_liver"),
      apathya_for=("acidity",),
      nutrition=N(27, 0.85, 5.1, 0.36, 0.0, source="usda"), **_DAIRY),

    F("Santanika (Cream)", id="cream",
      rasa=("madhura",), guna=("guru", "snigdha", "picchila"), virya="shita",
      vipaka="madhura",
      dosha=(-2, -1, 2), ritu=("shishira", "hemanta"),
      pathya_for=("anemia",),
      apathya_for=("obesity", "high_cholesterol", "fatty_liver", "hypothyroid"),
      nutrition=N(340, 2.8, 2.8, 36.1, 0.0, source="usda"), **_DAIRY),

    F("Cottage Cheese", id="cottage_cheese",
      rasa=("madhura", "amla"), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, 0, 2), ritu=("shishira", "hemanta", "vasanta"),
      apathya_for=("obesity", "hypothyroid", "asthma"),
      nutrition=N(98, 11.1, 3.4, 4.3, 0.0, source="usda"),
      **{**_DAIRY, "ref": "modern_extrapolated",
         "varga": "No classical entry. Reasoned from Kilata (curdled milk solids), with "
                  "an amla anurasa the acid-set curdling adds and less guru than paneer "
                  "for its lower fat. Extrapolated, not cited."}),

    F("Lassi (Sweetened Takra)", id="lassi",
      rasa=("madhura", "amla"), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      prabhava="Sweetening and thickening reverse Takra's action: sweet Lassi is guru "
               "and Kapha-vardhaka where the Takra it is made from is laghu and "
               "Kapha-hara. The preparation, not the milk, decides.",
      dosha=(-1, -1, 2), ritu=("grishma", "sharad"),
      pathya_for=("acidity",),
      apathya_for=("obesity", "hypothyroid", "asthma", "fatty_liver"),
      nutrition=N(110, 3.0, 17.0, 3.0, 0.0, source="authored_estimate"), **_DAIRY),
]
