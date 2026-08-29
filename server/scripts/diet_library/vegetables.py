"""The thirty-five vegetables — the category the derived library flattened hardest.

`seed_diet_foods.py` gives every one of these `rasa: ["bitter", "astringent"],
virya: cooling, vipaka: pungent, dosha: (+1, -1, -1), agni: easy`, then overrides a
handful by name. So in the file this replaces:

  * Pumpkin, sweet potato, yam and carrot are bitter-astringent. They are madhura.
  * Tomato is sour by a name override but keeps `vipaka: pungent` from the category;
    amla rasa yields amla vipaka.
  * Garlic and onion are bitter-astringent and cooling. Both are katu and ushna, and
    Lasuna is the classical Vata medicine — heating is the whole point of it.
  * Bitter gourd and pumpkin sit on identical Ayurvedic rows.

`spinach` and `palak` are the same leaf under two ids, and `corn_sweet` duplicates the
`corn` row in the grain category. Both are carried forward with the duplication stated,
so the migration maps one-to-one.

`ginger` here is Ardraka — fresh ginger — and is a different dravya from `ginger_dry_
saunth` in the spice tranche. Fresh is snigdha and katu-vipaka; dry is ruksha with
madhura vipaka. That distinction is the reason `prep_state` exists.

Macros are per 100 g raw for the leaves and salad vegetables, cooked for the roots and
gourds, matching how each is eaten.

AUTHORED, NOT CLINICALLY REVIEWED. Macros from USDA FoodData Central unless marked.
"""

from diet_library.spec import F, N

_V = dict(category="vegetable", prep_state="cooked", meal=("lunch", "dinner"),
          prep_minutes=15, diet_types=("vegetarian", "vegan"), vegan=True,
          ref="bhavaprakasha", varga="Shaka")
_RAW = {**_V, "prep_state": "raw", "prep_minutes": 5}

