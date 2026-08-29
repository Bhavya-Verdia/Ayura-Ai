"""The twenty grains.

The generator's `grain` default is `rasa: ["sweet"], virya: cooling, vipaka: sweet,
dosha: (-1, -1, +1)`, with four name overrides. Under it, Yava and Shali are the same
row — and Yava is the classical Medohara grain, prescribed in Sthaulya and Prameha
precisely because it reduces Kapha, while Shali is the Kapha-building one. Bajra is
ushna virya and Pitta-vardhaka; the default made it cooling.

## Macros are per 100 g AS EATEN

Cooked, for everything here that is cooked. This matters more than it sounds: the
engine's portion model treats a grain serving as 150 g, so a dry figure would put
545 kcal of raw rice on the plate instead of 195 kcal of cooked. The file this replaces
mixes the two — basmati rice is recorded cooked at 130 kcal and oats dry at 389, in the
same category, with nothing saying which is which.

`poha` and `rice_flakes` were two ids for one ingredient. They are kept as two rows
because `prep_state` can now tell them apart: the dry flake and the cooked dish are not
the same food, and the difference is 346 kcal against 130.

AUTHORED, NOT CLINICALLY REVIEWED. Macros from USDA FoodData Central unless marked.
"""

from diet_library.spec import F, N

_G = dict(category="grain", meal=("breakfast", "lunch", "dinner"), prep_minutes=20,
          diet_types=("vegetarian", "vegan"), vegan=True, ref="bhavaprakasha",
          varga="Dhanya")

