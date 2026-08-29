"""The twenty fruits.

The generator's `fruit` default is `rasa: ["sweet"], virya: cooling, vipaka: sweet,
dosha: (-1, -1, +1), agni: easy` for all twenty, with apple and pomegranate picked out
by name for a Pitta override. Under it Jambu and Kharjura are the same row — Jambu is
the classical Prameha fruit, kashaya, ruksha and Kapha-Meda reducing; Kharjura is
brimhana and builds both.

Two classical exceptions the default could not hold:

  * **Kadali (banana)** has *amla* vipaka against a madhura-kashaya rasa. It is one of
    the reasons Amla Vipaka being unreachable matters — banana with milk is Viruddha
    precisely because of it.
  * **Amalaki** is amla-dominant with *madhura* vipaka and shita virya, which is why it
    is the one sour fruit given freely in Pitta.

`apple` is authored raw. `ayurvedic_foods.json` — the 25 hand-written entries that sit
beside the derived file in the same RAG collection — says raw apple raises Vata; the
derived fruit default says it lowers it. This row agrees with the authored file.

AUTHORED, NOT CLINICALLY REVIEWED. Macros from USDA FoodData Central unless marked.
"""

from diet_library.spec import F, N

_F = dict(category="fruit", prep_state="ripe", meal=("breakfast", "snack"),
          prep_minutes=2, diet_types=("vegetarian", "vegan"), vegan=True,
          ref="bhavaprakasha", varga="Amradi Phala")

