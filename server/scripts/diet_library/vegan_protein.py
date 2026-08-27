"""The ten plant-milk and plant-protein rows — and the category that has no texts.

Nine of these ten have no entry in any nighantu. They are twentieth-century foods, and
the generator gave them a rasa, a virya, a vipaka and a dosha effect from the
`vegan_protein` category default (`rasa: ["sweet"], virya: cooling, dosha: (0, -1, +1)`)
with exactly the confidence it gave Shunthi one. Nothing in the row recorded that the
first was cited and the second invented.

They are marked `modern_extrapolated` here, each carrying the dravya it is reasoned
from. That is not a hedge: it is the difference a reviewer needs, and it makes this
category the first thing a Vaidya should look at, because it is the part of the library
where a rule engine is furthest from a source.

Coconut milk is the exception — Narikela is in Bhavaprakasha.

AUTHORED, NOT CLINICALLY REVIEWED.
"""

from diet_library.spec import F, N

_VP = dict(category="vegan_protein", prep_state="prepared",
           meal=("breakfast", "snack"), prep_minutes=2,
           diet_types=("vegetarian", "vegan"), vegan=True)

VEGAN_PROTEIN = [
    F("Narikela Ksheera (Coconut Milk)", id="coconut_milk",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -2, 2), ritu=("grishma", "sharad"),
      pathya_for=("acidity", "psoriasis"),
      apathya_for=("obesity", "high_cholesterol", "hypothyroid"),
      nutrition=N(230, 2.3, 5.5, 24.0, 2.2, source="usda"),
      ref="bhavaprakasha", varga="Amradi Phala", **_VP),

    F("Almond Milk", id="almond_milk",
      rasa=("madhura",), guna=("laghu", "snigdha"), virya="shita", vipaka="madhura",
      dosha=(-1, -1, 1), ritu=("grishma", "sharad", "vasanta"),
      pathya_for=("acidity",), apathya_for=("hypothyroid",), allergen=True,
      nutrition=N(15, 0.6, 0.6, 1.2, 0.3, source="usda"),
      ref="modern_extrapolated",
      varga="No classical entry. Reasoned from Badama (Vatadi), diluted roughly ten "
            "to one — the madhura rasa and snigdha guna survive, the guru quality does "
            "not. Extrapolated, not cited.", **_VP),

    F("Soy Milk", id="soy_milk",
      rasa=("madhura", "kashaya"), guna=("guru", "picchila"), virya="shita",
      vipaka="madhura",
      dosha=(1, -1, 1), ritu=("grishma", "sharad"),
      apathya_for=("hypothyroid", "thyroid", "ibs", "pcos"), allergen=True,
      nutrition=N(33, 2.8, 1.8, 1.6, 0.4, source="usda"),
      ref="modern_extrapolated",
      varga="No classical entry; the soybean itself is absent from the nighantus. "
            "Reasoned from the Shimbi (legume) Varga as a madhura-kashaya, guru, "
            "abhishyandi preparation — Vata-vardhaka by its flatulence, as legumes are. "
            "Extrapolated, not cited.", **_VP),

    F("Oat Milk", id="oat_milk",
      rasa=("madhura",), guna=("guru", "snigdha", "picchila"), virya="shita",
      vipaka="madhura",
      dosha=(-1, -1, 2), ritu=("shishira", "hemanta", "vasanta"),
      apathya_for=("diabetes", "obesity"),
      nutrition=N(43, 0.8, 7.0, 1.3, 0.8, source="usda"),
      ref="modern_extrapolated",
      varga="No classical entry. Reasoned from Yava Varga — a madhura, picchila grain "
            "extract; unlike Yava itself it is not Kapha-hara, because the milling and "
            "straining leave the sweet starch and discard the ruksha bran. "
            "Extrapolated, not cited.", **_VP),

    F("Coconut Yogurt", id="coconut_yogurt",
      rasa=("madhura", "amla"), guna=("guru", "snigdha"), virya="ushna", vipaka="amla",
      dosha=(-1, 1, 1), ritu=("shishira", "hemanta"),
      apathya_for=("amavata", "psoriasis", "acidity", "obesity"),
      nutrition=N(97, 0.9, 7.4, 7.4, 0.9, source="authored_estimate"),
      ref="modern_extrapolated",
      varga="No classical entry. Reasoned as Narikela Ksheera taken through the "
            "fermentation Dadhi undergoes — amla rasa and amla vipaka arrive with the "
            "souring, and the Amavata bar arrives with them. Extrapolated, not cited.",
      **_VP),

    F("Tofu", id="vegan_paneer_tofu",
      rasa=("madhura", "kashaya"), guna=("guru", "picchila"), virya="shita",
      vipaka="madhura",
      dosha=(1, -1, 1), ritu=("grishma", "sharad"),
      apathya_for=("hypothyroid", "thyroid", "ibs", "pcos"), allergen=True,
      nutrition=N(76, 8.1, 1.9, 4.8, 0.3, source="usda"),
      ref="modern_extrapolated",
      varga="No classical entry. Reasoned from the Shimbi Varga curdled as Kilata is — "
            "guru and abhishyandi like paneer, but Vata-vardhaka where paneer is "
            "Vata-hara, because the legume's flatulence survives the curdling. "
            "Extrapolated, not cited.", **_VP),

    F("Nutritional Yeast", id="nutritional_yeast",
      rasa=("kashaya", "tikta"), guna=("laghu", "ruksha"), virya="ushna", vipaka="katu",
      # Pitta is left at 0 rather than raised. The validator refused +1 against a
      # kashaya-tikta rasa and it was right to: the Pitta claim would have rested on
      # the food being fermented, not on anything in its rasa or virya, and for a
      # dravya with no classical entry that is a guess wearing a number. The
      # fermentation concern is stated where it belongs, as an apathya.
      dosha=(1, 0, -2), ritu=("varsha", "sharad", "hemanta"),
      pathya_for=("anemia",), apathya_for=("migraine", "psoriasis", "amavata"),
      nutrition=N(385, 45.0, 36.0, 5.0, 21.0, source="usda"),
      ref="modern_extrapolated",
      varga="No classical entry. A dried fermented product with no dravya analogue; "
            "reasoned as kashaya-tikta, laghu and ruksha, Kapha-hara and "
            "Vata-vardhaka. The Amavata and psoriasis bars follow from its being "
            "fermented, which is Viruddha in Kushtha. Extrapolated, not cited.", **_VP),

    F("Coconut Cream", id="coconut_cream",
      rasa=("madhura",), guna=("guru", "snigdha", "picchila"), virya="shita",
      vipaka="madhura",
      dosha=(-2, -2, 2), ritu=("grishma", "sharad"),
      pathya_for=("acidity",),
      apathya_for=("obesity", "high_cholesterol", "hypothyroid", "fatty_liver"),
      nutrition=N(330, 3.6, 6.6, 34.7, 2.2, source="usda"),
      ref="bhavaprakasha", varga="Amradi Phala", **_VP),

    F("Cashew Cream", id="cashew_cream",
      rasa=("madhura",), guna=("guru", "snigdha"), virya="ushna", vipaka="madhura",
      prabhava="Pitta-vardhaka despite madhura rasa — Kaju is ushna virya, the one "
               "sweet nut the texts warn against in Pitta, and blending it into a cream "
               "concentrates rather than tempers that.",
      dosha=(-2, 1, 2), ritu=("shishira", "hemanta"),
      apathya_for=("acidity", "obesity", "high_cholesterol", "psoriasis"), allergen=True,
      nutrition=N(250, 8.0, 14.0, 20.0, 1.5, source="authored_estimate"),
      ref="modern_extrapolated",
      varga="No classical entry for the preparation. Reasoned from Kaju (Vatadi Varga) "
            "wet-ground — its ushna virya and Pitta action carry over undiluted. "
            "Extrapolated, not cited.", **_VP),

    F("Flax Milk", id="flax_milk",
      rasa=("madhura", "kashaya"), guna=("guru", "snigdha", "picchila"),
      virya="ushna", vipaka="katu",
      prabhava="Atasi is ushna virya and katu vipaka against a madhura-kashaya rasa, "
               "and Pitta-vardhaka with it — the classical caution on flax, which is "
               "why it is a Vata-Kapha seed and not a cooling one. Cited for the seed; "
               "carried to the milk by extrapolation.",
      dosha=(-1, 1, 0), ritu=("shishira", "hemanta"),
      pathya_for=("pcos", "constipation", "high_cholesterol"),
      apathya_for=("acidity", "psoriasis"),
      nutrition=N(25, 0.0, 1.5, 2.5, 0.0, source="usda"),
      ref="modern_extrapolated",
      varga="No classical entry. Reasoned from Atasi (Uma Varga), which is ushna virya "
            "and katu vipaka despite a madhura-kashaya rasa — the Pitta caution is "
            "Atasi's own and survives the dilution. Extrapolated, not cited.", **_VP),
]
