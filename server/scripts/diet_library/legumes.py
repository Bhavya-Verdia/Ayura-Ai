"""The twenty legumes.

The generator's `legume` default is `rasa: ["sweet", "astringent"], virya: cooling,
vipaka: pungent, dosha: (+1, -1, -1), agni: heavy` for all twenty. Under it Mudga and
Masha are the same row.

They are the two poles of the Shimbi Varga. Mudga is laghu, ruksha, shita and called
the best of legumes — the one given in fever, in convalescence and to a weak Agni.
Masha is guru, snigdha, picchila, ushna, Vata-hara and Kapha-Pitta vardhaka — the one
given for strength and withheld from almost every condition this app tracks. A single
category profile made them interchangeable, and the diet engine composes from whatever
it is handed.

Macros are per 100 g **cooked**, matching the engine's 100 g legume portion. Peanut and
besan are the exceptions and are recorded as eaten — raw and as flour.

`kidney_beans` and `rajma` are one dravya under two ids, as are `tofu_firm` and
`vegan_paneer_tofu` across two categories; both pairs are inherited from the file this
replaces and carried forward so the migration maps one-to-one. That fact belongs here
and not in the rows' `nighantu_ref`, which is seeded verbatim into the nutrition corpus
and read back as a source line when a plan is written.

AUTHORED, NOT CLINICALLY REVIEWED. Macros from USDA FoodData Central unless marked.
"""

from diet_library.spec import F, N

_L = dict(category="legume", meal=("lunch", "dinner"), prep_minutes=30,
          diet_types=("vegetarian", "vegan"), vegan=True, ref="bhavaprakasha",
          varga="Shimbi Dhanya")

