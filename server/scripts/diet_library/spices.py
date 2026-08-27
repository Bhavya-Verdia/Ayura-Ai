"""The ten spices, authored.

The first tranche, chosen because a spice is the clearest case of what the derived
library flattened. `seed_diet_foods.py` gives every row in the `spice` category the
same profile — `rasa: ["pungent"], virya: heating, vipaka: pungent, dosha: (-1, +1, -1)`
— with three name overrides on top. Two of these ten contradict that profile in the
classical texts, and neither could be expressed before:

  * **Shunthi (dry ginger)** has *madhura* vipaka despite katu rasa. It is the
    textbook prabhava exception, and the old schema had no vipaka value it could not
    reach only because it happened to guess katu for everything pungent.
  * **Ela (cardamom)** is *shita* virya — cooling — despite carrying katu rasa. The
    category default made it heating, which is the opposite of why it is given.

Every macro block is transcribed from USDA FoodData Central for the ground or whole
spice and is a build input to be spot-checked, not a clinical claim. The Ayurvedic
fields are AUTHORED, NOT CLINICALLY REVIEWED, like every other clinical claim in this
repository; `reviewed` is False on all of them and they belong in the Vaidya packet.

Ids match the keys already in `diet_foods.json` so the migration maps one-to-one.
"""

from diet_library.schema import ALL_RITU
from diet_library.spec import F, N

_SPICE = dict(category="spice", prep_state="prepared", meal=("breakfast", "lunch", "dinner"),
              prep_minutes=1, diet_types=("vegetarian", "vegan"), vegan=True,
              ref="bhavaprakasha")

