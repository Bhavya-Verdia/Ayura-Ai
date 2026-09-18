"""
Diet Brief Builder
Builds the classical Ayurvedic patient brief passed to the LLM and provides
allergen-scanning utilities.  Extracted from diet_llm_generator.py so the
knowledge constants and brief logic are independently testable and importable.
"""

from services.ahara_safety import _canon_condition, _COND_CANON, _term_in_text
from services.diet_condition_foods import condition_food_rules

# ── Dosha-based meal timing ────────────────────────────────────────────────────
MEAL_TIMING: dict[str, dict] = {
    "vata": {
        "breakfast": "7:00–8:00 AM — warm, cooked; before Vata peaks at 10 AM",
        "lunch": "12:00–1:00 PM — largest meal at solar peak",
        "snack": "4:00–5:00 PM — small nourishing snack before Vata evening spike",
        "dinner": "6:30–7:30 PM — warm, light; at least 2 hrs before sleep",
        "wake_up_drink": "Warm water with a pinch of rock salt and cumin",
        "bedtime_drink": "Warm golden milk with turmeric and cardamom",
        "general_note": "Regularity is the single most important Vata prescription. Eat at the same time every day.",
    },
    "pitta": {
        "breakfast": "7:30–8:30 AM — moderate, cooling breakfast",
        "lunch": "12:00–1:00 PM — substantial; Pitta digestion peaks at midday",
        "snack": "3:00–4:00 PM — cooling fruit or coconut water",
        "dinner": "7:00–8:00 PM — light, early; prevents overnight heat buildup",
        "wake_up_drink": "Room-temperature water with soaked dates or raisins",
        "bedtime_drink": "Cool milk with cardamom and fennel",
        "general_note": "Never skip lunch — Pitta Agni is strongest and must be fed at midday.",
    },
    "kapha": {
        "breakfast": "8:00–9:00 AM — light or skip; only eat if truly hungry",
        "lunch": "12:30–1:30 PM — main meal; spiced, warm, light grains and legumes",
        "snack": "4:00–5:00 PM — skip if not hungry; ginger tea instead",
        "dinner": "6:00–7:00 PM — very light, early; avoid heavy foods after dark",
        "wake_up_drink": "Warm water with honey, ginger, and lemon — kindles Kapha Agni",
        "bedtime_drink": "Warm ginger-cinnamon tea — prevents Kapha overnight accumulation",
        "general_note": "Less is more for Kapha. Never eat out of boredom or habit.",
    },
}

# ── Dosha-specific spice guides ────────────────────────────────────────────────
DOSHA_SPICES: dict[str, list[dict]] = {
    "vata": [
        {"name": "Ginger", "sanskrit": "Shunthi",
         "use": "Fresh in morning tea and all cooked meals — kindles Agni, warms Vata"},
        {"name": "Cumin", "sanskrit": "Jeeraka",
         "use": "Toast and add to dal and rice — grounds Vata, aids digestion"},
        {"name": "Cardamom", "sanskrit": "Ela",
         "use": "In warm milk or chai — reduces bloating, calms nervous system"},
        {"name": "Ajwain", "sanskrit": "Ajamoda",
         "use": "In rotis and dals — powerful carminative for Vata bloating"},
        {"name": "Asafoetida", "sanskrit": "Hingu",
         "use": "Tiny pinch in tadka — prevents Vata gas; most important Vata spice"},
    ],
    "pitta": [
        {"name": "Coriander", "sanskrit": "Dhanyaka",
         "use": "Fresh or seeds — the best Pitta-pacifying spice; use liberally"},
        {"name": "Fennel", "sanskrit": "Shatapushpa",
         "use": "After meals — cooling, anti-inflammatory, aids digestion"},
        {"name": "Cardamom", "sanskrit": "Ela",
         "use": "In cool drinks and desserts — sweet, cooling"},
        {"name": "Turmeric", "sanskrit": "Haridra",
         "use": "In all cooking — anti-inflammatory; use moderately (mildly heating)"},
        {"name": "Saffron", "sanskrit": "Kumkuma",
         "use": "In warm milk — royal Pitta tonic, cooling and nourishing"},
    ],
    "kapha": [
        {"name": "Black Pepper", "sanskrit": "Maricha",
         "use": "In all meals — stimulates sluggish Kapha Agni, burns Ama"},
        {"name": "Dry Ginger", "sanskrit": "Shunthi",
         "use": "Powder in food and tea — Kapha's number-one spice"},
        {"name": "Turmeric", "sanskrit": "Haridra",
         "use": "Generous amounts — reduces Kapha mucus and inflammation"},
        {"name": "Cinnamon", "sanskrit": "Tvak",
         "use": "In morning tea and porridge — warms and stimulates Kapha metabolism"},
        {"name": "Fenugreek", "sanskrit": "Methi",
         "use": "Seeds in dal or sprouted — the best Kapha fat-burning seed"},
    ],
}

# ── General Ayurvedic diet tips per dosha ─────────────────────────────────────
AYUR_TIPS: dict[str, str] = {
    "vata": (
        "Favour warm, cooked, oily, and grounding foods. Use generous ghee. "
        "Eat at consistent times — regularity is the single most important Vata prescription. "
        "Avoid cold drinks, raw salads, and dry snacks."
    ),
    "pitta": (
        "Favour cooling, mildly spiced, lightly sweet foods. Include coconut, coriander, and fennel liberally. "
        "Never skip lunch — your Agni is strongest at midday. "
        "Avoid excess chilli, garlic, onion, vinegar, and fermented foods."
    ),
    "kapha": (
        "Favour light, warm, pungent, and spiced foods. Prefer honey over sugar. "
        "Skip or minimise breakfast if not genuinely hungry. "
        "Avoid heavy dairy, cold foods, sweets, and eating after 7 PM."
    ),
}

