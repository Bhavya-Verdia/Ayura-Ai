"""The five beverages.

The generator's `beverage` default is `rasa: ["sweet", "astringent"], virya: cooling,
dosha: (-1, -1, -1)` — every beverage pacifies every dosha. Ginger tea then gets a
name override to katu rasa and ushna virya but keeps `vipaka: sweet` from the category,
which is one of the five rows in the current library whose vipaka contradicts its own
rasa.

Lemon water is another: `rasa: ["sour"]` with `vipaka: "sweet"`, where amla rasa yields
amla vipaka. Amla Vipaka does not exist anywhere in the file the generator writes, so
every sour food carries a vipaka that cannot be right.

AUTHORED, NOT CLINICALLY REVIEWED.
"""

from diet_library.schema import ALL_RITU
from diet_library.spec import F, N

_BEV = dict(category="beverage", prep_state="prepared",
            meal=("breakfast", "snack"), prep_minutes=5,
            diet_types=("vegetarian", "vegan"), vegan=True)

BEVERAGES = [
    F("Green Tea", id="green_tea",
      rasa=("kashaya", "tikta"), guna=("laghu", "ruksha"), virya="ushna", vipaka="katu",
      dosha=(1, 0, -2), ritu=("vasanta", "grishma", "sharad"),
      pathya_for=("obesity", "high_cholesterol", "fatty_liver"),
      apathya_for=("constipation", "acidity", "anemia"),
      nutrition=N(1, 0.2, 0.0, 0.0, 0.0, source="usda"),
      ref="modern_extrapolated",
      varga="No classical entry for the prepared infusion. Reasoned from Kashaya "
            "Kalpana — a kashaya-tikta decoction, laghu and ruksha, Kapha-hara and "
            "Vata-vardhaka on repetition. Extrapolated, not cited.", **_BEV),

    F("Tulsi Tea", id="tulsi_tea",
      rasa=("katu", "tikta"), guna=("laghu", "ruksha", "tikshna"),
      virya="ushna", vipaka="katu",
      prabhava="Hridya and Rasayana — Tulsi's specific action carries it past what its "
               "katu-tikta rasa alone would do, which is why it is given as a daily "
               "drink and Maricha is not.",
      dosha=(-1, 1, -2), ritu=("shishira", "hemanta", "varsha", "vasanta"),
      pathya_for=("asthma", "migraine", "hypothyroid"),
      apathya_for=("acidity",),
      nutrition=N(1, 0.1, 0.2, 0.0, 0.0, source="authored_estimate"),
      ref="bhavaprakasha", varga="Pushpa", **_BEV),

    F("Shunthi Kwatha (Ginger Tea)", id="ginger_tea",
      rasa=("katu",), guna=("laghu", "snigdha"), virya="ushna", vipaka="madhura",
      prabhava="Made from Shunthi, and carries its exception: madhura vipaka despite "
               "katu rasa, and vata-hara where the rasa alone would raise Vata.",
      dosha=(-2, 1, -2), ritu=("shishira", "hemanta", "varsha"),
      pathya_for=("ibs", "grahani", "asthma", "obesity"),
      apathya_for=("acidity", "arsha"),
      nutrition=N(3, 0.1, 0.8, 0.0, 0.0, source="authored_estimate"),
      ref="bhavaprakasha", varga="Haritakyadi", **_BEV),

    F("Narikela Jala (Tender Coconut Water)", id="coconut_water",
      rasa=("madhura",), guna=("laghu", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -2, 0), ritu=("grishma", "sharad"),
      pathya_for=("acidity", "kidney_disease", "migraine"),
      apathya_for=("obesity",),
      nutrition=N(19, 0.7, 3.7, 0.2, 1.1, source="usda"),
      ref="bhavaprakasha", varga="Amradi Phala", **_BEV),

    F("Nimbu Jala (Lemon Water)", id="lemon_water",
      rasa=("amla",), guna=("laghu", "ruksha"), virya="ushna", vipaka="amla",
      prabhava="Kapha-hara despite amla rasa, which raises Kapha by rule. Nimbu's "
               "laghu-ruksha guna and its deepana-lekhana action govern — the reason "
               "warm lemon water is the classical morning drink for Ama and not a "
               "Kapha-aggravating one.",
      dosha=(-1, 1, -1), ritu=ALL_RITU,
      pathya_for=("constipation", "obesity"),
      apathya_for=("acidity", "psoriasis", "amavata"),
      viruddha_with=("milk", "curd_yogurt"),
      nutrition=N(6, 0.1, 2.0, 0.0, 0.1, source="usda"),
      ref="bhavaprakasha", varga="Amradi Phala", **_BEV),
]