VEGETABLES = [
    # ── Leaves ────────────────────────────────────────────────────────────────
    F("Palakya (Spinach)", id="spinach",
      rasa=("madhura", "kashaya", "tikta"), guna=("guru", "ruksha"), virya="shita",
      vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira", "vasanta"),
      pathya_for=("anemia", "obesity", "diabetes"),
      apathya_for=("amavata", "kidney_disease", "ibs"),
      nutrition=N(23, 2.9, 3.6, 0.4, 2.2, source="usda"), **_V),

    F("Palakya (Palak)", id="palak",
      rasa=("madhura", "kashaya", "tikta"), guna=("guru", "ruksha"), virya="shita",
      vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira", "vasanta"),
      pathya_for=("anemia", "obesity", "diabetes"),
      apathya_for=("amavata", "kidney_disease", "ibs"),
      nutrition=N(23, 2.9, 3.6, 0.4, 2.2, source="usda"),
      **{**_V, "varga": "Shaka"}),

    F("Methika Patra (Fenugreek Leaves)", id="methi_fenugreek_leaves",
      rasa=("tikta", "kashaya"), guna=("laghu", "ruksha"), virya="ushna", vipaka="katu",
      prabhava="Deepana and Vata-hara despite a tikta-kashaya rasa that raises Vata by "
               "rule — the leaf is warming where the rasa is not, which is why Methi "
               "greens are a winter Shaka.",
      dosha=(-1, 1, -2), ritu=("hemanta", "shishira"),
      pathya_for=("diabetes", "obesity", "amavata", "high_cholesterol"),
      apathya_for=("acidity", "pregnancy"),
      nutrition=N(49, 4.4, 6.0, 0.9, 1.1, source="usda"), **_V),

    # ── Crucifers ─────────────────────────────────────────────────────────────
    F("Broccoli", id="broccoli",
      rasa=("tikta", "kashaya"), guna=("laghu", "ruksha"), virya="shita", vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("obesity", "diabetes", "high_cholesterol"),
      apathya_for=("hypothyroid", "thyroid", "ibs", "grahani"),
      nutrition=N(35, 2.4, 7.2, 0.4, 3.3, source="usda"),
      **{**_V, "ref": "modern_extrapolated",
         "varga": "No nighantu entry. Reasoned from the Shaka Varga at its tikta-kashaya, "
                  "laghu, ruksha end alongside the other crucifers; the goitrogen "
                  "caution is modern. Extrapolated, not cited."}),

    F("Cauliflower", id="cauliflower",
      rasa=("kashaya", "madhura"), guna=("laghu", "ruksha"), virya="shita", vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("obesity", "diabetes"),
      apathya_for=("hypothyroid", "thyroid", "ibs", "grahani", "amavata"),
      nutrition=N(25, 1.9, 5.0, 0.3, 2.0, source="usda"),
      **{**_V, "ref": "modern_extrapolated",
         "varga": "No nighantu entry. Reasoned with the other crucifers as laghu, "
                  "ruksha and markedly Vata-vardhaka — the flatulence is what the "
                  "classical Shaka cautions describe. Extrapolated, not cited."}),

    F("Cabbage", id="cabbage",
      rasa=("kashaya", "madhura"), guna=("laghu", "ruksha"), virya="shita", vipaka="katu",
      dosha=(2, -1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("obesity", "diabetes"),
      apathya_for=("hypothyroid", "thyroid", "ibs", "grahani", "amavata"),
      nutrition=N(25, 1.3, 5.8, 0.1, 2.5, source="usda"),
      **{**_V, "ref": "modern_extrapolated",
         "varga": "No nighantu entry. Reasoned with the other crucifers; strongly "
                  "Vata-vardhaka. Extrapolated, not cited."}),

    # ── Roots and tubers ──────────────────────────────────────────────────────
    F("Garjara (Carrot)", id="carrot",
      rasa=("madhura", "tikta"), guna=("laghu", "ruksha"), virya="ushna", vipaka="katu",
      prabhava="Deepana and Grahi — Garjara is warming and binding, which is why it is "
               "a winter root and not the cooling one its madhura rasa suggests.",
      dosha=(-1, 1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("anemia", "grahani", "constipation"),
      apathya_for=("acidity",),
      nutrition=N(41, 0.9, 9.6, 0.2, 2.8, source="usda"), **_V),

    F("Palanki (Beetroot)", id="beetroot",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="ushna", vipaka="madhura",
      dosha=(-1, 1, 1), ritu=("hemanta", "shishira"),
      pathya_for=("anemia", "constipation", "hypertension"),
      apathya_for=("diabetes", "acidity"),
      nutrition=N(44, 1.7, 10.0, 0.2, 2.0, source="usda"), **_V),

    F("Aluka (Potato)", id="potato",
      rasa=("madhura",), guna=("guru", "ruksha"), virya="shita", vipaka="madhura",
      prabhava="Vata-vardhaka despite madhura rasa and against shita virya, which "
               "would raise Vata anyway — Aluka is Vatala in the texts, the standard "
               "caution on the tuber, and the reason it is cooked with ajwain.",
      dosha=(2, -1, 1), ritu=("varsha", "sharad", "hemanta"),
      apathya_for=("diabetes", "obesity", "ibs", "amavata"),
      nutrition=N(77, 2.0, 17.5, 0.1, 2.2, source="usda"), **_V),

    F("Shakarkand (Sweet Potato)", id="sweet_potato",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -1, 2), ritu=("hemanta", "shishira"),
      pathya_for=("constipation", "anemia"),
      apathya_for=("diabetes", "obesity", "hypothyroid"),
      nutrition=N(86, 1.6, 20.1, 0.1, 3.0, source="usda"), **_V),

    F("Kanda (Yam)", id="yam",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="ushna",
      vipaka="madhura",
      prabhava="Arshoghna — Surana is the classical haemorrhoid remedy, the action it "
               "is named for and one no part of its rasa predicts.",
      dosha=(-1, 1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("arsha", "obesity"),
      apathya_for=("acidity", "psoriasis"),
      nutrition=N(118, 1.5, 27.9, 0.2, 4.1, source="usda"),
      **{**_V, "varga": "Shaka — Surana"}),

    F("Arbi (Colocasia)", id="colocasia_arbi",
      rasa=("madhura", "kashaya"), guna=("guru", "picchila"), virya="shita",
      vipaka="madhura",
      dosha=(2, -1, 2), ritu=("varsha", "sharad"),
      apathya_for=("amavata", "ibs", "diabetes", "obesity"),
      nutrition=N(112, 1.5, 26.5, 0.2, 4.1, source="usda"), **_V),

    F("Kamala Kanda (Lotus Stem)", id="lotus_stem",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita",
      vipaka="madhura",
      dosha=(1, -1, 0), ritu=("hemanta", "shishira"),
      pathya_for=("anemia", "acidity"),
      apathya_for=("ibs",),
      nutrition=N(74, 2.6, 17.2, 0.1, 4.9, source="usda"),
      **{**_V, "varga": "Shaka — Kamala"}),

    # ── Gourds ────────────────────────────────────────────────────────────────
    F("Alabu (Bottle Gourd)", id="bottle_gourd",
      rasa=("madhura",), guna=("laghu", "snigdha", "drava"), virya="shita",
      vipaka="madhura",
      prabhava="Laghu and Mutrala where a madhura, snigdha dravya would be neither — "
               "which is why Alabu is the gourd given in fever, in convalescence and "
               "to a weak Agni.",
      dosha=(0, -2, -1), ritu=("grishma", "varsha", "sharad"),
      pathya_for=("acidity", "obesity", "kidney_disease", "hypertension", "fatty_liver"),
      nutrition=N(14, 0.6, 3.4, 0.0, 0.5, source="usda"), **_V),

    F("Koshataki (Ridge Gourd)", id="ridge_gourd",
      rasa=("madhura", "tikta"), guna=("laghu", "ruksha"), virya="shita", vipaka="katu",
      dosha=(1, -1, -1), ritu=("grishma", "varsha"),
      pathya_for=("obesity", "diabetes", "fatty_liver"),
      nutrition=N(20, 1.2, 4.4, 0.2, 1.1, source="usda"), **_V),

    F("Karavellaka (Bitter Gourd)", id="bitter_gourd_karela",
      rasa=("tikta",), guna=("laghu", "ruksha"), virya="ushna", vipaka="katu",
      prabhava="The Prameha vegetable — Karavellaka's sugar-reducing action is the one "
               "the texts single it out for, and it is ushna against a tikta rasa that "
               "would cool.",
      dosha=(1, -1, -2), ritu=("grishma", "varsha", "sharad"),
      pathya_for=("diabetes", "obesity", "psoriasis", "fatty_liver", "high_cholesterol"),
      apathya_for=("constipation",),
      nutrition=N(17, 1.0, 3.7, 0.2, 2.8, source="usda"), **_V),

    F("Tindora (Ivy Gourd)", id="ivy_gourd_tindora",
      rasa=("tikta", "kashaya"), guna=("laghu", "ruksha"), virya="shita", vipaka="katu",
      dosha=(1, -1, -1), ritu=("grishma", "varsha"),
      pathya_for=("diabetes", "obesity"),
      nutrition=N(18, 1.2, 3.1, 0.1, 1.6, source="usda"),
      **{**_V, "varga": "Shaka — Bimbi"}),

    F("Kushmanda (Pumpkin)", id="pumpkin",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      prabhava="Medhya and Hridya — Kushmanda is the Rasayana gourd, given in mental "
               "and cardiac depletion, which is not an action any of its qualities "
               "predict.",
      dosha=(-1, -2, 1), ritu=("sharad", "hemanta"),
      pathya_for=("acidity", "anemia", "migraine", "kidney_disease"),
      apathya_for=("diabetes", "obesity"),
      nutrition=N(26, 1.0, 6.5, 0.1, 0.5, source="usda"), **_V),

    F("Trapusha (Cucumber)", id="cucumber",
      rasa=("madhura",), guna=("guru", "snigdha", "drava"), virya="shita",
      vipaka="madhura",
      dosha=(1, -2, 1), ritu=("grishma", "sharad"),
      pathya_for=("acidity", "kidney_disease", "hypertension"),
      apathya_for=("ibs", "grahani", "amavata"),
      nutrition=N(15, 0.7, 3.6, 0.1, 0.5, source="usda"), **_RAW),

    F("Zucchini", id="zucchini",
      rasa=("madhura",), guna=("laghu", "drava"), virya="shita", vipaka="madhura",
      dosha=(0, -1, 0), ritu=("grishma", "sharad"),
      pathya_for=("obesity", "acidity", "kidney_disease"),
      nutrition=N(17, 1.2, 3.1, 0.3, 1.0, source="usda"),
      **{**_V, "ref": "modern_extrapolated",
         "varga": "No nighantu entry. Reasoned from Koshataki and Alabu as a laghu, "
                  "drava summer gourd. Extrapolated, not cited."}),

    # ── Alliums and pungents ──────────────────────────────────────────────────
    F("Palandu (Onion)", id="onion",
      rasa=("katu", "madhura"), guna=("guru", "snigdha", "tikshna"), virya="ushna",
      vipaka="katu",
      dosha=(-1, 2, -1), ritu=("hemanta", "shishira", "vasanta"),
      pathya_for=("high_cholesterol", "hypertension"),
      apathya_for=("acidity", "migraine", "psoriasis", "ibs"),
      nutrition=N(40, 1.1, 9.3, 0.1, 1.7, source="usda"), **_V),

    F("Lasuna (Garlic)", id="garlic",
      rasa=("katu",), guna=("guru", "snigdha", "tikshna"), virya="ushna", vipaka="katu",
      prabhava="Rasayana for Vata and the classical Amavata medicine — Lasuna carries "
               "five of the six rasas and is prescribed where its katu rasa alone would "
               "bar it.",
      dosha=(-2, 2, -2), ritu=("hemanta", "shishira", "varsha"),
      pathya_for=("amavata", "high_cholesterol", "hypothyroid", "asthma", "obesity"),
      apathya_for=("acidity", "psoriasis", "migraine", "pregnancy"),
      nutrition=N(149, 6.4, 33.1, 0.5, 2.1, source="usda"), **_V),

    F("Ardraka (Fresh Ginger)", id="ginger",
      rasa=("katu",), guna=("guru", "snigdha", "tikshna"), virya="ushna", vipaka="katu",
      prabhava="Ardraka is guru and snigdha with katu vipaka where dried Shunthi is "
               "laghu with madhura vipaka. Fresh and dry are two dravyas and the texts "
               "prescribe them differently — this row and `ginger_dry_saunth` are that "
               "distinction.",
      dosha=(-2, 1, -2), ritu=("hemanta", "shishira", "varsha"),
      pathya_for=("ibs", "grahani", "amavata", "asthma", "constipation"),
      apathya_for=("acidity", "arsha", "psoriasis"),
      nutrition=N(80, 1.8, 17.8, 0.8, 2.0, source="usda"),
      **{**_V, "prep_state": "fresh", "varga": "Haritakyadi — Ardraka"}),

    F("Katuvira (Capsicum)", id="capsicum_bell_pepper",
      rasa=("katu", "madhura"), guna=("laghu", "ruksha"), virya="ushna", vipaka="katu",
      dosha=(-1, 1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("obesity",),
      apathya_for=("acidity", "psoriasis"),
      nutrition=N(31, 1.0, 6.0, 0.3, 2.1, source="usda"),
      **{**_V, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — Capsicum is a New World genus. Reasoned as a "
                  "mild katu, laghu, ushna Shaka, far below Maricha in tikshna. "
                  "Extrapolated, not cited."}),

    # ── Fruiting vegetables ───────────────────────────────────────────────────
    F("Raktaphala (Tomato)", id="tomato",
      rasa=("amla", "madhura"), guna=("laghu", "snigdha"), virya="ushna", vipaka="amla",
      dosha=(-1, 2, -1), ritu=("hemanta", "shishira"),
      apathya_for=("acidity", "amavata", "psoriasis", "arsha", "kidney_disease"),
      viruddha_with=("milk_full_fat",),
      nutrition=N(18, 0.9, 3.9, 0.2, 1.2, source="usda"),
      **{**_RAW, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — the tomato is a New World fruit. Reasoned as "
                  "amla-madhura with amla vipaka and ushna virya; the Amlapitta and "
                  "Amavata cautions follow from the amla rasa the derived row already "
                  "named while giving it katu vipaka. Extrapolated, not cited."}),

    F("Shigru (Drumstick / Moringa)", id="drumstick_moringa",
      rasa=("katu", "tikta"), guna=("laghu", "ruksha", "tikshna"), virya="ushna",
      vipaka="katu",
      prabhava="Shothahara and Krimighna — Shigru is the anti-inflammatory Shaka, "
               "given in Amavata and in Shotha where a katu-tikta vegetable would "
               "otherwise be avoided for Vata.",
      dosha=(-1, 1, -2), ritu=("vasanta", "grishma"),
      pathya_for=("amavata", "obesity", "diabetes", "anemia", "hypothyroid"),
      apathya_for=("acidity", "pregnancy"),
      nutrition=N(37, 2.1, 8.5, 0.2, 3.2, source="usda"), **_V),

    F("Kadali Kanda (Raw Banana)", id="raw_banana",
      rasa=("kashaya", "madhura"), guna=("guru", "ruksha"), virya="shita", vipaka="katu",
      dosha=(2, -1, -1), ritu=("grishma", "varsha"),
      pathya_for=("grahani", "diabetes", "obesity"),
      apathya_for=("constipation", "ibs"),
      nutrition=N(89, 1.1, 22.8, 0.3, 2.6, source="usda"),
      **{**_V, "prep_state": "unripe", "varga": "Shaka — Kadali, unripe"}),

    F("Panasa (Jackfruit)", id="jackfruit",
      rasa=("madhura", "kashaya"), guna=("guru", "picchila"), virya="shita",
      vipaka="madhura",
      dosha=(-1, -1, 2), ritu=("grishma", "varsha"),
      apathya_for=("diabetes", "obesity", "ibs", "grahani", "hypothyroid"),
      nutrition=N(95, 1.7, 23.2, 0.6, 1.5, source="usda"), **_V),

    F("Amra (Raw Mango)", id="raw_mango",
      rasa=("amla", "kashaya"), guna=("laghu", "ruksha"), virya="ushna", vipaka="amla",
      dosha=(1, 2, -1), ritu=("grishma",),
      pathya_for=("obesity",),
      apathya_for=("acidity", "psoriasis", "amavata", "arsha"),
      nutrition=N(60, 0.8, 15.0, 0.4, 1.6, source="usda"),
      **{**_V, "prep_state": "unripe", "varga": "Amradi Phala — Amra, unripe"}),

    F("Eranda-karkati (Raw Papaya)", id="raw_papaya",
      rasa=("kashaya", "tikta"), guna=("laghu", "tikshna", "ruksha"), virya="ushna",
      vipaka="katu",
      prabhava="Bhedana and a uterine stimulant — unripe papaya carries the action far "
               "more strongly than the ripe fruit, which is the whole basis of the "
               "pregnancy bar.",
      dosha=(1, 1, -2), ritu=("varsha", "sharad"),
      pathya_for=("constipation", "obesity", "grahani"),
      apathya_for=("pregnancy", "acidity"),
      nutrition=N(43, 0.5, 10.8, 0.3, 1.7, source="usda"),
      **{**_V, "prep_state": "unripe"}),

    # ── Pods, shoots, fungi ───────────────────────────────────────────────────
    F("French Beans", id="french_beans",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="shita", vipaka="katu",
      dosha=(1, -1, -1), ritu=("hemanta", "shishira"),
      pathya_for=("diabetes", "obesity"),
      apathya_for=("ibs", "grahani"),
      nutrition=N(31, 1.8, 7.1, 0.2, 3.4, source="usda"),
      **{**_V, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — a New World bean. Reasoned from the Shimbi "
                  "Shaka as laghu, ruksha and Vata-vardhaka. Extrapolated, not cited."}),

    F("Gavar (Cluster Beans)", id="cluster_beans_gavar",
      rasa=("kashaya", "madhura", "tikta"), guna=("guru", "ruksha"), virya="shita",
      vipaka="katu",
      dosha=(2, -1, -1), ritu=("varsha", "sharad"),
      pathya_for=("diabetes", "obesity", "high_cholesterol"),
      apathya_for=("ibs", "grahani", "amavata", "constipation"),
      nutrition=N(16, 3.2, 10.8, 0.4, 3.2, source="ifct2017"), **_V),

    F("Asparagus", id="asparagus",
      rasa=("madhura", "tikta"), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -2, 0), ritu=("vasanta", "grishma"),
      pathya_for=("kidney_disease", "acidity", "pcos"),
      nutrition=N(20, 2.2, 3.9, 0.1, 2.1, source="usda"),
      **{**_V, "ref": "modern_extrapolated",
         "varga": "The garden asparagus is not Shatavari, though the genus is shared; "
                  "the nighantu entry describes the root and this row is the shoot. "
                  "Reasoned as a madhura-tikta, shita Shaka with a mutrala action. "
                  "Extrapolated, not cited."}),

    F("Mushroom", id="mushroom",
      rasa=("madhura", "kashaya"), guna=("guru", "picchila"), virya="shita",
      vipaka="katu",
      dosha=(1, -1, 1), ritu=("varsha", "sharad"),
      apathya_for=("amavata", "psoriasis", "ibs"),
      nutrition=N(22, 3.1, 3.3, 0.3, 1.0, source="usda"),
      **{**_V, "varga": "Shaka — Chatraka. The texts class Chatraka among the foods to "
                        "be avoided, being guru, picchila and Ama-forming; the row "
                        "carries that caution rather than the modern reading."}),

    F("Makka (Sweet Corn)", id="corn_sweet",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="ushna", vipaka="katu",
      dosha=(1, 1, -1), ritu=("varsha", "sharad"),
      apathya_for=("ibs", "grahani", "acidity"),
      nutrition=N(96, 3.4, 21.0, 1.5, 2.4, source="usda"),
      **{**_V, "varga": "Kudhanya"}),
]