# ── Condition Pathya-Apathya hints ────────────────────────────────────────────
PATHYA_APATHYA_HINTS: dict[str, dict] = {
    # ── The twenty-one conditions the app recognised and said nothing about ──────
    # `engine/condition_vocab` accepts 38 canonical conditions. Twenty-one of them
    # had no entry here, no entry in `_CONDITION_APATHYA_TERMS`, and no claim in the
    # authored food library — so the brief told the model to "use your classical
    # Ayurvedic knowledge to determine Pathya-Apathya" and the deterministic floor
    # was whatever `classify_condition_apathya_llm` invented for them. Gout and
    # kidney stones were among them, which are the two conditions here where diet is
    # most of the treatment.
    #
    # AUTHORED, NOT CLINICALLY REVIEWED — they go into the Vaidya packet with the
    # library's 708 claims. Where a condition has no classical counterpart the entry
    # says so in `modern_extrapolated` rather than inventing a Samhita chapter for it.
    "gout": {
        "ayurvedic_name": "Vatarakta",
        "pathya": ["old rice (Puranashali)", "barley (Yava)", "moong dal (Mudga)",
                   "bitter gourd (Karela)", "pointed gourd (Patola)", "amla (Amalaki)",
                   "cow's ghee", "cow's milk", "plenty of warm water"],
        "apathya": ["red meat", "organ meat", "shellfish and prawns", "alcohol and beer",
                    "urad dal (Masha)", "curd (Dadhi)", "excess salt", "fermented and sour foods"],
        "classical_ref": "Charaka Chikitsa 29 (Vatashonita); Ashtanga Hridayam Nidana 16",
    },
    "kidney_stones": {
        "ayurvedic_name": "Mutrashmari",
        "pathya": ["horse gram (Kulattha) — the classical Ashmari dravya", "barley (Yava)",
                   "plenty of water throughout the day", "tender coconut water",
                   "banana stem (Kadali Kanda)", "pomegranate (Dadima)",
                   "Gokshura and Punarnava preparations", "cucumber (Trapusha)"],
        "apathya": ["spinach and other high-oxalate greens", "tomato seeds", "excess salt",
                    "red meat", "beetroot", "chocolate and cocoa", "strong black tea",
                    "excess nuts"],
        "classical_ref": "Sushruta Nidana 3 (Ashmari); Charaka Chikitsa 26 (Trimarmiya)",
    },
    "gallstones": {
        "ayurvedic_name": "Pittashmari / Yakrit Vikara",
        "pathya": ["barley (Yava)", "moong dal", "bitter greens", "turmeric (Haridra)",
                   "amla (Amalaki)", "warm water", "light early dinner",
                   "pointed gourd (Patola)"],
        "apathya": ["deep-fried foods", "butter and cream", "excess ghee", "red meat",
                    "egg yolk", "full-fat cheese and paneer", "heavy late-night meals"],
        "classical_ref": "Sushruta Nidana 3 (Ashmari); Charaka Chikitsa 26",
    },
    "heart_disease": {
        "ayurvedic_name": "Hridroga",
        "pathya": ["Arjuna bark preparations", "garlic (Lasuna)", "amla (Amalaki)",
                   "pomegranate (Dadima)", "barley (Yava)", "oats", "moong dal",
                   "flax seeds (Atasi)"],
        "apathya": ["excess salt", "deep-fried foods", "red meat", "butter, cream and cheese",
                    "alcohol", "very heavy meals", "sleeping immediately after eating"],
        "classical_ref": "Charaka Chikitsa 26 (Trimarmiya — Hridroga); Sushruta Uttara 43",
    },
    "hyperthyroidism": {
        "ayurvedic_name": "Atyagni / Bhasmaka with Galaganda",
        "pathya": ["cow's milk", "cow's ghee", "sweet ripe fruits", "fresh coconut",
                   "almonds (Badama)", "oats", "cabbage, cauliflower and broccoli",
                   "rice and other grounding grains"],
        "apathya": ["strong coffee and black tea", "chilli and excess pungent spices",
                    "alcohol", "seaweed and other concentrated iodine sources",
                    "skipping meals", "excess bitter and astringent foods"],
        "classical_ref": "Charaka Nidana 11 (Galaganda); Charaka Chikitsa 15 (Bhasmaka)",
    },
    "osteoarthritis": {
        "ayurvedic_name": "Sandhigata Vata",
        "pathya": ["cow's ghee", "sesame oil (Tila Taila)", "garlic (Lasuna)",
                   "ginger (Ardraka)", "turmeric (Haridra)", "warm cooked moong",
                   "old rice", "warm milk"],
        "apathya": ["cold and refrigerated foods", "dry and raw foods", "curd (Dadhi)",
                    "fermented foods", "rajma and chana in excess", "carbonated drinks"],
        "classical_ref": "Charaka Chikitsa 28 (Vatavyadhi); Ashtanga Hridayam Nidana 15",
    },
    "sciatica": {
        "ayurvedic_name": "Gridhrasi",
        "pathya": ["cow's ghee", "sesame oil", "castor oil (Eranda Taila) — the classical "
                   "Gridhrasi dravya", "garlic", "dry ginger (Shunthi)", "moong dal",
                   "old rice", "warm unctuous food"],
        "apathya": ["cold and refrigerated foods", "dry and raw foods", "curd",
                    "fermented foods", "heavy legumes", "carbonated drinks"],
        "classical_ref": "Charaka Chikitsa 28 (Vatavyadhi — Gridhrasi); Sushruta Nidana 1",
    },
    "cervical_spondylosis": {
        "ayurvedic_name": "Griva Sandhigata Vata / Manyastambha",
        "pathya": ["cow's ghee", "sesame oil", "warm milk", "garlic", "ginger",
                   "moong dal", "old rice", "warm cooked vegetables"],
        "apathya": ["cold and refrigerated foods", "curd at night", "dry and raw foods",
                    "fermented foods", "carbonated drinks"],
        "classical_ref": "Charaka Chikitsa 28 (Vatavyadhi); Ashtanga Hridayam Nidana 15",
    },
    "ankylosing_spondylitis": {
        "ayurvedic_name": "Asthi-Majjagata Vata with Ama",
        "pathya": ["warm freshly cooked food", "cow's ghee", "dry ginger (Shunthi)",
                   "turmeric (Haridra)", "garlic", "moong dal", "old rice",
                   "Guggulu preparations"],
        "apathya": ["curd (Dadhi)", "cold and refrigerated foods", "fermented foods",
                    "urad dal and rajma", "deep-fried foods", "incompatible combinations "
                    "(Viruddha Ahara)"],
        "classical_ref": "Charaka Chikitsa 28 (Vatavyadhi); Charaka Chikitsa 29 (Vatashonita)",
    },
    "fibromyalgia": {
        "ayurvedic_name": "Mamsagata Vata with Ama",
        "pathya": ["warm easily digestible food", "cow's ghee", "dry ginger", "turmeric",
                   "moong soup", "old rice", "warm water"],
        "apathya": ["cold and raw foods", "curd", "fermented foods",
                    "strong coffee and black tea", "irregular meal times"],
        "classical_ref": "Charaka Chikitsa 28 (Vatavyadhi); Charaka Chikitsa 15 (Ama)",
    },
    "anxiety": {
        "ayurvedic_name": "Chittodvega",
        "pathya": ["warm milk with nutmeg", "cow's ghee", "soaked almonds", "dates (Kharjura)",
                   "Brahmi and Ashwagandha preparations", "rice", "sesame seeds",
                   "regular meal times"],
        "apathya": ["coffee and strong black tea", "alcohol", "energy drinks",
                    "dry and raw cold foods", "skipping meals", "excess pungent food"],
        "classical_ref": "Charaka Sutra 11 (Manasa); Charaka Chikitsa 9 (Unmada)",
    },
    "depression": {
        "ayurvedic_name": "Vishada / Manasa Avasada",
        "pathya": ["warm light freshly cooked food", "cow's ghee", "saffron milk",
                   "dates", "Brahmi and Jatamansi preparations", "sesame seeds",
                   "warming spices"],
        "apathya": ["heavy cold Kapha-increasing foods", "excess sweets", "alcohol",
                    "stale and reheated food", "sleeping during the day"],
        "classical_ref": "Charaka Chikitsa 9 (Unmada); Charaka Sutra 11",
    },
    "epilepsy": {
        "ayurvedic_name": "Apasmara",
        "pathya": ["Brahmi ghrita and other medicated ghee", "cow's milk", "old rice",
                   "moong dal", "light sattvic food", "regular meals"],
        "apathya": ["alcohol", "heavy meat", "stale and fermented food",
                    "incompatible combinations (Viruddha Ahara)", "excess pungent food",
                    "fasting to exhaustion"],
        "classical_ref": "Charaka Chikitsa 10 (Apasmara); Ashtanga Hridayam Uttara 7",
    },
    "eczema": {
        "ayurvedic_name": "Vicharchika (Kshudra Kushtha)",
        "pathya": ["bitter vegetables", "neem (Nimba)", "turmeric (Haridra)", "moong dal",
                   "old rice", "cow's ghee", "pointed gourd (Patola)"],
        "apathya": ["milk with fish — the classical Viruddha pair", "curd", "sour foods",
                    "excess salt", "seafood", "brinjal", "sour fruits"],
        "classical_ref": "Charaka Chikitsa 7 (Kushtha); Sushruta Nidana 5",
    },
    "sinusitis": {
        "ayurvedic_name": "Dushta Pratishyaya / Peenasa",
        "pathya": ["warm water through the day", "dry ginger (Shunthi)", "tulsi",
                   "black pepper (Maricha)", "turmeric", "honey", "light warm khichdi"],
        "apathya": ["curd (Dadhi)", "banana", "cold drinks", "ice cream", "heavy dairy",
                    "refrigerated food", "sleeping during the day"],
        "classical_ref": "Ashtanga Hridayam Uttara 24 (Nasaroga); Charaka Chikitsa 26",
    },
    "common_cold": {
        "ayurvedic_name": "Pratishyaya",
        "pathya": ["warm water", "ginger and tulsi decoction", "black pepper", "honey",
                   "turmeric milk", "light khichdi", "warm soups"],
        "apathya": ["curd", "banana", "cold drinks", "ice cream", "deep-fried foods",
                    "heavy dairy", "sleeping during the day"],
        "classical_ref": "Ashtanga Hridayam Uttara 24 (Nasaroga); Charaka Chikitsa 26",
    },
    "recurrent_uti": {
        "ayurvedic_name": "Mutrakrichra",
        "pathya": ["plenty of water", "tender coconut water", "barley water (Yava)",
                   "Gokshura and Punarnava preparations", "cucumber (Trapusha)",
                   "coriander seed water", "amla (Amalaki)"],
        "apathya": ["chilli and excess pungent spices", "alcohol", "coffee",
                    "pickles and fermented food", "sour foods", "holding the urge to urinate"],
        "classical_ref": "Charaka Chikitsa 26 (Mutrakrichra); Sushruta Uttara 59",
    },
    "glaucoma": {
        "ayurvedic_name": "Adhimantha",
        "pathya": ["Triphala preparations", "amla (Amalaki)", "cow's ghee",
                   "green leafy vegetables", "carrot (Garjara)", "cooling sweet foods"],
        "apathya": ["excess salt", "coffee and strong black tea", "alcohol",
                    "large volumes of fluid at one time", "very hot and pungent food",
                    "suppression of natural urges"],
        "classical_ref": "Sushruta Uttara 6 (Netraroga); Ashtanga Hridayam Uttara 15",
    },
    "vertigo": {
        "ayurvedic_name": "Bhrama",
        "pathya": ["cow's milk", "cow's ghee", "amla", "coriander (Dhanyaka)",
                   "grapes (Draksha)", "adequate water", "small frequent meals"],
        "apathya": ["excess salt", "coffee and strong black tea", "alcohol",
                    "fasting", "very sour foods", "heavy meals at night"],
        "classical_ref": "Charaka Chikitsa 28 (Vatavyadhi — Bhrama); Ashtanga Hridayam Sutra 17",
    },
    "low_blood_pressure": {
        "ayurvedic_name": "Nyuna Rakta Chapa (no direct classical counterpart; "
                          "treated as Ojas and Bala Kshaya)",
        "modern_extrapolated": True,
        "pathya": ["adequate salt — unlike hypertension, this is not restricted",
                   "soaked raisins (Draksha)", "dates (Kharjura)", "cow's milk",
                   "cow's ghee", "Ashwagandha and Yashtimadhu preparations",
                   "small frequent meals", "adequate fluids"],
        "apathya": ["fasting and skipping meals", "alcohol",
                    "excess bitter and astringent foods", "dehydration",
                    "standing up abruptly after eating"],
        "classical_ref": "Extrapolated from Charaka Sutra 21 (Ojas) and Charaka Sutra 11; "
                         "no classical Nidana describes this entity directly",
    },
    "long_covid": {
        "ayurvedic_name": "Post-viral Dhatu Kshaya with residual Ama "
                          "(closest classical parallel: Jirna Jwara)",
        "modern_extrapolated": True,
        "pathya": ["warm easily digestible food", "moong soup", "rice gruel (Peya)",
                   "dry ginger (Shunthi)", "tulsi", "amla (Amalaki)",
                   "adequate protein once Agni returns", "Rasayana once Ama has cleared"],
        "apathya": ["heavy and deep-fried foods", "cold and refrigerated food",
                    "fermented foods", "Rasayana given before Ama has cleared",
                    "sleeping during the day", "exertion beyond capacity"],
        "classical_ref": "Extrapolated from Charaka Chikitsa 3 (Jwara — Jirna Jwara and "
                         "Jwaramukti); no classical Nidana describes this entity directly",
    },
    "diabetes": {
        "ayurvedic_name": "Prameha / Madhumeha",
        "pathya": ["bitter gourd (Karela)", "fenugreek seeds (Methi)", "barley (Yava)", "moong dal (Mudga)", "amla (Amalaki)", "turmeric (Haridra)", "neem leaves (Nimba)"],
        "apathya": ["sugar", "jaggery in excess", "white rice", "maida/refined flour", "sweet fruits", "heavy dairy", "cold drinks"],
        "classical_ref": "Charaka Chikitsa Sthana 6 (Prameha Chikitsa); Ashtanga Hridayam Nidana 10",
    },
    "hypertension": {
        "ayurvedic_name": "Rakta Gata Vata / Uchcha Rakta Chapa",
        "pathya": ["garlic (Lasuna)", "amla", "pomegranate (Dadima)", "cucumber", "banana (Kadali)", "celery", "moong dal", "barley"],
        "apathya": ["excess salt", "pickles", "processed foods", "red meat", "alcohol", "excess chilli", "heavy fried foods"],
        "classical_ref": "Charaka Chikitsa 28 (Vatavyadhi); Ashtanga Hridayam Chikitsa 20",
    },
    "pcos": {
        "ayurvedic_name": "Artava Dushti / Pushpa Dushti",
        "pathya": ["flaxseeds (Atasi)", "fenugreek (Methi)", "spearmint (Pudina)", "amla", "sesame seeds", "moong dal", "millet (Shyamaka)"],
        "apathya": ["sugar", "refined carbs", "heavy dairy", "red meat", "soy in excess", "cold foods"],
        "classical_ref": "Charaka Chikitsa 30 (Yonivyapad); Astanga Samgraha",
    },
    "hypothyroid": {
        "ayurvedic_name": "Galaganda / Kapha-Vata Vyadhi",
        "pathya": ["coconut oil", "pumpkin seeds", "ginger (Shunthi)", "black pepper (Maricha)", "guggul-supported foods", "iodine-rich seaweeds (if available)"],
        "apathya": ["raw crucifers (cabbage, broccoli, cauliflower, kale)", "soy in excess", "gluten (if sensitive)", "refined sugar"],
        "classical_ref": "Charaka Nidana 11 (Galaganda); Sushruta Nidana 11",
    },
    # Carries what the separate `thyroid_disorder` entry held, for the same reason
    # as `ibs` above.
    "thyroid": {
        "ayurvedic_name": "Galaganda",
        "pathya": ["ginger", "black pepper", "coconut oil", "pumpkin seeds", "tulsi",
                   "selenium-rich foods"],
        "apathya": ["raw crucifers", "soy", "refined sugar"],
        "classical_ref": "Charaka Nidana 11; Sushruta Nidana 11",
    },
    "obesity": {
        "ayurvedic_name": "Sthoulya",
        "pathya": ["barley (Yava)", "old rice (Puranashali)", "moong dal (Mudga)", "honey (Madhu)", "bitter gourd", "drumstick (Shigru)", "horse gram (Kulatha)"],
        "apathya": ["new rice", "heavy wheat", "sugar", "excess dairy", "sweets", "cold foods", "sleeping after meals"],
        "classical_ref": "Charaka Sutra 21 (Sthoulya Nidana); Charaka Chikitsa 15",
    },
    # Carries what the separate `grahani` entry held: the two were near-duplicate
    # hints for one disease, and `grahani` now canonicalises onto this key, which
    # would have left its Pathya unreachable.
    "ibs": {
        "ayurvedic_name": "Grahani / Atisara",
        "pathya": ["bael fruit (Bilwa)", "pomegranate (Dadima)", "Peya (thin rice gruel)",
                   "Yavagu (thick gruel)", "ginger tea", "moong dal soup (thin)",
                   "buttermilk (Takra) with ginger and rock salt", "cumin water (Jeeraka Jala)"],
        "apathya": ["raw vegetables", "gas-forming foods (cabbage, broccoli, beans)",
                    "sour foods (curd, sour fruits)", "heavy dairy", "cold milk",
                    "cold water", "fried foods",
                    "incompatible food combinations (Viruddha Ahara)",
                    "eating before the previous meal is digested"],
        "classical_ref": "Charaka Chikitsa 15 (Grahani Chikitsa); Ashtanga Hridayam Nidana 8",
    },
    "arsha": {
        "ayurvedic_name": "Arsha (Haemorrhoids / Piles)",
        "pathya": ["horse gram (Kulatha)", "wheat (Godhuma) without bran loss", "old rice", "buttermilk", "drumstick (Shigru) flowers", "Haritaki (Chebulic myrobalan)", "pomegranate"],
        "apathya": ["excess spicy food", "fried food", "beans causing flatulence", "sitting for long hours after eating", "suppression of natural urges"],
        "classical_ref": "Charaka Chikitsa 14 (Arsha Chikitsa); Sushruta Nidana 2",
    },
    "anemia": {
        "ayurvedic_name": "Pandu Roga",
        "pathya": ["pomegranate (Dadima)", "amla (Amalaki)", "dates (Kharjura)", "beetroot", "spinach (Palaka) cooked with iron vessel or sesame", "sesame seeds (Tila)", "jaggery (Guda) with amla"],
        "apathya": ["clay eating", "excess raw food", "cold water", "curd with milk", "excess exercise during treatment"],
        "classical_ref": "Charaka Chikitsa 16 (Pandu Roga Chikitsa); Ashtanga Hridayam Chikitsa 13",
    },
    "fatty_liver": {
        "ayurvedic_name": "Yakrit Vikara / Yakrit Vriddhi",
        "pathya": ["turmeric (Haridra)", "amla", "kutki (Picrorhiza kurroa)", "moong dal", "leafy greens (cooked)", "bitter gourd", "garlic"],
        "apathya": ["alcohol (absolute contraindication)", "excess oil and fat", "processed foods", "sugar", "red meat", "cold foods"],
        "classical_ref": "Charaka Chikitsa 18 (Kamala Chikitsa); Sushruta Uttara 44",
    },
    "high_cholesterol": {
        "ayurvedic_name": "Medoroga / Rasa-Meda Dushti",
        "pathya": ["garlic (Lasuna)", "amla", "guggulu-supported foods", "barley (Yava)", "moong dal", "fenugreek (Methi)", "cooked leafy greens", "flaxseeds"],
        "apathya": ["fried foods", "vanaspati / dalda", "excess ghee and butter", "red meat", "cheese", "refined sugar", "cold heavy foods"],
        "classical_ref": "Charaka Sutrasthana 21 (Ashtauninditiya); Ashtanga Hridayam Sutrasthana 14 (Medoroga)",
    },
    "kidney_disease": {
        "ayurvedic_name": "Mutraghata / Mutrakrichra / Vrikkavikara",
        "pathya": ["old rice (Puranashali)", "moong dal (very well cooked)", "barley water (Yava Jala)", "apple", "cooked cabbage (low potassium)"],
        "apathya": ["banana (high potassium)", "tomato", "spinach in large amounts", "excess protein", "excess salt", "pickle", "sour fruits"],
        "classical_ref": "Charaka Chikitsa 26 (Mutraghata); Sushruta Nidana 3",
    },
    "amavata": {
        "ayurvedic_name": "Amavata (Rheumatoid Arthritis)",
        "pathya": ["ginger (Shunthi) — most important", "garlic (Lasuna)", "horse gram (Kulatha) soup", "castor oil (Eranda) with warm water", "moong dal with turmeric", "Rasona Kshira (garlic milk)"],
        "apathya": ["curd (Dadhi)", "fish", "black gram (Urad)", "new rice", "cold foods", "refrigerated food", "incompatible food combinations"],
        "classical_ref": "Madhava Nidana 25 (Amavata Nidana); Yogaratnakara Amavata Chikitsa",
    },
    "asthma": {
        "ayurvedic_name": "Tamaka Shwasa",
        "pathya": ["ginger (Shunthi)", "black pepper (Maricha)", "long pepper (Pippali)", "honey (Madhu)", "warm foods", "Tulsi tea", "light easily digestible foods"],
        "apathya": ["cold foods", "cold water", "curd", "banana", "ice cream", "fried foods", "excess sweet taste", "fish and dairy together"],
        "classical_ref": "Charaka Chikitsa 17 (Shwasa Chikitsa); Ashtanga Hridayam Chikitsa 4",
    },
    "migraine": {
        "ayurvedic_name": "Ardhavabhedaka / Suryavarta",
        "pathya": ["coriander seeds water", "amla", "pomegranate", "moong dal", "cucumber", "cooling foods for Pitta type"],
        "apathya": ["excess sour, salty, pungent foods", "red wine/alcohol", "aged cheese", "chocolate", "onion in excess", "skipping meals"],
        "classical_ref": "Charaka Sutra 20; Ashtanga Hridayam Uttara 23",
    },
    "psoriasis": {
        "ayurvedic_name": "Kitibha Kushtha / Mandal Kushtha",
        "pathya": ["neem (Nimba) preparations", "turmeric", "bitter gourd", "amla", "moong dal", "old rice", "cucumber"],
        "apathya": ["fish and milk together", "sour foods", "sesame + milk", "meat + milk", "salt + milk", "incompatible combinations"],
        "classical_ref": "Charaka Chikitsa 7 (Kushtha Chikitsa); Ashtanga Hridayam Chikitsa 19",
    },
    "constipation": {
        "ayurvedic_name": "Vibandha / Anaha",
        "pathya": ["warm water in morning", "castor oil (Eranda) in milk", "figs (Anjeer)", "flaxseeds", "psyllium husk", "triphala (Haritaki, Amalaki, Bibhitaki)", "ghee in food"],
        "apathya": ["dry, light foods in excess", "cold water", "suppressing the urge to defecate", "excess travel/exertion"],
        "classical_ref": "Charaka Sutra 28; Ashtanga Hridayam Chikitsa 9",
    },
    # Adhmana is the one `gut_health_issue` value that was not already a canonical
    # condition. Authored here rather than aliased onto IBS or constipation: its
    # Samprapti is Vata trapped by Ama in the Pakvashaya, so the Apathya is the
    # Vatala and Abhishyandi foods — not IBS's sour and raw list, and not
    # constipation's dry and cold one. Authored, NOT clinically reviewed.
    "bloating": {
        "ayurvedic_name": "Adhmana / Anaha (Vata-Ama in the Pakvashaya)",
        "pathya": ["hing (Hingu) in the tadka", "ajwain (Yavani) water",
                   "cumin-coriander-fennel water", "ginger with rock salt before meals",
                   "moong dal (well cooked, thin)", "buttermilk (Takra) with ajwain",
                   "warm cooked vegetables", "old rice"],
        "apathya": ["raw salads", "cabbage, cauliflower and broccoli",
                    "rajma, chana and other heavy legumes", "carbonated drinks",
                    "curd at night", "cold water with meals",
                    "eating before the previous meal is digested",
                    "suppressing the urge to pass flatus"],
        "classical_ref": "Charaka Sutra 19 (Anaha); Ashtanga Hridayam Nidana 8",
    },
    "acidity": {
        "ayurvedic_name": "Amlapitta",
        "pathya": ["coconut water (Narikela Jala)", "pomegranate", "coriander seeds water", "amla", "fennel (Shatapushpa)", "old rice", "ghee", "milk (warm)"],
        "apathya": ["sour foods", "fermented foods", "chilli", "garlic", "onion", "coffee", "alcohol", "eating before previous meal digests"],
        "classical_ref": "Charaka Chikitsa 15 (Amlapitta); Ashtanga Hridayam Chikitsa 10",
    },
}