GRAINS = [
    F("Shali (Basmati Rice)", id="basmati_rice", prep_state="cooked",
      rasa=("madhura",), guna=("laghu", "snigdha", "mridu"), virya="shita",
      vipaka="madhura",
      prabhava="Purana Shali — aged rice — is laghu where new rice is guru, which is "
               "why the texts specify the age.",
      dosha=(-1, -1, 1), ritu=("grishma", "sharad", "varsha"),
      pathya_for=("acidity", "grahani", "ibs"),
      apathya_for=("diabetes", "obesity", "hypothyroid"),
      nutrition=N(130, 2.7, 28.0, 0.3, 0.4, source="usda"), **_G),

    F("White Rice", id="white_rice", prep_state="cooked",
      rasa=("madhura",), guna=("laghu", "picchila"), virya="shita", vipaka="madhura",
      dosha=(-1, -1, 2), ritu=("grishma", "sharad"),
      pathya_for=("acidity", "grahani"),
      apathya_for=("diabetes", "obesity", "hypothyroid", "fatty_liver"),
      nutrition=N(130, 2.7, 28.0, 0.3, 0.4, source="usda"), **_G),

    F("Brown Rice", id="brown_rice", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="shita",
      vipaka="madhura",
      dosha=(1, -1, 0), ritu=("sharad", "hemanta"),
      pathya_for=("diabetes", "high_cholesterol", "constipation"),
      apathya_for=("grahani", "ibs"),
      nutrition=N(111, 2.6, 23.0, 0.9, 1.8, source="usda"),
      **{**_G, "varga": "Dhanya — Shali, unpolished"}),

    F("Godhuma (Whole Wheat Roti)", id="roti_whole_wheat", prep_state="cooked",
      rasa=("madhura",), guna=("guru", "snigdha", "sthira"), virya="shita",
      vipaka="madhura",
      prabhava="Brimhana and Jivana — wheat builds tissue, which is the action that "
               "makes it Vata's staple and Kapha's burden at the same time.",
      dosha=(-2, -1, 2), ritu=("shishira", "hemanta", "vasanta"),
      pathya_for=("anemia", "constipation"),
      apathya_for=("obesity", "hypothyroid", "ibs", "fatty_liver"),
      allergen=True,
      nutrition=N(297, 11.0, 51.0, 5.4, 8.0, source="usda"), **_G),

    F("Paratha", id="paratha", prep_state="cooked",
      rasa=("madhura",), guna=("guru", "snigdha", "sthira"), virya="ushna",
      vipaka="madhura",
      prabhava="Pitta-vardhaka against a madhura rasa that pacifies Pitta by rule. "
               "The preparation decides: sneha taken to griddle heat turns the virya "
               "ushna, which is Vidahi — the same reason fried food is the first "
               "Apathya named in Amlapitta.",
      dosha=(-2, 1, 2), ritu=("shishira", "hemanta"),
      apathya_for=("obesity", "high_cholesterol", "fatty_liver", "acidity", "arsha"),
      allergen=True,
      nutrition=N(320, 7.0, 45.0, 12.0, 5.0, source="authored_estimate"),
      **{**_G, "ref": "modern_extrapolated",
         "varga": "A preparation, not a dravya. Reasoned from Godhuma cooked in sneha: "
                  "the wheat's guru-snigdha guna intensified and the virya turned ushna "
                  "by the ghee and the griddle. Extrapolated, not cited."}),

    F("Prithuka (Poha, Cooked)", id="poha", prep_state="cooked",
      rasa=("madhura",), guna=("laghu", "picchila"), virya="shita", vipaka="madhura",
      dosha=(-1, -1, 1), ritu=("vasanta", "grishma", "sharad"),
      pathya_for=("grahani", "acidity"),
      apathya_for=("diabetes", "obesity"),
      nutrition=N(130, 2.5, 27.0, 1.5, 1.0, source="authored_estimate"), **_G),

    F("Prithuka (Rice Flakes, Dry)", id="rice_flakes", prep_state="dry",
      rasa=("madhura",), guna=("guru", "picchila"), virya="shita", vipaka="madhura",
      prabhava="Prithuka is guru and Kapha-vardhaka in Bhavaprakasha despite coming "
               "from laghu Shali — the flattening and drying change the dravya, so the "
               "dry flake and the cooked dish do not share a guna.",
      dosha=(-1, -1, 2), ritu=("vasanta", "grishma"),
      apathya_for=("diabetes", "obesity", "hypothyroid"),
      nutrition=N(346, 6.6, 77.0, 1.2, 2.4, source="usda"), **_G),

    F("Upma", id="upma", prep_state="cooked",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="ushna", vipaka="madhura",
      dosha=(-1, 0, 1), ritu=("shishira", "hemanta", "varsha"),
      apathya_for=("diabetes", "obesity"), allergen=True,
      nutrition=N(145, 3.5, 24.0, 4.0, 1.5, source="authored_estimate"),
      **{**_G, "ref": "modern_extrapolated",
         "varga": "A preparation, not a dravya. Reasoned from Godhuma sooji with a "
                  "ushna tadka — the semolina's guru guna, warmed and lightened by "
                  "the spices. Extrapolated, not cited."}),

    F("Oats Porridge", id="oats", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "picchila", "snigdha"),
      virya="shita", vipaka="madhura",
      dosha=(-1, -1, 1), ritu=("shishira", "hemanta"),
      pathya_for=("high_cholesterol", "constipation", "acidity"),
      apathya_for=("hypothyroid", "ibs"), allergen=True,
      nutrition=N(71, 2.5, 12.0, 1.5, 1.7, source="usda"),
      **{**_G, "ref": "modern_extrapolated",
         "varga": "No classical entry. Reasoned from Yava Varga — but unlike Yava it is "
                  "picchila and not Medohara, because the sliminess that makes oats "
                  "cholesterol-lowering is the opposite of Yava's ruksha, sara quality. "
                  "Extrapolated, not cited."}),

    F("Quinoa", id="quinoa", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="madhura",
      dosha=(0, -1, -1), ritu=("grishma", "sharad", "vasanta"),
      pathya_for=("diabetes", "obesity", "high_cholesterol", "pcos"),
      nutrition=N(120, 4.4, 21.3, 1.9, 2.8, source="usda"),
      **{**_G, "ref": "modern_extrapolated",
         "varga": "No classical entry. Reasoned from the Kudhanya (minor millet) group "
                  "as a laghu, ruksha, madhura-kashaya grain — nearest to Shyamaka in "
                  "guna. Extrapolated, not cited."}),

    F("Bajra (Pearl Millet)", id="millet_bajra", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="ushna",
      vipaka="katu",
      prabhava="Ushna virya and Pitta-vardhaka against a madhura-kashaya rasa that "
               "would pacify Pitta by rule — the classical caution on Bajra, and why "
               "it is a winter grain and not a summer one.",
      dosha=(1, 1, -2), ritu=("shishira", "hemanta"),
      pathya_for=("obesity", "diabetes", "hypothyroid"),
      apathya_for=("acidity", "psoriasis"),
      nutrition=N(119, 3.5, 23.7, 1.0, 1.3, source="usda"),
      **{**_G, "varga": "Kudhanya"}),

    F("Jowar (Sorghum)", id="millet_jowar", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="katu",
      dosha=(1, -1, -2), ritu=("grishma", "sharad"),
      pathya_for=("obesity", "diabetes", "high_cholesterol"),
      apathya_for=("constipation", "ibs"),
      nutrition=N(115, 3.5, 25.0, 0.6, 2.2, source="authored_estimate"),
      **{**_G, "varga": "Kudhanya"}),

    F("Daliya (Broken Wheat)", id="daliya", prep_state="cooked",
      rasa=("madhura",), guna=("laghu", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -1, 1), ritu=("shishira", "hemanta", "vasanta"),
      pathya_for=("constipation", "anemia", "grahani"),
      apathya_for=("obesity",), allergen=True,
      nutrition=N(83, 3.1, 18.6, 0.2, 4.5, source="usda"),
      **{**_G, "varga": "Dhanya — Godhuma, broken"}),

    F("Rava (Semolina)", id="semolina_rava", prep_state="cooked",
      rasa=("madhura",), guna=("guru", "picchila"), virya="shita", vipaka="madhura",
      dosha=(-1, -1, 2), ritu=("shishira", "hemanta"),
      apathya_for=("diabetes", "obesity", "hypothyroid"), allergen=True,
      nutrition=N(100, 3.4, 20.5, 0.3, 1.1, source="authored_estimate"),
      **{**_G, "varga": "Dhanya — Godhuma, milled"}),

    F("Whole Wheat Bread", id="bread_whole_wheat", prep_state="fermented",
      rasa=("madhura", "amla"), guna=("guru", "ruksha", "sthira"),
      virya="ushna", vipaka="amla",
      prabhava="Vata-vardhaka against a madhura-amla rasa that pacifies Vata by rule. "
               "Yeast fermentation makes the loaf ruksha and khara where the wheat was "
               "snigdha, and Vata follows the guna here rather than the rasa — the "
               "same reason dry, aerated food is withheld in Vata disorders.",
      dosha=(1, 1, 2), ritu=("shishira", "hemanta"),
      apathya_for=("amavata", "psoriasis", "acidity", "obesity", "ibs"),
      allergen=True,
      nutrition=N(247, 13.0, 41.0, 3.4, 7.0, source="usda"),
      **{**_G, "ref": "modern_extrapolated",
         "varga": "No classical entry. Reasoned from Godhuma taken through yeast "
                  "fermentation: amla rasa and amla vipaka arrive with the souring, "
                  "and with them the Amavata and Kushtha bars that attach to fermented "
                  "food. Extrapolated, not cited."}),

    F("Yava (Barley)", id="barley", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha", "chala"), virya="shita",
      vipaka="katu",
      # No note about the old generator here: `prabhava` is seeded verbatim into the
      # nutrition corpus and read back as background context when a plan is written,
      # so a sentence about this repo would reach the model mid-diagnosis. Why the
      # field exists belongs in the module docstring, which is where it is.
      prabhava="Medohara and Kapha-hara despite madhura rasa — the textbook Prabhava, "
               "and the reason Yava is the grain prescribed in Sthaulya and Prameha "
               "while Shali is withheld.",
      dosha=(1, -1, -2), ritu=("vasanta", "grishma", "sharad"),
      pathya_for=("obesity", "diabetes", "high_cholesterol", "hypothyroid", "pcos"),
      apathya_for=("constipation",), allergen=True,
      nutrition=N(123, 2.3, 28.2, 0.4, 3.8, source="usda"), **_G),

    F("Ramdana (Amaranth)", id="amaranth", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="shita",
      vipaka="madhura",
      dosha=(0, -1, -1), ritu=("grishma", "sharad"),
      pathya_for=("anemia", "diabetes", "constipation"),
      nutrition=N(102, 3.8, 19.0, 1.6, 2.1, source="usda"),
      **{**_G, "varga": "Kudhanya"}),

    F("Kuttu (Buckwheat)", id="buckwheat", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("laghu", "ruksha"), virya="ushna",
      vipaka="katu",
      prabhava="Ushna virya and Pitta-vardhaka against a rasa that would pacify Pitta "
               "— the reason Kuttu is a Vrata grain for cold months and sits badly in "
               "Grishma.",
      dosha=(1, 1, -1), ritu=("shishira", "hemanta"),
      pathya_for=("diabetes", "obesity"),
      apathya_for=("acidity", "psoriasis"),
      nutrition=N(92, 3.4, 19.9, 0.6, 2.7, source="usda"),
      **{**_G, "ref": "modern_extrapolated",
         "varga": "No nighantu entry; a Vrata food of later usage. Reasoned as a laghu, "
                  "ruksha, ushna Kudhanya — its Pitta caution is the one folk practice "
                  "and Unani sources agree on. Extrapolated, not cited."}),

    F("Makka (Sweet Corn)", id="corn", prep_state="cooked",
      rasa=("madhura", "kashaya"), guna=("guru", "ruksha"), virya="ushna",
      vipaka="katu",
      prabhava="Ushna despite madhura rasa, and guru while ruksha — the combination "
               "that makes Makka hard on Vata and on a weak Agni both.",
      dosha=(1, 1, -1), ritu=("varsha", "sharad"),
      apathya_for=("ibs", "grahani", "acidity"),
      nutrition=N(96, 3.4, 21.0, 1.5, 2.4, source="usda"),
      **{**_G, "varga": "Kudhanya"}),

    F("Sabudana (Tapioca Pearls)", id="sabudana", prep_state="cooked",
      rasa=("madhura",), guna=("guru", "picchila", "sthira"), virya="shita",
      vipaka="madhura",
      dosha=(-1, -1, 2), ritu=("grishma", "sharad"),
      apathya_for=("diabetes", "obesity", "hypothyroid", "fatty_liver"),
      nutrition=N(130, 0.2, 32.0, 0.0, 0.3, source="authored_estimate"),
      **{**_G, "ref": "modern_extrapolated",
         "varga": "No nighantu entry — tapioca is a New World root and reaches India "
                  "long after the texts. Reasoned as pure madhura starch: guru, "
                  "picchila, Kapha-vardhaka, and nutritionally near-empty besides "
                  "carbohydrate. Extrapolated, not cited."}),
]