LEGUMES = [
    F("Mudga (Yellow Moong Dal)", id="moong_dal_yellow", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="katu",
      prabhava="Shreshtha among the Shimbi — the one legume the texts call tridoshaghna "
               "and prescribe in fever, in convalescence and to a weak Agni, where "
               "every other legume in this varga is withheld.",
      dosha=(0, -1, -1), ritu=("grishma", "sharad", "varsha"),
      pathya_for=("grahani", "ibs", "anemia", "obesity", "diabetes", "amavata"),
      nutrition=N(105, 7.0, 19.0, 0.4, 4.1, source="usda"), **_L),

    F("Mudga (Whole Green Gram)", id="moong_dal_green", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="katu",
      dosha=(1, -1, -1), ritu=("grishma", "sharad"),
      pathya_for=("obesity", "diabetes", "high_cholesterol"),
      apathya_for=("ibs",),
      nutrition=N(105, 7.0, 19.0, 0.4, 7.6, source="usda"), **_L),

    F("Mudga (Sprouted Moong)", id="sprouted_moong", prep_state="sprouted",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha", "chala"), virya="shita",
      vipaka="katu",
      dosha=(2, -1, -1), ritu=("vasanta", "grishma"),
      pathya_for=("obesity", "diabetes", "anemia"),
      apathya_for=("ibs", "grahani", "amavata"),
      nutrition=N(30, 3.0, 5.9, 0.2, 1.8, source="usda"),
      **{**_L, "meal": ("breakfast", "snack"), "prep_minutes": 5}),

    F("Masura (Masoor Dal)", id="masoor_dal", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="ushna",
      vipaka="katu",
      prabhava="Grahi — it binds the stool, which is why Masura is given in loose "
               "motions and is the legume withheld in constipation.",
      dosha=(1, 0, -1), ritu=("shishira", "hemanta", "varsha"),
      pathya_for=("grahani", "obesity"),
      apathya_for=("constipation", "acidity"),
      nutrition=N(116, 9.0, 20.1, 0.4, 7.9, source="usda"), **_L),

    F("Masura (Whole Brown Lentil)", id="lentils_brown", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="ushna", vipaka="katu",
      dosha=(2, 0, -1), ritu=("shishira", "hemanta"),
      pathya_for=("anemia", "obesity"),
      apathya_for=("ibs", "constipation"),
      nutrition=N(116, 9.0, 20.1, 0.4, 7.9, source="usda"), **_L),

    F("Chanaka (Chana Dal)", id="chana_dal", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("diabetes", "obesity", "high_cholesterol"),
      apathya_for=("ibs", "grahani", "arsha"),
      nutrition=N(164, 8.9, 27.4, 2.6, 7.6, source="usda"), **_L),

    F("Chanaka (Kabuli Chana)", id="chhole", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita", vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("diabetes", "anemia"),
      apathya_for=("ibs", "grahani", "arsha", "amavata"),
      nutrition=N(164, 8.9, 27.4, 2.6, 7.6, source="usda"), **_L),

    F("Chanaka Churna (Besan)", id="chickpea_flour_besan", prep_state="dry",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira", "vasanta"),
      pathya_for=("diabetes",),
      apathya_for=("ibs", "grahani"),
      nutrition=N(387, 22.4, 57.8, 6.7, 10.8, source="usda"), **_L),

    F("Adhaki (Toor Dal)", id="toor_dal", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="katu",
      dosha=(1, -1, -1), ritu=("grishma", "sharad", "hemanta"),
      pathya_for=("obesity", "high_cholesterol"),
      apathya_for=("ibs", "arsha"),
      nutrition=N(121, 7.0, 23.0, 0.4, 5.0, source="usda"), **_L),

    F("Masha (Urad Dal)", id="urad_dal", prep_state="cooked",
      rasa=("madhura",), guna=("guru", "snigdha", "picchila"), virya="ushna",
      vipaka="madhura",
      prabhava="Ushna virya and Pitta-vardhaka against a madhura rasa that pacifies "
               "Pitta by rule — Masha is Balya and Vrishya, the strength-building "
               "legume, and the pole opposite Mudga in this varga. It is the black gram "
               "named first in the Amavata Apathya.",
      dosha=(-2, 2, 2), ritu=("shishira", "hemanta"),
      pathya_for=("constipation", "anemia"),
      apathya_for=("amavata", "obesity", "acidity", "psoriasis", "high_cholesterol",
                   "hypothyroid", "arsha"),
      nutrition=N(118, 7.5, 20.6, 0.5, 6.0, source="usda"), **_L),

    F("Rajamasha (Black-Eyed Peas)", id="black_eyed_peas", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita", vipaka="katu",
      dosha=(2, -1, -1), ritu=("varsha", "sharad"),
      pathya_for=("anemia", "diabetes"),
      apathya_for=("ibs", "grahani", "arsha"),
      nutrition=N(116, 7.7, 20.8, 0.5, 6.5, source="usda"), **_L),

    F("Kalaya (Green Peas)", id="green_peas", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita", vipaka="katu",
      dosha=(2, -1, -1), ritu=("shishira", "hemanta", "vasanta"),
      pathya_for=("diabetes", "obesity"),
      apathya_for=("ibs", "grahani", "amavata"),
      nutrition=N(84, 5.4, 15.6, 0.2, 5.5, source="usda"), **_L),

    F("Rajma (Kidney Beans)", id="rajma", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha", "sthira"), virya="shita",
      vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("diabetes",),
      apathya_for=("ibs", "grahani", "arsha", "amavata"),
      nutrition=N(127, 8.7, 22.8, 0.5, 6.4, source="usda"),
      **{**_L, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — the kidney bean is a New World crop. Reasoned "
                  "from the Shimbi Varga at its guru, ruksha, Vata-vardhaka end, "
                  "which is where its reputation for flatulence puts it. "
                  "Extrapolated, not cited."}),

    F("Kidney Beans", id="kidney_beans", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha", "sthira"), virya="shita",
      vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira"),
      apathya_for=("ibs", "grahani", "arsha", "amavata"),
      nutrition=N(127, 8.7, 22.8, 0.5, 6.4, source="usda"),
      **{**_L, "ref": "modern_extrapolated",
         "varga": "No classical entry. Reasoned from the Shimbi Varga as a guru, "
                  "ruksha, kashaya-madhura legume. Extrapolated, not cited."}),

    F("Black Beans", id="black_beans", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita", vipaka="katu",
      dosha=(2, 0, -1), ritu=("hemanta", "shishira"),
      pathya_for=("diabetes", "high_cholesterol"),
      apathya_for=("ibs", "grahani", "arsha"),
      nutrition=N(132, 8.9, 23.7, 0.5, 8.7, source="usda"),
      **{**_L, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — a New World crop. Reasoned from the Shimbi "
                  "Varga as guru, ruksha and Vata-vardhaka. Extrapolated, not cited."}),

    F("Soya Chunks", id="soya_chunks", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita", vipaka="katu",
      dosha=(2, 0, 0), ritu=("hemanta", "shishira"),
      apathya_for=("hypothyroid", "thyroid", "ibs", "pcos"), allergen=True,
      nutrition=N(105, 15.0, 8.0, 0.5, 4.0, source="authored_estimate"),
      **{**_L, "ref": "modern_extrapolated",
         "varga": "No nighantu entry, and the defatted extrusion has no dravya "
                  "analogue at all. Reasoned from the Shimbi Varga as guru and ruksha; "
                  "the thyroid caution is modern and does not come from the texts. "
                  "Extrapolated, not cited."}),

    F("Tofu (Firm)", id="tofu_firm", prep_state="prepared",
      rasa=("madhura", "kashaya"), guna=("guru", "picchila"), virya="shita",
      vipaka="madhura",
      dosha=(1, -1, 1), ritu=("grishma", "sharad"),
      apathya_for=("hypothyroid", "thyroid", "ibs", "pcos"), allergen=True,
      nutrition=N(76, 8.1, 1.9, 4.8, 0.3, source="usda"),
      **{**_L, "ref": "modern_extrapolated",
         "varga": "No classical entry. Reasoned from the Shimbi Varga curdled as "
                  "Kilata is. Extrapolated, not cited."}),

    F("Tempeh", id="tempeh", prep_state="fermented",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="ushna", vipaka="katu",
      dosha=(1, 1, 0), ritu=("hemanta", "shishira"),
      apathya_for=("amavata", "psoriasis", "hypothyroid", "migraine"), allergen=True,
      nutrition=N(192, 20.3, 7.6, 10.8, 4.0, source="usda"),
      **{**_L, "ref": "modern_extrapolated",
         "varga": "No nighantu entry. Reasoned as a Shimbi taken through mould "
                  "fermentation: ushna virya and katu vipaka arrive with it, and with "
                  "them the Amavata and Kushtha bars that attach to fermented food. "
                  "Extrapolated, not cited."}),

    F("Edamame", id="edamame", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita", vipaka="katu",
      dosha=(1, -1, 0), ritu=("grishma", "sharad"),
      apathya_for=("hypothyroid", "thyroid", "ibs"), allergen=True,
      nutrition=N(121, 11.9, 8.9, 5.2, 5.2, source="usda"),
      **{**_L, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — the green soybean. Reasoned from the Shimbi "
                  "Varga; lighter than the dried bean because it is eaten immature. "
                  "Extrapolated, not cited."}),

    F("Mandapi (Peanuts)", id="peanuts", prep_state="raw",
      rasa=("madhura", "kashaya"), guna=("guru", "snigdha"), virya="ushna",
      vipaka="madhura",
      prabhava="Ushna and Vidahi against a madhura rasa — the peanut heats and burns "
               "where its rasa says it should cool, which is the classical caution and "
               "the reason it is withheld in Amlapitta and Kushtha.",
      dosha=(-1, 2, 2), ritu=("shishira", "hemanta"),
      apathya_for=("acidity", "psoriasis", "obesity", "high_cholesterol", "migraine"),
      allergen=True,
      nutrition=N(567, 25.8, 16.1, 49.2, 8.5, source="usda"),
      **{**_L, "meal": ("snack",), "prep_minutes": 1,
         "varga": "Shimbi Dhanya — Mandapi, a later addition to the varga"}),
]