# Canonical condition keys live in `ahara_safety`, which is the layer that enforces
# them. This module kept its own map, and the two disagreed on 22 inputs — and because
# `uncurated_conditions()` skips the LLM classifier whenever the BRIEF recognises a
# condition, every input the brief canonicalised and the scan did not was left with no
# deterministic floor at all. See `_COND_CANON` for the list.
COND_ALIASES = _COND_CANON

AGNI_DESC: dict[str, str] = {
    "sama":    "balanced and strong — can handle a varied diet with regular timing",
    "manda":   "slow and sluggish (Kapha dominant) — needs light, warm, spiced, easily digestible foods; avoid heavy meals; fasting one meal helps kindle Agni",
    "tikshna": "sharp and intense (Pitta dominant) — must not skip meals; needs regular nourishment; avoid fasting; favour cooling foods",
    "vishama": "irregular and variable (Vata dominant) — needs grounding, consistent meal times; warm, moist, easily digestible foods; most sensitive to cold and irregular eating",
}

AMA_DESC: dict[str, str] = {
    "high":     "high toxic load — Ama is present and must be cleared first; all foods should be Deepaniya (Agni-kindling) and Pachana (Ama-digesting); avoid heavy, sour, cold, and incompatible foods",
    "moderate": "moderate Ama — dietary refinement needed; avoid Ama-producing combinations; favour ginger, cumin, turmeric",
    "low":      "minimal Ama — diet can be more varied",
    "none":     "no Ama — normal Ayurvedic diet appropriate",
}