FRUITS = [
    F("Kadali (Banana)", id="banana",
      rasa=("madhura", "kashaya"), guna=("guru", "snigdha", "picchila"), virya="shita",
      vipaka="amla",
      prabhava="Amla vipaka against a madhura-kashaya rasa — the classical exception "
               "for Kadali, and the reason banana with milk is named Viruddha.",
      dosha=(-1, 0, 2), ritu=("grishma", "sharad"),
      pathya_for=("acidity", "constipation", "hypertension"),
      apathya_for=("diabetes", "obesity", "asthma", "hypothyroid"),
      viruddha_with=("milk_full_fat", "curd_yogurt"),
      nutrition=N(89, 1.1, 22.8, 0.3, 2.6, source="usda"), **_F),

    F("Seva (Apple, Raw)", id="apple",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita",
      vipaka="madhura",
      dosha=(1, -1, 0), ritu=("sharad", "hemanta"),
      pathya_for=("high_cholesterol", "diabetes", "acidity"),
      apathya_for=("ibs", "grahani"),
      nutrition=N(52, 0.3, 13.8, 0.2, 2.4, source="usda"),
      **{**_F, "prep_state": "raw"}),

    F("Amra (Mango)", id="mango",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="ushna", vipaka="madhura",
      prabhava="Ripe Amra is Vrishya and Balya, and ushna despite a purely madhura "
               "rasa — the reason it is a summer fruit that nonetheless aggravates "
               "Pitta in quantity.",
      dosha=(-2, 1, 2), ritu=("grishma",),
      pathya_for=("anemia",),
      apathya_for=("diabetes", "obesity", "acidity", "psoriasis"),
      nutrition=N(60, 0.8, 15.0, 0.4, 1.6, source="usda"), **_F),

    F("Eranda-karkati (Papaya)", id="papaya",
      rasa=("madhura",), guna=("guru", "tikshna"), virya="ushna", vipaka="katu",
      prabhava="Deepana and Bhedana — the digestive and purgative action that makes "
               "papaya a medicine for a sluggish gut and a uterine stimulant in "
               "pregnancy. Both come from the same Prabhava.",
      dosha=(-1, 1, -1), ritu=("varsha", "sharad"),
      pathya_for=("constipation", "grahani", "obesity"),
      apathya_for=("pregnancy", "acidity"),
      nutrition=N(43, 0.5, 10.8, 0.3, 1.7, source="usda"), **_F),

    F("Dadima (Pomegranate)", id="pomegranate",
      rasa=("madhura", "amla", "kashaya"), guna=("laghu", "snigdha"), virya="shita",
      vipaka="madhura",
      prabhava="Tridoshaghna and Hridya — the sweet Dadima is one of the few fruits "
               "the texts give to all three Doshas, and the one prescribed in Grahani "
               "and in convalescence.",
      dosha=(-1, -1, -1), ritu=("sharad", "hemanta"),
      pathya_for=("grahani", "anemia", "acidity", "hypertension", "ibs"),
      nutrition=N(83, 1.7, 18.7, 1.2, 4.0, source="usda"), **_F),

    F("Amalaki (Amla)", id="amla",
      rasa=("amla", "kashaya", "madhura"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="madhura",
      prabhava="Amla rasa with shita virya and madhura vipaka — the combination is "
               "unique to Amalaki and is why the one sour fruit in the pharmacopoeia "
               "is given freely in Pitta. Rasayana and tridoshaghna.",
      dosha=(-1, -2, -1), ritu=("sharad", "hemanta", "shishira"),
      pathya_for=("acidity", "diabetes", "anemia", "psoriasis", "high_cholesterol",
                  "hypothyroid"),
      nutrition=N(44, 0.9, 10.2, 0.6, 4.3, source="usda"), **_F),

    F("Narikela (Fresh Coconut)", id="coconut",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -2, 2), ritu=("grishma", "sharad"),
      pathya_for=("acidity", "psoriasis", "kidney_disease"),
      apathya_for=("obesity", "high_cholesterol", "hypothyroid"),
      nutrition=N(354, 3.3, 15.2, 33.5, 9.0, source="usda"), **_F),

    F("Kharjura (Dates)", id="dates",
      rasa=("madhura",), guna=("guru", "snigdha", "mridu"), virya="shita",
      vipaka="madhura",
      prabhava="Brimhana and Balya — Kharjura is the classical convalescent fruit, "
               "given to rebuild after depletion where its guru guna would otherwise "
               "argue against it.",
      dosha=(-2, -2, 2), ritu=("shishira", "hemanta"),
      pathya_for=("anemia", "constipation", "acidity"),
      apathya_for=("diabetes", "obesity", "hypothyroid"),
      nutrition=N(277, 1.8, 75.0, 0.2, 6.7, source="usda"), **_F),

    F("Anjeera (Figs)", id="figs",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -1, 1), ritu=("varsha", "sharad"),
      pathya_for=("constipation", "anemia", "acidity"),
      apathya_for=("diabetes", "obesity"),
      nutrition=N(74, 0.8, 19.2, 0.3, 2.9, source="usda"), **_F),

    F("Perukam (Guava)", id="guava",
      rasa=("madhura", "amla", "kashaya"), guna=("guru", "ruksha"), virya="shita",
      vipaka="madhura",
      dosha=(1, -1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("diabetes", "constipation", "high_cholesterol"),
      apathya_for=("ibs", "grahani"),
      nutrition=N(68, 2.6, 14.3, 1.0, 5.4, source="usda"), **_F),

    F("Kalinga (Watermelon)", id="watermelon",
      rasa=("madhura",), guna=("guru", "snigdha", "drava"), virya="shita",
      vipaka="madhura",
      prabhava="Mutrala — the diuretic action is why Kalinga is given in Grishma and "
               "in urinary heat, and why it is not simply a heavy sweet fruit.",
      dosha=(1, -2, 1), ritu=("grishma",),
      pathya_for=("kidney_disease", "acidity"),
      apathya_for=("diabetes", "obesity", "ibs"),
      nutrition=N(30, 0.6, 7.6, 0.2, 0.4, source="usda"), **_F),

    F("Nagaranga (Orange)", id="orange",
      rasa=("madhura", "amla"), guna=("laghu", "snigdha"), virya="shita",
      vipaka="madhura",
      dosha=(-1, 0, 1), ritu=("hemanta", "shishira"),
      pathya_for=("anemia", "constipation"),
      apathya_for=("acidity", "asthma", "amavata"),
      viruddha_with=("milk_full_fat",),
      nutrition=N(47, 0.9, 11.8, 0.1, 2.4, source="usda"), **_F),

    F("Mosambi (Sweet Lime)", id="mosambi_sweet_lime",
      rasa=("madhura", "amla"), guna=("laghu", "snigdha"), virya="shita",
      vipaka="madhura",
      dosha=(-1, -1, 1), ritu=("grishma", "sharad"),
      pathya_for=("acidity", "anemia", "fatty_liver"),
      apathya_for=("asthma",),
      viruddha_with=("milk_full_fat",),
      nutrition=N(43, 0.8, 9.3, 0.3, 0.5, source="authored_estimate"), **_F),

    F("Nashpati (Pear)", id="pear",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita",
      vipaka="madhura",
      dosha=(1, -1, 0), ritu=("sharad", "hemanta"),
      pathya_for=("constipation", "high_cholesterol"),
      apathya_for=("ibs", "grahani"),
      nutrition=N(57, 0.4, 15.2, 0.1, 3.1, source="usda"), **_F),

    F("Jambu (Jamun)", id="jamun",
      rasa=("kashaya", "amla", "madhura"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="katu",
      prabhava="The classical Prameha fruit — Jambu's Kapha-Meda reducing action is "
               "the one the texts single it out for, and the seed is used where the "
               "fruit is not.",
      dosha=(2, -1, -2), ritu=("grishma", "varsha"),
      pathya_for=("diabetes", "obesity", "grahani", "high_cholesterol"),
      apathya_for=("constipation", "ibs"),
      nutrition=N(60, 0.7, 15.6, 0.2, 0.9, source="ifct2017"), **_F),

    F("Draksha (Grapes)", id="grapes",
      rasa=("madhura",), guna=("guru", "snigdha", "mridu"), virya="shita",
      vipaka="madhura",
      prabhava="Phalottama — the texts call Draksha the best of fruits and give it in "
               "all three Doshas, which no other madhura, guru fruit here earns.",
      dosha=(-2, -2, 1), ritu=("sharad", "hemanta"),
      pathya_for=("acidity", "constipation", "anemia", "kidney_disease"),
      apathya_for=("diabetes", "obesity"),
      nutrition=N(69, 0.7, 18.1, 0.2, 0.9, source="usda"), **_F),

    F("Chikoo (Sapota)", id="chikoo_sapota",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -1, 2), ritu=("grishma", "varsha"),
      pathya_for=("constipation", "anemia"),
      apathya_for=("diabetes", "obesity", "hypothyroid"),
      nutrition=N(83, 0.4, 20.0, 1.1, 5.3, source="usda"),
      **{**_F, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — sapota reaches India from the New World in the "
                  "colonial period. Reasoned from the Amradi Phala Varga as a madhura, "
                  "guru, shita fruit, nearest to Kharjura in guna. Extrapolated, "
                  "not cited."}),

    F("Pineapple", id="pineapple",
      rasa=("madhura", "amla"), guna=("guru", "tikshna"), virya="ushna", vipaka="amla",
      dosha=(-1, 1, -1), ritu=("grishma", "varsha"),
      pathya_for=("obesity", "constipation"),
      apathya_for=("pregnancy", "acidity", "psoriasis", "amavata"),
      nutrition=N(50, 0.5, 13.1, 0.1, 1.4, source="usda"),
      **{**_F, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — a New World fruit. Reasoned as madhura-amla, "
                  "tikshna and ushna; the pregnancy caution is the one folk and modern "
                  "sources agree on and matches papaya's Bhedana action. Extrapolated, "
                  "not cited."}),

    F("Kiwi", id="kiwi",
      rasa=("madhura", "amla"), guna=("laghu", "snigdha"), virya="shita", vipaka="amla",
      dosha=(-1, 0, 0), ritu=("hemanta", "shishira"),
      pathya_for=("constipation", "anemia"),
      apathya_for=("acidity",),
      nutrition=N(61, 1.1, 14.7, 0.5, 3.0, source="usda"),
      **{**_F, "ref": "modern_extrapolated",
         "varga": "No nighantu entry. Reasoned from the Amradi Phala Varga as a "
                  "madhura-amla, laghu, shita fruit — nearest to Nagaranga in action, "
                  "milder in its Kapha effect. Extrapolated, not cited."}),

    F("Strawberry", id="strawberry",
      rasa=("madhura", "amla"), guna=("laghu", "snigdha"), virya="shita", vipaka="amla",
      dosha=(-1, -1, 0), ritu=("vasanta", "grishma"),
      pathya_for=("acidity", "high_cholesterol"),
      nutrition=N(32, 0.7, 7.7, 0.3, 2.0, source="usda"),
      **{**_F, "ref": "modern_extrapolated",
         "varga": "No nighantu entry. Reasoned from the Amradi Phala Varga as a light, "
                  "madhura-amla, shita fruit. Extrapolated, not cited."}),
]
