"""The fifteen nuts and seeds.

The generator's `nut_seed` default is `rasa: ["sweet"], virya: heating, vipaka: sweet,
dosha: (-1, +1, +1)`. That is close to right for the tree nuts and wrong for the seeds:
Makhana is shita and given in pregnancy, pumpkin and melon seeds are shita and mutrala,
and Tila and Atasi have katu vipaka against a madhura rasa.

`peanuts` and `peanuts_roasted` are the same dravya in two states, and unlike the other
inherited duplicates that distinction is real — roasting turns Mandapi more ruksha and
more Vidahi. They are kept as two rows and `prep_state` says which is which.

Macros are per 100 g raw, as these are eaten.

AUTHORED, NOT CLINICALLY REVIEWED. Macros from USDA FoodData Central unless marked.
"""

from diet_library.spec import F, N

_N = dict(category="nut_seed", prep_state="raw", meal=("snack",), prep_minutes=1,
          diet_types=("vegetarian", "vegan"), vegan=True, allergen=True,
          ref="bhavaprakasha", varga="Vatadi")

NUTS_SEEDS = [
    F("Badama (Almonds)", id="almonds",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="ushna", vipaka="madhura",
      prabhava="Medhya, Balya and Vrishya — the actions that make Badama a Rasayana "
               "rather than a fat, and the reason it is soaked and peeled before use.",
      dosha=(-2, 1, 2), ritu=("shishira", "hemanta", "vasanta"),
      pathya_for=("anemia", "constipation"),
      apathya_for=("acidity", "obesity", "high_cholesterol", "psoriasis"),
      nutrition=N(579, 21.2, 21.6, 49.9, 12.5, source="usda"), **_N),

    F("Akshota (Walnuts)", id="walnuts",
      rasa=("madhura", "kashaya"), guna=("guru", "snigdha"), virya="ushna",
      vipaka="madhura",
      dosha=(-2, 1, 1), ritu=("shishira", "hemanta"),
      pathya_for=("constipation", "high_cholesterol"),
      apathya_for=("acidity", "obesity"),
      nutrition=N(654, 15.2, 13.7, 65.2, 6.7, source="usda"), **_N),

    F("Kaju (Cashews)", id="cashews",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="ushna", vipaka="madhura",
      prabhava="The one sweet nut the texts warn against in Pitta — Kaju is ushna and "
               "Vidahi where its madhura rasa says it should cool.",
      dosha=(-2, 2, 2), ritu=("shishira", "hemanta"),
      apathya_for=("acidity", "psoriasis", "obesity", "high_cholesterol", "migraine"),
      nutrition=N(553, 18.2, 30.2, 43.9, 3.3, source="usda"), **_N),

    F("Pistachios", id="pistachios",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="ushna", vipaka="madhura",
      dosha=(-2, 1, 2), ritu=("shishira", "hemanta"),
      apathya_for=("acidity", "obesity", "hypertension"),
      nutrition=N(560, 20.2, 27.2, 45.3, 10.6, source="usda"), **_N),

    F("Mandapi (Roasted Peanuts)", id="peanuts_roasted",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha", "tikshna"), virya="ushna",
      vipaka="madhura",
      prabhava="Roasting turns Mandapi ruksha and more Vidahi than the raw seed — the "
               "same dravya, a sharper one, and the reason roasted peanuts sit worse "
               "in Amlapitta than boiled ones.",
      dosha=(-1, 2, 1), ritu=("shishira", "hemanta"),
      apathya_for=("acidity", "psoriasis", "obesity", "migraine", "high_cholesterol"),
      nutrition=N(587, 24.4, 21.5, 49.7, 8.0, source="usda"),
      **{**_N, "prep_state": "roasted",
         "varga": "Shimbi Dhanya — Mandapi, roasted"}),

    F("Tila (Sesame Seeds)", id="sesame_seeds_til",
      rasa=("madhura", "tikta", "kashaya"), guna=("guru", "snigdha"), virya="ushna",
      vipaka="katu",
      prabhava="Balya and Vata-hara, and the Kushtha caution that comes with it — Tila "
               "with milk is named Viruddha in the Kushtha Nidana (Charaka Chikitsa 7).",
      dosha=(-2, 1, 1), ritu=("shishira", "hemanta"),
      pathya_for=("constipation", "anemia", "amavata"),
      apathya_for=("psoriasis", "acidity", "obesity"),
      viruddha_with=("milk_full_fat",),
      nutrition=N(573, 17.7, 23.4, 49.7, 11.8, source="usda"),
      **{**_N, "varga": "Uma — Tila"}),

    F("Atasi (Flax Seeds)", id="flax_seeds",
      rasa=("madhura", "kashaya"), guna=("guru", "snigdha", "picchila"), virya="ushna",
      vipaka="katu",
      prabhava="Ushna virya and katu vipaka against a madhura-kashaya rasa — the "
               "classical caution on Atasi, and why it is a Vata-Kapha seed rather "
               "than a cooling one.",
      dosha=(-2, 1, 0), ritu=("shishira", "hemanta"),
      pathya_for=("pcos", "constipation", "high_cholesterol", "hypothyroid"),
      apathya_for=("acidity", "psoriasis"),
      nutrition=N(534, 18.3, 28.9, 42.2, 27.3, source="usda"),
      **{**_N, "varga": "Uma — Atasi"}),

    F("Kushmanda Bija (Pumpkin Seeds)", id="pumpkin_seeds",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      prabhava="Krimighna and Mutrala — the anthelmintic and diuretic actions the "
               "texts give Kushmanda seed, neither of which follows from its rasa.",
      dosha=(-1, -1, 1), ritu=("grishma", "sharad"),
      pathya_for=("pcos", "kidney_disease", "anemia"),
      apathya_for=("obesity",),
      nutrition=N(559, 30.2, 10.7, 49.1, 6.0, source="usda"),
      **{**_N, "varga": "Shaka — Kushmanda, seed"}),

    F("Kharbuja Bija (Melon Seeds / Magaz)", id="melon_seeds_magaz",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      prabhava="Mutrala and Pittahara — one of the Chatur Bija, given for urinary heat "
               "where its guru-snigdha guna alone would suggest otherwise.",
      dosha=(-1, -2, 1), ritu=("grishma", "sharad"),
      pathya_for=("kidney_disease", "acidity"),
      apathya_for=("obesity",),
      nutrition=N(557, 28.3, 15.0, 47.4, 6.0, source="authored_estimate"),
      **{**_N, "varga": "Chatur Bija"}),

    F("Kalinga Bija (Watermelon Seeds)", id="watermelon_seeds",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -1, 1), ritu=("grishma", "sharad"),
      pathya_for=("kidney_disease",),
      nutrition=N(557, 28.3, 15.3, 47.4, 6.0, source="usda"),
      **{**_N, "varga": "Chatur Bija"}),

    F("Padmabija (Makhana / Fox Nuts)", id="fox_nuts_makhana",
      rasa=("madhura", "kashaya"), guna=("guru", "snigdha", "sthira"), virya="shita",
      vipaka="madhura",
      prabhava="Garbhasthapana and Vrishya — Makhana is the one nut given freely in "
               "pregnancy, which is why it is here and Kaju is not.",
      dosha=(-1, -1, 1), ritu=("grishma", "sharad", "varsha"),
      pathya_for=("acidity", "kidney_disease", "anemia"),
      apathya_for=("obesity",),
      nutrition=N(347, 9.7, 76.9, 0.1, 14.5, source="ifct2017"),
      **{**_N, "prep_state": "roasted", "allergen": False,
         "varga": "Padma — bija"}),

    F("Sunflower Seeds", id="sunflower_seeds",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="ushna", vipaka="madhura",
      dosha=(-1, 1, 1), ritu=("shishira", "hemanta"),
      pathya_for=("high_cholesterol",),
      apathya_for=("acidity", "obesity"),
      nutrition=N(584, 20.8, 20.0, 51.5, 8.6, source="usda"),
      **{**_N, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — a New World seed. Reasoned from the Vatadi "
                  "Varga as a guru, snigdha, ushna oilseed, nearest to Tila in guna "
                  "but without its tikta rasa. Extrapolated, not cited."}),

    F("Chia Seeds", id="chia_seeds",
      rasa=("madhura", "kashaya"), guna=("guru", "picchila", "snigdha"), virya="shita",
      vipaka="madhura",
      dosha=(-1, -1, 0), ritu=("grishma", "sharad"),
      pathya_for=("constipation", "high_cholesterol", "diabetes", "acidity"),
      nutrition=N(486, 16.5, 42.1, 30.7, 34.4, source="usda"),
      **{**_N, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — a New World seed. Reasoned from Atasi for its "
                  "picchila swelling in water, but shita rather than ushna: it lacks "
                  "the heat Atasi is cautioned for. Extrapolated, not cited."}),

    F("Hemp Seeds", id="hemp_seeds",
      rasa=("madhura", "kashaya"), guna=("guru", "snigdha"), virya="ushna",
      vipaka="madhura",
      dosha=(-1, 1, 1), ritu=("shishira", "hemanta"),
      pathya_for=("high_cholesterol", "amavata"),
      apathya_for=("acidity",),
      nutrition=N(553, 31.6, 8.7, 48.8, 4.0, source="usda"),
      **{**_N, "ref": "modern_extrapolated",
         "varga": "The plant is Vijaya in the nighantus but the hulled seed is a modern "
                  "food and carries none of Vijaya's action. Reasoned from the Vatadi "
                  "Varga as a guru, snigdha, ushna oilseed. Extrapolated, not cited."}),

    F("Chilgoza (Pine Nuts)", id="pine_nuts",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="ushna", vipaka="madhura",
      dosha=(-2, 1, 1), ritu=("shishira", "hemanta"),
      pathya_for=("constipation", "anemia"),
      apathya_for=("acidity", "obesity"),
      nutrition=N(673, 13.7, 13.1, 68.4, 3.7, source="usda"), **_N),
]