SEASON_GUIDANCE: dict[str, str] = {
    "vasanta": "Vasanta Ritucharya (Spring): Kapha accumulated in winter now liquefies — kindle Agni with pungent, bitter, astringent foods. Avoid heavy dairy, excess sweet, oily foods. Favour: barley, bitter gourd, light grains. Classical reference: Ashtanga Hridayam Sutra 3",
    "grishma": "Grishma Ritucharya (Summer): Agni is naturally weak; body needs cooling, sweet, hydrating foods. Avoid pungent, sour, salty, hot foods. Favour: coconut water, cucumber, amla, sweet fruits, light rice. Reference: Charaka Sutra 6.27",
    "varsha":  "Varsha Ritucharya (Rainy Season): Agni is at its lowest; Vata is aggravated by cool, damp winds. Light, warm, freshly cooked foods essential. Avoid leafy greens (worm/bacteria risk), river water. Favour: moong dal, old rice, ginger, warm soups. Reference: Charaka Sutra 6.32",
    "sharad":  "Sharad Ritucharya (Autumn): Post-monsoon Pitta aggravation — cooling, sweet, astringent foods. Avoid excess sour, salty, pungent. Favour: bitter gourd, pomegranate, amla, light rice, ghee. This season is best for Virechana if Pitta is aggravated. Reference: Charaka Sutra 6.41",
    "hemanta": "Hemanta Ritucharya (Early Winter): Agni is strongest — can handle heavier, nourishing foods. Ideal season for Brimhana (nourishing) diet. Favour: wheat, sesame, ghee, milk, meat (if applicable), urad dal, jaggery. Reference: Charaka Sutra 6.7",
    "shishira": "Shishira Ritucharya (Late Winter): Similar to Hemanta; deep Agni, need for Snehana (oleation) diet. Sour, salty, oily foods appropriate. Favour: ghee, sesame, warming spices, nourishing grains. Reference: Ashtanga Hridayam Sutra 3",
}