SPICES = [
    F("Haridra (Turmeric)", id="turmeric", varga="Haritakyadi",
      rasa=("tikta", "katu"), guna=("ruksha", "laghu"), virya="ushna", vipaka="katu",
      dosha=(0, -1, -2), ritu=ALL_RITU,
      pathya_for=("psoriasis", "diabetes", "amavata", "high_cholesterol"),
      apathya_for=("pregnancy",),
      nutrition=N(312, 9.7, 67.1, 3.3, 22.7, source="usda"), **_SPICE),

    F("Jiraka (Cumin)", id="cumin_jeera", varga="Haritakyadi",
      rasa=("katu",), guna=("laghu", "ruksha"), virya="ushna", vipaka="katu",
      prabhava="Vata-anulomana. Katu rasa raises Vata by rule; Jiraka relieves it, by "
               "kindling Agni and clearing the Anaha through which Vata accumulates. "
               "Classically vata-kapha hara.",
      dosha=(-1, 1, -2), ritu=ALL_RITU,
      pathya_for=("ibs", "grahani", "constipation"),
      nutrition=N(375, 17.8, 44.2, 22.3, 10.5, source="usda"), **_SPICE),

    F("Dhanyaka (Coriander Seed)", id="coriander_dhania", varga="Haritakyadi",
      rasa=("kashaya", "tikta", "madhura"), guna=("laghu", "snigdha"),
      virya="ushna", vipaka="madhura",
      prabhava="Tridoshaghna, and Pitta-shamaka in effect despite ushna virya — the "
               "action the texts attribute to Dhanyaka specifically, which is why it "
               "is the one warm spice given freely in Pitta conditions.",
      dosha=(-1, -1, -1), ritu=ALL_RITU,
      pathya_for=("acidity", "migraine", "kidney_disease"),
      nutrition=N(298, 12.4, 55.0, 17.8, 41.9, source="usda"), **_SPICE),

    F("Mishreya (Fennel)", id="fennel_saunf", varga="Haritakyadi",
      rasa=("madhura", "tikta", "katu"), guna=("laghu", "snigdha"),
      virya="ushna", vipaka="madhura",
      dosha=(-1, -1, 0), ritu=ALL_RITU,
      pathya_for=("acidity", "ibs", "grahani"),
      nutrition=N(345, 15.8, 52.3, 14.9, 39.8, source="usda"), **_SPICE),

    F("Ela (Green Cardamom)", id="cardamom_elaichi", varga="Karpuradi",
      rasa=("katu", "madhura"), guna=("laghu", "ruksha"), virya="shita", vipaka="madhura",
      prabhava="Shita virya despite katu rasa — the classical exception that makes Ela "
               "the aromatic given in Pitta conditions where Maricha and Twak are barred.",
      dosha=(-1, -1, -1), ritu=ALL_RITU,
      pathya_for=("acidity", "asthma"),
      nutrition=N(311, 10.8, 68.5, 6.7, 28.0, source="usda"), **_SPICE),

    F("Twak (Cinnamon)", id="cinnamon_dalchini", varga="Karpuradi",
      rasa=("katu", "tikta", "madhura"), guna=("laghu", "ruksha", "tikshna"),
      virya="ushna", vipaka="katu",
      dosha=(-1, 1, -2), ritu=("shishira", "hemanta", "vasanta", "varsha"),
      pathya_for=("diabetes", "obesity", "hypothyroid"),
      nutrition=N(247, 4.0, 80.6, 1.2, 53.1, source="usda"), **_SPICE),

    F("Maricha (Black Pepper)", id="black_pepper", varga="Haritakyadi",
      rasa=("katu",), guna=("laghu", "tikshna", "ruksha"), virya="ushna", vipaka="katu",
      prabhava="Vata-kapha hara at culinary dose, where the deepana action dominates the "
               "Vata-raising tendency of katu rasa. In quantity the rasa wins — which is "
               "why Maricha is classically a pinch and not a spoon.",
      dosha=(-1, 2, -2), ritu=("shishira", "hemanta", "vasanta", "varsha"),
      pathya_for=("obesity", "hypothyroid", "asthma"),
      apathya_for=("acidity", "arsha"),
      nutrition=N(251, 10.4, 63.9, 3.3, 25.3, source="usda"), **_SPICE),

    F("Shunthi (Dry Ginger)", id="ginger_dry_saunth", varga="Haritakyadi",
      rasa=("katu",), guna=("laghu", "snigdha"), virya="ushna", vipaka="madhura",
      prabhava="Madhura vipaka despite katu rasa — the classical exception for Shunthi, "
               "and the reason dry ginger nourishes where fresh Ardraka only stimulates. "
               "The same action makes it vata-hara where katu rasa alone would raise Vata.",
      dosha=(-2, 1, -2), ritu=ALL_RITU,
      pathya_for=("ibs", "grahani", "obesity", "amavata", "asthma"),
      apathya_for=("acidity", "arsha"),
      nutrition=N(335, 8.98, 71.6, 4.24, 14.1, source="usda"), **_SPICE),

    F("Methika (Fenugreek Seed)", id="fenugreek_seeds_methi", varga="Haritakyadi",
      rasa=("tikta", "katu"), guna=("laghu", "snigdha"), virya="ushna", vipaka="katu",
      prabhava="Vata-kapha hara — the snigdha guna offsets the ruksha tendency its "
               "tikta-katu rasa would otherwise carry into Vata.",
      dosha=(-1, 1, -2), ritu=("shishira", "hemanta", "vasanta"),
      pathya_for=("diabetes", "pcos", "high_cholesterol", "amavata"),
      apathya_for=("pregnancy",),
      nutrition=N(323, 23.0, 58.4, 6.4, 24.6, source="usda"), **_SPICE),

    F("Yavani (Ajwain)", id="ajwain", varga="Haritakyadi",
      rasa=("katu", "tikta"), guna=("laghu", "ruksha", "tikshna"),
      virya="ushna", vipaka="katu",
      prabhava="Vata-anulomana and shula-prashamana — the classical carminative. It "
               "clears the Anaha through which its own katu-tikta rasa would aggravate Vata.",
      dosha=(-2, 1, -2), ritu=ALL_RITU,
      pathya_for=("ibs", "grahani", "constipation", "asthma"),
      apathya_for=("acidity",),
      nutrition=N(305, 15.9, 43.2, 21.1, 21.2, source="ifct2017"), **_SPICE),
]