# ── Allergen term lookup for post-LLM safety scan ─────────────────────────────
# The allergen and intolerance term lists live in `ahara_safety`, which is the layer
# that enforces them. This module kept its own copy, and the copies drifted: the copy
# here was missing every one of the four `food_intolerances` values, so `flag_allergens`
# resolved `lactose` through `.get(key, [key])` and scanned meal text for the literal
# word "lactose" — the exact failure PR #61 fixed in `apply_ahara_safety` and only
# there. It also disagreed with the live list on 8 of the 10 keys it did have.
from services.ahara_safety import ALLERGEN_TERMS  # noqa: E402  (re-exported below)


# ── Multi-condition conflict resolution ───────────────────────────────────────
# When a patient has several diseases, a food can be Pathya (recommended) for one
# and Apathya (contraindicated) for another — e.g. spinach helps anemia but is
# restricted in kidney disease. Left implicit, the LLM may centre a meal on such a
# food and then the deterministic safety scan flags it everywhere. We detect these
# conflicts up front and hand the LLM an explicit resolution rule.
#
# Priority: lower number = more restrictive / safety-critical → its "avoid" wins
# when the whole diet is pulled two ways.
_CONDITION_PRIORITY: dict[str, int] = {
    "kidney_disease": 1,
    "fatty_liver": 2, "diabetes": 2, "hypertension": 2, "high_cholesterol": 2,
    "pcos": 2, "hypothyroid": 2, "thyroid": 2, "obesity": 2, "acidity": 2,
    "amavata": 2, "rheumatoid_arthritis": 2, "asthma": 2, "psoriasis": 2,
    "anemia": 3, "constipation": 3, "grahani": 3, "ibs": 3, "migraine": 3, "arsha": 3,
}

# Words that qualify a food phrase but aren't the food itself.
_FOOD_QUALIFIERS = frozenset({
    "excess", "old", "new", "cold", "hot", "heavy", "raw", "refined", "low", "high",
    "very", "well", "cooked", "dried", "fresh", "incompatible", "processed", "in",
    "large", "small", "amounts", "amount",
})
# Headwords that are too generic to be a real food-conflict signal.
_GENERIC_FOOD_WORDS = frozenset({
    "food", "foods", "water", "exercise", "eating", "combinations", "combination",
    "treatment", "drinks", "diet", "meal", "meals", "items",
})


def normalize_condition_key(cond: str) -> str:
    """Canonical diet key for a stored or free-text condition.

    Delegates to `ahara_safety._canon_condition` so the brief and the scan cannot
    reach different conclusions about which disease the patient has. It used to
    double-pass its own alias map; chains are now resolved in the table itself.
    """
    return _canon_condition(cond)


# ── The diseases the diet path must treat ─────────────────────────────────────
# `gut_health_issue` is asked on the diet preferences form and its four values are
# diseases: three of them — acidity, constipation, ibs — are already canonical keys
# with a `PATHYA_APATHYA_HINTS` block, a `_CONDITION_APATHYA_TERMS` floor and
# authored `apathya_for` / `pathya_for` claims on the 150 library rows.
#
# None of that reached them. The answer was rendered into the brief as the single
# line `GUT HEALTH: Acidity` and went nowhere else: the condition list came from
# `medical_history` alone, so the brief carried no Pathya-Apathya block, named none
# of the library's Apathya foods, and `apply_condition_food_safety` scanned the
# meals against nothing. Measured on the same patient, the same disease declared on
# the diet form produced a 1,812-character brief with 0 Apathya foods named; declared
# in `medical_history` it produced 3,789 characters and 50.
#
# It is the shape PR #77 found in Panchakarma — a question asked at check-in whose
# answer no engine could see — and the fix is the same: one function, used by the
# brief and by the safety scan, so a disease cannot be visible to one and not the
# other.
_GUT_ISSUE_CONDITIONS: dict[str, str] = {
    "acidity": "acidity",
    "constipation": "constipation",
    "bloating": "bloating",
    "ibs": "ibs",
    # "healthy" declares no disease and adds nothing.
}


def diet_conditions(user_profile: dict, diet_prefs: dict | None = None) -> list[str]:
    """Every disease the diet path must treat, from both places the app collects one.

    `medical_history` (onboarding) plus `gut_health_issue` (the diet form). Returns
    canonical keys, deduplicated, with `medical_history` first so a condition
    declared in both keeps its original spelling in the brief's heading.

    Every caller that builds a condition list for the diet path goes through here.
    Passing `diet_prefs=None` gives the medical-history-only list, which is what a
    caller with no preferences document has.
    """
    out: list[str] = []
    seen: set[str] = set()
    for cond in (user_profile.get("medical_history") or []):
        canon = normalize_condition_key(cond)
        if canon and canon not in seen:
            seen.add(canon)
            out.append(canon)
    gut = str((diet_prefs or {}).get("gut_health_issue") or "healthy").strip().lower()
    canon = _GUT_ISSUE_CONDITIONS.get(gut)
    if canon and canon not in seen:
        seen.add(canon)
        out.append(canon)
    return out


def diet_allergies(user_profile: dict, diet_prefs: dict | None = None) -> list[str]:
    """Every allergy the app holds for this patient, from both places it stores one.

    `diet_prefs["food_allergies"]` (the diet form) and `user_profile["allergies"]`
    (onboarding). The diet path read only the first, so an allergy declared once, in
    the health step, was enforced by the remedies engine and by nothing in the one
    feature that is entirely about food.

    An allergy is the one declaration where asking twice and honouring one answer is
    not acceptable, so this is a union and never a choice between them.
    """
    out: list[str] = []
    seen: set[str] = set()
    for source in ((diet_prefs or {}).get("food_allergies") or [],
                   user_profile.get("allergies") or []):
        for a in source:
            key = str(a).strip().lower().replace(" ", "_")
            if key and key not in seen:
                seen.add(key)
                out.append(key)
    return out


def uncurated_conditions(conditions: list[str]) -> list[str]:
    """Conditions with NO curated Pathya/Apathya hint — the only ones that should
    be sent to the LLM Apathya classifier. Curated conditions are authoritative and
    must not be overwritten by an LLM guess (which mislabels e.g. sesame for anemia)."""
    out = []
    for c in conditions or []:
        if normalize_condition_key(c) not in PATHYA_APATHYA_HINTS:
            out.append(c)
    return out


def _food_headword(phrase: str) -> str:
    """Extract the core food word from a Pathya/Apathya phrase.

    'banana (high potassium)' → 'banana'; 'spinach in large amounts' → 'spinach';
    'jaggery in excess' → 'jaggery'; 'old rice' → 'rice'; 'cold foods' → '' (generic).
    """
    import re as _re
    s = _re.sub(r"\([^)]*\)", " ", str(phrase).lower())   # drop parentheticals
    s = _re.sub(r"[^a-z\s]", " ", s)                       # keep letters
    for tok in s.split():
        if tok in _FOOD_QUALIFIERS:
            continue
        if tok in _GENERIC_FOOD_WORDS or len(tok) <= 2:
            return ""       # generic-led phrase → no reliable food signal
        return tok
    return ""


def _pretty_cond(canon: str) -> str:
    label = canon.replace("_", " ").title()
    ayur = (PATHYA_APATHYA_HINTS.get(canon) or {}).get("ayurvedic_name")
    return f"{label} ({ayur})" if ayur else label


def detect_condition_conflicts(norm_conditions: list[str]) -> list[dict]:
    """Foods that are beneficial for one of the patient's conditions but
    contraindicated for another. Returns [{food, beneficial_for, contraindicated_for}]."""
    conds = [c for c in dict.fromkeys(norm_conditions) if c in PATHYA_APATHYA_HINTS]
    if len(conds) < 2:
        return []
    # Map each condition to its set of Pathya / Apathya headwords.
    pathya_words: dict[str, dict[str, str]] = {}   # cond -> {headword: original phrase}
    apathya_words: dict[str, dict[str, str]] = {}
    for c in conds:
        h = PATHYA_APATHYA_HINTS[c]
        pathya_words[c] = {hw: p for p in h.get("pathya", []) if (hw := _food_headword(p))}
        apathya_words[c] = {hw: a for a in h.get("apathya", []) if (hw := _food_headword(a))}

    conflicts: dict[str, dict] = {}
    for benefit_c in conds:
        for hw, phrase in pathya_words[benefit_c].items():
            for avoid_c in conds:
                if avoid_c == benefit_c:
                    continue
                if hw in apathya_words[avoid_c]:
                    entry = conflicts.setdefault(hw, {
                        "food": hw, "beneficial_for": set(), "contraindicated_for": set(),
                    })
                    entry["beneficial_for"].add(benefit_c)
                    entry["contraindicated_for"].add(avoid_c)
    # Serialise, sorting contraindicating condition by priority (most critical first).
    out = []
    for hw, e in conflicts.items():
        out.append({
            "food": hw,
            "beneficial_for": sorted(e["beneficial_for"]),
            "contraindicated_for": sorted(e["contraindicated_for"],
                                          key=lambda c: _CONDITION_PRIORITY.get(c, 3)),
        })
    return sorted(out, key=lambda x: x["food"])


def _conflict_section(norm_conditions: list[str]) -> str:
    """Brief section instructing the LLM how to resolve multi-condition food conflicts."""
    conflicts = detect_condition_conflicts(norm_conditions)
    known = [c for c in dict.fromkeys(norm_conditions) if c in PATHYA_APATHYA_HINTS]
    if not conflicts:
        return ""
    primary = min(known, key=lambda c: _CONDITION_PRIORITY.get(c, 3))
    lines = [
        "\n\n⚠️ MULTIPLE CONDITIONS — CONFLICT RESOLUTION (critical, resolve deterministically):",
        f"  Primary condition (its restrictions win when foods conflict): {_pretty_cond(primary)}",
        "  Specific food conflicts detected:",
    ]
    for c in conflicts:
        benefit = ", ".join(x.replace("_", " ").title() for x in c["beneficial_for"])
        avoid = ", ".join(x.replace("_", " ").title() for x in c["contraindicated_for"])
        lines.append(
            f"    • {c['food'].title()} — beneficial for {benefit}, but contraindicated for {avoid}. "
            f"AVOID it and meet the lost benefit with a substitute that is safe for ALL of this "
            f"patient's conditions."
        )
    lines.append(
        "  RULE: when a food helps one condition but harms another, AVOID it (safety first) and "
        "replace its benefit with an alternative that is not Apathya for any of this patient's diseases."
    )
    return "\n".join(lines)


def target_calories(user_profile: dict, diet_prefs: dict) -> int:
    """Deprecated — kept only so callers outside this module keep working.

    This read neither height, weight nor activity level: a very active 82 kg woman and
    a sedentary 78 kg woman were both told 1200 kcal. `services.diet_energy` computes
    the target from the patient's actual body, and `build_brief` now uses that.
    """
    from services.diet_energy import energy_target
    return energy_target(user_profile, diet_prefs)["target_calories"]


def build_brief(user_profile: dict, diet_prefs: dict) -> str:
    """Build the classical Ayurvedic patient brief string passed to the LLM."""
    dominant_dosha = (user_profile.get("dominant_dosha") or "vata").lower()
    vikriti = (user_profile.get("vikriti_dominant") or dominant_dosha).lower()
    vikriti_secondary = (user_profile.get("vikriti_secondary") or "").lower()
    agni = (user_profile.get("agni_type") or "sama").lower()
    ama = (user_profile.get("ama_indicator") or "none").lower()
    ojas = (user_profile.get("ojas_level") or "moderate").lower()
    koshtha = (user_profile.get("koshtha") or "").lower()
    age = user_profile.get("age") or "unknown"
    gender = (user_profile.get("gender") or "not specified").title()
    is_pregnant = user_profile.get("pregnancy_or_nursing") or False
    season = (user_profile.get("current_season") or "").lower()
    stress = (user_profile.get("stress_level") or "moderate").lower()
    sleep = (user_profile.get("sleep_quality") or "moderate").lower()
    bmi = (user_profile.get("bmi_category") or "normal").lower()
    name = user_profile.get("name") or user_profile.get("full_name") or "the patient"

    diet_type = diet_prefs.get("dietary_type") or "vegetarian"
    allergies = diet_allergies(user_profile, diet_prefs)
    intolerances = diet_prefs.get("food_intolerances") or []
    gut = diet_prefs.get("gut_health_issue") or "healthy"
    goal = diet_prefs.get("diet_goal") or "general_wellness"
    fasting_days = diet_prefs.get("fasting_days") or []
    if_window = diet_prefs.get("intermittent_fasting") or "no"
    water = diet_prefs.get("water_intake") or "1-2L"

    # Both places the app collects a disease — `medical_history` and the diet form's
    # own `gut_health_issue`. The second used to reach the model as the single line
    # `GUT HEALTH: Acidity` and nothing else.
    norm_conditions = diet_conditions(user_profile, diet_prefs)
    conditions = norm_conditions

    cond_blocks = []
    seen: set = set()
    for cond in norm_conditions:
        canon = COND_ALIASES.get(cond, cond)
        if canon in seen:
            continue
        seen.add(canon)
        hint = PATHYA_APATHYA_HINTS.get(canon)
        if hint:
            block = (
                f"  • {cond.replace('_', ' ').title()} ({hint['ayurvedic_name']}):\n"
                f"    Pathya: {', '.join(hint['pathya'][:6])}\n"
                f"    Apathya: {', '.join(hint['apathya'][:5])}\n"
                f"    Ref: {hint['classical_ref']}"
            )
        else:
            block = (
                f"  • {cond.replace('_', ' ').title()} — use your classical Ayurvedic knowledge "
                f"to determine Pathya-Apathya. Cite the relevant Samhita chapter."
            )
        # The authored library's own claims for this disease, by name. The hint above
        # is prose written per condition; these are the 150 rows of
        # `diet_foods.json`, where each (condition, food) pair was authored
        # individually. They reached the model only as scattered RAG passages before
        # — `apathya_for` was read by `diet_plan_engine`, which is the fallback, and
        # `pathya_for` by nothing at all.
        lib = condition_food_rules(canon)
        if lib["apathya_names"]:
            block += (
                f"\n    DO NOT USE (library Apathya for this disease — "
                f"{len(lib['apathya_names'])} foods): "
                f"{', '.join(lib['apathya_names'])}"
            )
        if lib["pathya_names"]:
            # Pathya is advisory, so it is capped; Apathya above is not, because a
            # truncated list of things to avoid is a list that fails silently.
            shown = lib["pathya_names"][:30]
            block += (
                f"\n    PREFER (library Pathya): {', '.join(shown)}"
                + (f" (+{len(lib['pathya_names']) - len(shown)} more)"
                   if len(lib["pathya_names"]) > len(shown) else "")
            )
        cond_blocks.append(block)

    cond_section = "\n".join(cond_blocks) if cond_blocks else "  • None reported"
    # Multi-condition conflict resolution — appended right after the conditions list.
    cond_section += _conflict_section(norm_conditions)
    season_guidance = SEASON_GUIDANCE.get(season, "No specific season provided — use general Ayurvedic diet principles.")

    hard_constraints = [
        f"Dietary type: {diet_type} (STRICTLY honour — never recommend non-{diet_type} items). "
        f"Ayura serves vegetarian and vegan plans only: the authored food library has no "
        f"egg, fish or meat row, so an animal-food meal reaches the patient screened "
        f"against none of their conditions."
    ]
    if allergies:
        hard_constraints.append(f"ALLERGIES (absolutely avoid): {', '.join(allergies)}")
    if intolerances:
        hard_constraints.append(f"Intolerances (avoid): {', '.join(intolerances)}")
    if fasting_days:
        hard_constraints.append(f"Fasting days: {', '.join(fasting_days)} — only Phalahar (fruits, milk, nuts) on these days")
    if if_window != "no":
        hard_constraints.append(f"Intermittent fasting: {if_window} window — adjust meal timing accordingly")
    if is_pregnant:
        hard_constraints.append(
            "PREGNANCY / NURSING — absolutely avoid: papaya (raw/ripe), pineapple, excess fenugreek seeds, "
            "excess aloe vera, high-dose turmeric, hot spices in large amounts, liver/organ meat, "
            "unpasteurised dairy; all meals must be Satvic, warm, and nourishing (Garbhini Paricharya)"
        )

    # The gut issue is now carried in MEDICAL CONDITIONS with a full Pathya-Apathya
    # block. This line stays because it says something that list cannot: which of the
    # patient's diseases is the presenting complaint — the reason they opened the diet
    # form — as opposed to a comorbidity carried over from onboarding.
    if gut in _GUT_ISSUE_CONDITIONS:
        gut_line = (f"GUT HEALTH: {gut.replace('_', ' ').title()} — the presenting digestive "
                    f"complaint, and the primary target of this plan. Its Pathya-Apathya is "
                    f"listed under MEDICAL CONDITIONS above.")
    else:
        gut_line = f"GUT HEALTH: {gut.replace('_', ' ').title()}"

    _KOSHTHA_DESC = {
        "krura": "Krura Koshtha (hard bowel — constipation tendency) — use more ghee, warm water, soaked dried fruits; avoid dry/astringent foods",
        "mridu": "Mridu Koshtha (soft bowel — loose stool tendency) — favour astringent, binding foods; avoid excess oil, sour, and heavy dairy",
        "madhyama": "Madhyama Koshtha (balanced bowel) — general Ayurvedic diet applies",
    }
    koshtha_line = f"\n  Koshtha (bowel constitution): {_KOSHTHA_DESC.get(koshtha, koshtha.title())}" if koshtha else ""

    # The brief used to end on "TARGET CALORIES: approximately N kcal/day" and nothing
    # else, and the model divided that by eye: measured plans came back at 585-720 kcal
    # against a stated 1200, and 1240-1410 against a stated 2400. A per-meal budget
    # gives each meal an anchor instead of leaving the split to the model.
    from services.diet_energy import energy_target
    energy = energy_target(user_profile, diet_prefs)
    mb = energy["meal_budget"]
    energy_block = f"""ENERGY PRESCRIPTION (a clinical target, not a suggestion):
  Daily total: {energy['target_calories']} kcal. Every day of every week must land \
within {energy['band'][0]}-{energy['band'][1]} kcal.
  A day totalling far less than this is a failed plan, not a light one.
  Per-meal budget: breakfast ~{mb['breakfast']} kcal | lunch ~{mb['lunch']} kcal | \
snack ~{mb['snack']} kcal | dinner ~{mb['dinner']} kcal
  Minimum protein: {energy['protein_floor_g']} g/day across the four meals.
  Portions must be sized to deliver this. State the portion in a measurable unit
  (katori/ml/g/pieces) and make `macros_approx` honest for that portion — the figures
  are shown to the patient and are summed into a daily total on screen."""
    if energy["basis"] == "measured":
        energy_block += (
            f"\n  Basis: BMR {energy['bmr']} kcal, maintenance {energy['tdee']} kcal at the "
            f"patient's stated activity level."
        )
    for _note in energy["notes"]:
        energy_block += f"\n  Note: {_note}"

    return f"""PATIENT: {name} | Age: {age} | Gender: {gender}{' | PREGNANT/NURSING' if is_pregnant else ''}

PRAKRITI & VIKRITI:
  Prakriti (constitutional): {dominant_dosha.title()}
  Vikriti (current imbalance): {vikriti.title()}{(' + ' + vikriti_secondary.title()) if vikriti_secondary else ''}
  (If Prakriti ≠ Vikriti, treat the Vikriti preferentially while supporting Prakriti)

DIGESTIVE FIRE (AGNI):
  Type: {agni.title()} — {AGNI_DESC.get(agni, 'balanced')}{koshtha_line}

AMA STATUS:
  Level: {ama.title()} — {AMA_DESC.get(ama, 'none present')}

OJAS & VITALITY:
  Ojas level: {ojas.title()}
  Stress: {stress.title()} | Sleep quality: {sleep.title()}
  BMI category: {bmi.title()}

CURRENT SEASON (RITUCHARYA):
  {season_guidance}

MEDICAL CONDITIONS (Pathya-Apathya required for each):
{cond_section}

{gut_line}

HARD DIETARY CONSTRAINTS (never violate these):
  {chr(10).join(f'  {i+1}. {c}' for i, c in enumerate(hard_constraints))}

THERAPEUTIC GOAL: {goal.replace('_', ' ').title()}
WATER INTAKE: {water} per day

{energy_block}"""


def flag_allergens(weekly_plan: dict, allergies: list[str], intolerances: list[str]) -> dict:
    """Scan key_ingredients and meal_name for allergen terms and flag meals."""
    allergen_terms: set[str] = set()
    for a in (allergies or []) + (intolerances or []):
        key = str(a).lower()
        allergen_terms.update(ALLERGEN_TERMS.get(key, [key]))
    if not allergen_terms:
        return weekly_plan
    for day_data in weekly_plan.values():
        if not isinstance(day_data, dict):
            continue
        # The daily drink is scanned here too. It had its own copy of the four-slot
        # list, so the badge `DietView` renders on an unsafe meal could never appear
        # on an unsafe drink.
        for meal_key in ("breakfast", "lunch", "snack", "dinner", "special_drink"):
            meal = day_data.get(meal_key)
            if not isinstance(meal, dict):
                continue
            # A drink names its contents in `name` + `recipe`; a meal in
            # `meal_name` + `key_ingredients`. Read both shapes rather than
            # duplicating the slot list again.
            text = " ".join([
                str(meal.get("meal_name", "")),
                str(meal.get("name", "")),
                str(meal.get("description", "")),
                str(meal.get("recipe", "")),
                " ".join(meal.get("key_ingredients", []) or []),
            ]).lower()
            found = [t for t in allergen_terms if _term_in_text(t, text)]
            if found:
                meal["allergen_warning"] = True
                meal["allergen_terms"] = found
    return weekly_plan
