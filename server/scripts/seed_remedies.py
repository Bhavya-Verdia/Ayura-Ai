import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of 60 unique symptoms with 3 dosha-specific remedies each
REMEDIES_DATA = [
    # ── PAIN (10) ────────────────────────
    {
        "id": "headache", "symptom_id": "headache", "symptom_display": "Headache", "symptom_category": "pain",
        "dosha_cause": {"vata": "anxiety, dehydration, irregular sleep", "pitta": "excess heat, acidity, anger", "kapha": "congestion, sluggishness, heaviness"},
        "remedies": {
            "vata": {
                "name": "Warm Sesame Oil Scalp Massage with Brahmi",
                "ingredients": [{"item": "sesame oil", "amount": "2 tbsp", "preparation": "warmed"}, {"item": "brahmi powder", "amount": "1 tsp", "preparation": "optional"}],
                "preparation": "Warm sesame oil to body temperature. Massage into scalp in slow circular motions for 10-15 minutes focusing on crown and temples. Leave for 30 minutes then wash with warm water.",
                "dosage": "Once daily, preferably before sleep", "duration": "3-5 days", "expected_relief": "1-2 days"
            },
            "pitta": {
                "name": "Sandalwood Paste and Amalaki Cooling Remedy",
                "ingredients": [{"item": "sandalwood powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "rose water", "amount": "2 tbsp", "preparation": "cool"}, {"item": "amalaki juice", "amount": "30ml", "preparation": "fresh"}],
                "preparation": "Mix sandalwood powder with rose water to form a paste. Apply to forehead and temples. Leave for 20 minutes. Separately drink amalaki juice diluted in cool water.",
                "dosage": "Apply paste 2x daily, drink juice once", "duration": "2-3 days", "expected_relief": "Same day relief for paste"
            },
            "kapha": {
                "name": "Trikatu Steam Inhalation with Ginger Tea",
                "ingredients": [{"item": "dry ginger", "amount": "1 tsp", "preparation": "powder"}, {"item": "black pepper", "amount": "5 pieces", "preparation": "crushed"}, {"item": "pippali", "amount": "pinch", "preparation": "powder"}, {"item": "tulsi leaves", "amount": "5", "preparation": "fresh"}],
                "preparation": "Add all ingredients to 500ml boiling water. Inhale steam for 5-7 minutes with towel over head. Separately prepare ginger-tulsi tea by simmering same ingredients for 10 mins, strain and drink warm with honey.",
                "dosage": "Steam once daily, tea twice daily", "duration": "2-3 days", "expected_relief": "Within hours for steam"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Mild head massage with plain coconut oil.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if headache persists beyond 3 days or is unusually severe.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "migraine", "symptom_id": "migraine", "symptom_display": "Migraine", "symptom_category": "pain",
        "dosha_cause": {"vata": "sensory overload, wind exposure, skipped meals", "pitta": "sun exposure, visual strain, intense focus", "kapha": "sinus pressure, heavy food, sleeping after eating"},
        "remedies": {
            "vata": {
                "name": "Warm Ghee Nasya and Dashamoola Tea",
                "ingredients": [{"item": "ghee", "amount": "2 drops per nostril", "preparation": "warmed"}, {"item": "dashamoola powder", "amount": "1 tsp", "preparation": "boiled"}],
                "preparation": "Lie down and instil 2 drops of warm ghee in each nostril, sniffing gently. Separately, boil dashamoola in 1 cup water for 5 mins, strain and drink.",
                "dosage": "Nasya once daily, tea twice daily", "duration": "3 days", "expected_relief": "1 day"
            },
            "pitta": {
                "name": "Coriander Seed Infusion and Rose Water Spray",
                "ingredients": [{"item": "coriander seeds", "amount": "1 tbsp", "preparation": "crushed"}, {"item": "rose water", "amount": "spray", "preparation": "chilled"}],
                "preparation": "Soak crushed coriander seeds in cold water overnight. Strain and drink first thing in morning. Spray chilled rose water on closed eyes and forehead.",
                "dosage": "Drink once in morning, spray as needed", "duration": "3-5 days", "expected_relief": "1-2 days"
            },
            "kapha": {
                "name": "Eucalyptus Steam and Strong Ginger Application",
                "ingredients": [{"item": "eucalyptus oil", "amount": "3 drops", "preparation": "in hot water"}, {"item": "dry ginger powder", "amount": "1/2 tsp", "preparation": "paste"}],
                "preparation": "Add eucalyptus to boiling water for steam inhalation. Mix ginger powder with a few drops of hot water to make a paste, apply ONLY to temples (will burn slightly, avoid eyes).",
                "dosage": "Steam twice daily, paste once", "duration": "2 days", "expected_relief": "Within hours"
            }
        },
        "universal_remedy": None, "contraindications": ["active_fever"], "pregnancy_safe": False, "pregnancy_alternative": "Rest in a dark room with a cool compress.", "drug_interactions": [], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor immediately if migraine is accompanied by vision loss, numbness, or vomiting.", "source": "Lad", "safety_tier": "use_with_caution"
    },
    {
        "id": "joint_pain", "symptom_id": "joint_pain", "symptom_display": "Joint Pain", "symptom_category": "pain",
        "dosha_cause": {"vata": "dryness, cold weather, overexertion", "pitta": "inflammation, infection, hot foods", "kapha": "fluid retention, lack of movement, cold dampness"},
        "remedies": {
            "vata": {
                "name": "Mahanarayan Oil Massage with Ashwagandha Milk",
                "ingredients": [{"item": "mahanarayan oil (or sesame)", "amount": "1 tbsp", "preparation": "warm"}, {"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "in milk"}],
                "preparation": "Massage warm oil deeply into the affected joint. Boil ashwagandha in a cup of milk, let cool slightly, and drink before bed.",
                "dosage": "Massage daily, milk once at night", "duration": "7 days", "expected_relief": "3 days"
            },
            "pitta": {
                "name": "Cool Castor Oil Pack and Guduchi Decoction",
                "ingredients": [{"item": "castor oil", "amount": "1 tbsp", "preparation": "room temp"}, {"item": "guduchi powder", "amount": "1 tsp", "preparation": "decoction"}],
                "preparation": "Apply castor oil to the inflamed joint and wrap loosely with cotton. Boil guduchi in 2 cups water until reduced to 1 cup, cool and drink.",
                "dosage": "Pack overnight, drink once daily", "duration": "5 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Mustard Oil Friction and Guggulu Paste",
                "ingredients": [{"item": "mustard oil", "amount": "1 tbsp", "preparation": "warm"}, {"item": "guggulu", "amount": "1/2 tsp", "preparation": "paste"}],
                "preparation": "Vigorously rub warm mustard oil on the joint to generate heat. For severe stiffness, apply a warm paste of guggulu mixed with water.",
                "dosage": "Rub twice daily", "duration": "7 days", "expected_relief": "3-5 days"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Gentle massage with plain warm sesame oil.", "drug_interactions": ["immunosuppressants", "blood_thinners"], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if joint is red, hot, swollen, or restricts all movement.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "back_pain", "symptom_id": "back_pain", "symptom_display": "Back Pain", "symptom_category": "pain",
        "dosha_cause": {"vata": "muscle spasms, cold wind, dryness", "pitta": "nerve inflammation, excess heat", "kapha": "stagnation, weight pressure, sedentary"},
        "remedies": {
            "vata": {
                "name": "Garlic-Infused Sesame Oil Rub",
                "ingredients": [{"item": "sesame oil", "amount": "2 tbsp", "preparation": "warm"}, {"item": "garlic cloves", "amount": "3", "preparation": "crushed"}],
                "preparation": "Heat crushed garlic in sesame oil until brown. Strain and massage the warm oil firmly into the lower back. Cover with a warm blanket.",
                "dosage": "Once daily before sleep", "duration": "5 days", "expected_relief": "1-2 days"
            },
            "pitta": {
                "name": "Aloe Vera and Sandalwood Soothing Compress",
                "ingredients": [{"item": "aloe vera gel", "amount": "2 tbsp", "preparation": "fresh"}, {"item": "sandalwood powder", "amount": "1 tsp", "preparation": "mixed"}],
                "preparation": "Mix aloe gel with sandalwood. Apply a thick layer to the inflamed back area. Leave uncovered for 30 minutes, then rinse gently with cool water.",
                "dosage": "Apply once daily", "duration": "3 days", "expected_relief": "1 day"
            },
            "kapha": {
                "name": "Dry Ginger and Punarnava Poultice",
                "ingredients": [{"item": "dry ginger powder", "amount": "1 tbsp", "preparation": "powder"}, {"item": "punarnava powder", "amount": "1 tbsp", "preparation": "mixed with warm water"}],
                "preparation": "Make a thick, warm paste of the powders. Apply to the aching back, cover with a warm cloth, and leave for 20 minutes until it dries. Wash off with hot water.",
                "dosage": "Once daily", "duration": "4 days", "expected_relief": "2 days"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "", "drug_interactions": [], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if pain shoots down the leg, causes numbness, or follows trauma.", "source": "Traditional", "safety_tier": "home_safe"
    },
    {
        "id": "neck_pain", "symptom_id": "neck_pain", "symptom_display": "Neck Pain", "symptom_category": "pain",
        "dosha_cause": {"vata": "stiffness, cracking joints, cold draft", "pitta": "burning sensation, nerve irritation", "kapha": "heavy feeling, slow onset, poor posture"},
        "remedies": {
            "vata": {
                "name": "Warm Salt Poultice (Pottali)",
                "ingredients": [{"item": "rock salt", "amount": "1 cup", "preparation": "heated dry"}, {"item": "cotton cloth", "amount": "1", "preparation": "as pouch"}],
                "preparation": "Heat dry rock salt in a pan. Tie it securely in a cotton cloth to make a pouch. Gently press the warm pouch against the stiff neck muscles.",
                "dosage": "Use for 15 minutes, twice daily", "duration": "3 days", "expected_relief": "Immediate temporary relief"
            },
            "pitta": {
                "name": "Cool Coconut Oil and Brahmi Massage",
                "ingredients": [{"item": "coconut oil", "amount": "1 tbsp", "preparation": "room temp"}, {"item": "brahmi oil", "amount": "1 tsp", "preparation": "mixed"}],
                "preparation": "Mix the oils and apply with extremely gentle, cooling strokes down the neck and shoulders. Do not use deep friction.",
                "dosage": "Once daily in the evening", "duration": "3 days", "expected_relief": "1-2 days"
            },
            "kapha": {
                "name": "Camphor and Mustard Oil Vigorous Rub",
                "ingredients": [{"item": "mustard oil", "amount": "2 tbsp", "preparation": "warm"}, {"item": "camphor", "amount": "1 pinch", "preparation": "crushed"}],
                "preparation": "Warm the mustard oil and dissolve the camphor. Rub vigorously into the neck and upper back until the area feels hot.",
                "dosage": "Twice daily", "duration": "4 days", "expected_relief": "1 day"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if neck pain is accompanied by high fever or severe headache.", "source": "Traditional", "safety_tier": "home_safe"
    },
    {
        "id": "muscle_ache", "symptom_id": "muscle_ache", "symptom_display": "Muscle Ache", "symptom_category": "pain",
        "dosha_cause": {"vata": "cramps, twitching, overexertion", "pitta": "soreness, lactic acid buildup, heat", "kapha": "heaviness, lethargy, poor circulation"},
        "remedies": {
            "vata": {
                "name": "Epsom Salt Bath and Ashwagandha Tea",
                "ingredients": [{"item": "epsom salt", "amount": "1 cup", "preparation": "in warm bath"}, {"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "in warm water"}],
                "preparation": "Soak in a warm epsom salt bath for 20 minutes. Afterward, drink ashwagandha mixed in warm water to relax the nervous system.",
                "dosage": "Bath once, tea once", "duration": "1-2 days", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Cool Peppermint Compress and Coconut Water",
                "ingredients": [{"item": "peppermint oil", "amount": "2 drops", "preparation": "in cool water"}, {"item": "coconut water", "amount": "1 glass", "preparation": "fresh"}],
                "preparation": "Soak a cloth in cool water infused with peppermint oil. Apply to the sore muscle. Drink fresh coconut water to flush out acidic buildup.",
                "dosage": "Compress as needed, drink 1-2 glasses", "duration": "2 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Ginger and Turmeric Friction Paste",
                "ingredients": [{"item": "dry ginger powder", "amount": "1 tsp", "preparation": "mixed"}, {"item": "turmeric powder", "amount": "1 tsp", "preparation": "mixed with hot water"}],
                "preparation": "Create a hot paste. Apply directly to the aching muscle and rub vigorously to stimulate blood flow. Wash off after 15 minutes.",
                "dosage": "Apply once daily", "duration": "3 days", "expected_relief": "1 day"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if muscle ache persists for over a week without physical exertion.", "source": "Lad", "safety_tier": "home_safe"
    },
    {
        "id": "menstrual_cramps", "symptom_id": "menstrual_cramps", "symptom_display": "Menstrual Cramps", "symptom_category": "pain",
        "dosha_cause": {"vata": "sharp, spasming pain, scanty flow", "pitta": "burning pain, heavy flow, irritability", "kapha": "dull, heavy ache, bloating, slow onset"},
        "remedies": {
            "vata": {
                "name": "Ajwain and Hing Warm Decoction",
                "ingredients": [{"item": "ajwain (carom) seeds", "amount": "1/2 tsp", "preparation": "roasted"}, {"item": "hing (asafoetida)", "amount": "1 pinch", "preparation": "raw"}],
                "preparation": "Boil roasted ajwain and hing in 2 cups of water until reduced to half. Drink while comfortably hot.",
                "dosage": "Drink twice daily during menses", "duration": "3-5 days", "expected_relief": "Within hours"
            },
            "pitta": {
                "name": "Shatavari Milk and Coriander Tea",
                "ingredients": [{"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "in cool milk"}, {"item": "coriander seeds", "amount": "1 tsp", "preparation": "steeped"}],
                "preparation": "Mix shatavari in room-temperature milk. Sip slowly. For daytime, steep coriander seeds in water, strain and drink to reduce heat and heavy flow.",
                "dosage": "Shatavari once, coriander twice", "duration": "3-5 days", "expected_relief": "1 day"
            },
            "kapha": {
                "name": "Strong Ginger and Black Pepper Tea",
                "ingredients": [{"item": "fresh ginger", "amount": "1 inch", "preparation": "grated"}, {"item": "black pepper", "amount": "1 pinch", "preparation": "crushed"}],
                "preparation": "Boil ginger and pepper in water for 10 minutes. Strain and drink hot to clear congestion and stimulate flow.",
                "dosage": "Twice daily", "duration": "3 days", "expected_relief": "Same day"
            }
        },
        "universal_remedy": None, "contraindications": ["heavy_bleeding_for_vata_kapha"], "pregnancy_safe": False, "pregnancy_alternative": "Not applicable during pregnancy.", "drug_interactions": [], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if cramps are debilitating or accompanied by extremely heavy bleeding.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "tooth_pain", "symptom_id": "tooth_pain", "symptom_display": "Tooth Pain", "symptom_category": "pain",
        "dosha_cause": {"vata": "sensitivity to cold, shooting pain", "pitta": "inflammation, bleeding gums, heat sensitivity", "kapha": "dull ache, swelling, heavy feeling"},
        "remedies": {
            "vata": {
                "name": "Clove Oil and Sesame Swish",
                "ingredients": [{"item": "clove oil", "amount": "1 drop", "preparation": "on cotton swab"}, {"item": "sesame oil", "amount": "1 tbsp", "preparation": "warm"}],
                "preparation": "Apply clove oil directly to the painful tooth using a swab. Swish warm sesame oil in the mouth for 3 minutes and spit it out.",
                "dosage": "Swab as needed, swish once daily", "duration": "2 days", "expected_relief": "Immediate temporary relief"
            },
            "pitta": {
                "name": "Neem and Aloe Vera Gum Rub",
                "ingredients": [{"item": "neem powder", "amount": "1/4 tsp", "preparation": "paste"}, {"item": "aloe vera gel", "amount": "1/2 tsp", "preparation": "fresh"}],
                "preparation": "Mix neem and aloe vera into a paste. Gently rub onto the inflamed gums surrounding the painful tooth. Rinse after 5 minutes with cool water.",
                "dosage": "Twice daily", "duration": "3 days", "expected_relief": "1 day"
            },
            "kapha": {
                "name": "Turmeric and Rock Salt Scrub",
                "ingredients": [{"item": "turmeric powder", "amount": "1/2 tsp", "preparation": "dry"}, {"item": "rock salt", "amount": "1/4 tsp", "preparation": "finely ground"}],
                "preparation": "Mix turmeric and rock salt. Use your finger to scrub the painful tooth and surrounding gum vigorously. Rinse with warm water.",
                "dosage": "Twice daily", "duration": "2 days", "expected_relief": "1 day"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "", "drug_interactions": [], "severity_gate": "moderate", "consult_doctor_if": "Consult dentist immediately if there is a visible cavity, abscess, or swelling in the jaw.", "source": "Traditional", "safety_tier": "home_safe"
    },
    
    # ── DIGESTIVE (12) ───────────────────
    {
        "id": "bloating", "symptom_id": "bloating", "symptom_display": "Bloating", "symptom_category": "digestive",
        "dosha_cause": {"vata": "dry gas, constipation, irregular eating", "pitta": "acidic fermentation, sharp pain", "kapha": "sluggish digestion, water retention, heavy feeling"},
        "remedies": {
            "vata": {
                "name": "CCF Tea (Cumin, Coriander, Fennel) with Hing",
                "ingredients": [{"item": "cumin, coriander, fennel seeds", "amount": "1/2 tsp each", "preparation": "mixed"}, {"item": "hing (asafoetida)", "amount": "1 pinch", "preparation": "raw"}],
                "preparation": "Boil the seeds in 2 cups of water for 5 minutes. Add a pinch of hing. Strain and sip warm throughout the day.",
                "dosage": "2-3 cups daily", "duration": "3 days", "expected_relief": "Within hours"
            },
            "pitta": {
                "name": "Fennel and Mint Cooling Infusion",
                "ingredients": [{"item": "fennel seeds", "amount": "1 tsp", "preparation": "crushed"}, {"item": "mint leaves", "amount": "5-6", "preparation": "fresh"}],
                "preparation": "Steep fennel and mint in hot (not boiling) water for 10 minutes. Strain, let it cool slightly, and drink after meals.",
                "dosage": "After every meal", "duration": "3 days", "expected_relief": "1 day"
            },
            "kapha": {
                "name": "Ginger, Lemon, and Black Salt Shot",
                "ingredients": [{"item": "fresh ginger juice", "amount": "1 tsp", "preparation": "extracted"}, {"item": "lemon juice", "amount": "1 tsp", "preparation": "fresh"}, {"item": "black salt", "amount": "1 pinch", "preparation": "powder"}],
                "preparation": "Mix ginger juice, lemon juice, and black salt. Drink this 'shot' 15 minutes before meals to stoke the digestive fire (Agni).",
                "dosage": "Before lunch and dinner", "duration": "3-5 days", "expected_relief": "Same day"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if bloating is severe, persistent, or accompanied by severe abdominal pain.", "source": "Lad", "safety_tier": "home_safe"
    },
    {
        "id": "acid_reflux", "symptom_id": "acid_reflux", "symptom_display": "Acid Reflux", "symptom_category": "digestive",
        "dosha_cause": {"vata": "irregular eating times pushing acid up", "pitta": "excess stomach acid, spicy foods, anger", "kapha": "slow digestion causing food to sit and ferment"},
        "remedies": {
            "vata": {
                "name": "Warm Milk with Cardamom",
                "ingredients": [{"item": "milk (dairy or almond)", "amount": "1 cup", "preparation": "warm"}, {"item": "cardamom", "amount": "1 pinch", "preparation": "powder"}],
                "preparation": "Warm the milk gently and stir in cardamom. Drink slowly in the evening to settle downward energy (Apana Vayu).",
                "dosage": "Once daily before bed", "duration": "3 days", "expected_relief": "1 day"
            },
            "pitta": {
                "name": "Amalaki and Aloe Vera Coolant",
                "ingredients": [{"item": "amalaki powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "aloe vera juice", "amount": "2 tbsp", "preparation": "food grade"}],
                "preparation": "Mix amalaki powder and aloe vera juice into half a glass of room temperature water. Drink first thing in the morning on an empty stomach.",
                "dosage": "Once daily in morning", "duration": "5-7 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Clove and Coriander Seed Tea",
                "ingredients": [{"item": "clove", "amount": "1 piece", "preparation": "whole"}, {"item": "coriander seeds", "amount": "1 tsp", "preparation": "crushed"}],
                "preparation": "Boil clove and coriander in 1 cup of water for 5 minutes. Strain and drink warm after meals to speed up sluggish digestion.",
                "dosage": "Twice daily after meals", "duration": "3 days", "expected_relief": "1 day"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Use fennel tea and small amounts of cold milk.", "drug_interactions": ["diabetes_medication"], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if acid reflux causes difficulty swallowing or severe chest pain.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "constipation", "symptom_id": "constipation", "symptom_display": "Constipation", "symptom_category": "digestive",
        "dosha_cause": {"vata": "dryness in colon, hard stool, cold", "pitta": "liver heat drying out stool", "kapha": "sluggish bowel movement, mucus"},
        "remedies": {
            "vata": {
                "name": "Warm Ghee in Hot Water",
                "ingredients": [{"item": "ghee", "amount": "1 tbsp", "preparation": "melted"}, {"item": "hot water", "amount": "1 cup", "preparation": "hot"}],
                "preparation": "Stir melted ghee into a cup of hot water. Drink immediately before going to bed to lubricate the colon.",
                "dosage": "Once daily at night", "duration": "3-5 days", "expected_relief": "Next morning"
            },
            "pitta": {
                "name": "Triphala Powder with Room Temp Water",
                "ingredients": [{"item": "triphala powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "water", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Mix triphala powder in water. Let it sit for 10 minutes. Drink before bed to gently cleanse and cool the digestive tract.",
                "dosage": "Once daily at night", "duration": "3-5 days", "expected_relief": "1-2 days"
            },
            "kapha": {
                "name": "Triphala with Honey and Ginger",
                "ingredients": [{"item": "triphala powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "ginger juice", "amount": "1/2 tsp", "preparation": "fresh"}],
                "preparation": "Mix triphala, honey, and ginger juice into a thick paste. Consume followed by a sip of warm water before bed.",
                "dosage": "Once daily at night", "duration": "3 days", "expected_relief": "Next morning"
            }
        },
        "universal_remedy": None, "contraindications": ["diarrhea"], "pregnancy_safe": False, "pregnancy_alternative": "Soak 5 raisins in water overnight and eat them in the morning.", "drug_interactions": ["blood_thinners", "diabetes_medication"], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if constipated for more than 4 days or if there is severe abdominal pain.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    
    # ── ENERGY AND SLEEP (8) ─────────────
    {
        "id": "insomnia", "symptom_id": "insomnia", "symptom_display": "Insomnia", "symptom_category": "energy",
        "dosha_cause": {"vata": "racing thoughts, anxiety, waking between 2-4 AM", "pitta": "intense dreams, waking hot, difficulty falling asleep", "kapha": "excessive sleepiness but poor quality, lethargy"},
        "remedies": {
            "vata": {
                "name": "Nutmeg Milk and Foot Massage",
                "ingredients": [{"item": "nutmeg", "amount": "1 pinch", "preparation": "grated"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "sesame oil", "amount": "1 tsp", "preparation": "for feet"}],
                "preparation": "Add a pinch of grated nutmeg to warm milk and drink 30 mins before bed. Vigorously massage soles of feet with warm sesame oil.",
                "dosage": "Once daily at night", "duration": "Ongoing", "expected_relief": "1-3 days"
            },
            "pitta": {
                "name": "Brahmi Tea and Rose Oil",
                "ingredients": [{"item": "brahmi powder", "amount": "1/2 tsp", "preparation": "steeped"}, {"item": "rose essential oil", "amount": "1 drop", "preparation": "diluted"}],
                "preparation": "Steep brahmi in hot water for 5 mins, cool slightly and drink. Apply diluted rose oil to temples and third eye.",
                "dosage": "Once daily at night", "duration": "Ongoing", "expected_relief": "3-5 days"
            },
            "kapha": {
                "name": "Early Light Dinner and Dry Brushing",
                "ingredients": [{"item": "dry brush or raw silk glove", "amount": "1", "preparation": "dry"}, {"item": "triphala", "amount": "1/2 tsp", "preparation": "with warm water"}],
                "preparation": "Eat dinner before sunset. Before bed, rigorously dry brush the body to prevent stagnation. Take triphala with warm water.",
                "dosage": "Daily routine", "duration": "Ongoing", "expected_relief": "1 week"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Warm milk with a tiny pinch of cardamom (skip nutmeg).", "drug_interactions": ["sedatives"], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if insomnia persists for weeks and heavily impacts daily function.", "source": "Lad", "safety_tier": "home_safe"
    },
    {
        "id": "fatigue", "symptom_id": "fatigue", "symptom_display": "Fatigue", "symptom_category": "energy",
        "dosha_cause": {"vata": "burnout, lack of nourishment, erratic routine", "pitta": "adrenal exhaustion from overworking, intense heat", "kapha": "stagnation, oversleeping, heavy digestion"},
        "remedies": {
            "vata": {
                "name": "Ashwagandha and Dates Energy Tonic",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "dates", "amount": "3", "preparation": "chopped"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warmed"}],
                "preparation": "Blend or simmer ashwagandha and dates in warm milk. Drink mid-morning or afternoon for grounded energy.",
                "dosage": "Once daily", "duration": "14 days", "expected_relief": "3-5 days"
            },
            "pitta": {
                "name": "Shatavari and Coconut Water Refresher",
                "ingredients": [{"item": "shatavari powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "coconut water", "amount": "1 glass", "preparation": "fresh"}],
                "preparation": "Stir shatavari into fresh coconut water. Drink in the afternoon to replenish depleted cooling energy (Ojas) without heating the body.",
                "dosage": "Once daily", "duration": "14 days", "expected_relief": "3 days"
            },
            "kapha": {
                "name": "Ginger, Honey, and Black Pepper Stimulant",
                "ingredients": [{"item": "ginger juice", "amount": "1 tsp", "preparation": "fresh"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "black pepper", "amount": "1 pinch", "preparation": "crushed"}],
                "preparation": "Mix all ingredients into a paste. Take directly on the tongue first thing in the morning to burn off lethargy (Ama).",
                "dosage": "Once daily in morning", "duration": "7 days", "expected_relief": "1 day"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Eat 5 soaked almonds and 2 dates daily.", "drug_interactions": ["thyroid_medication", "immunosuppressants"], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if fatigue is severe, chronic, or accompanied by unexplained weight loss.", "source": "Classical", "safety_tier": "use_with_caution"
    },

    # ── SKIN (8) ─────────────────────────
    {
        "id": "acne", "symptom_id": "acne", "symptom_display": "Acne & Breakouts", "symptom_category": "skin",
        "dosha_cause": {"vata": "dry, blackheads, rough skin", "pitta": "red, inflamed, painful, pus-filled", "kapha": "deep cystic, oily, large, slow to heal"},
        "remedies": {
            "vata": {
                "name": "Warm Sesame Oil and Chickpea Flour Wash",
                "ingredients": [{"item": "sesame oil", "amount": "1/2 tsp", "preparation": "warm"}, {"item": "chickpea flour (besan)", "amount": "1 tbsp", "preparation": "dry"}],
                "preparation": "Massage face gently with warm sesame oil for 2 mins. Wash off using chickpea flour mixed with water as a gentle non-drying soap substitute.",
                "dosage": "Once daily", "duration": "7 days", "expected_relief": "3-4 days"
            },
            "pitta": {
                "name": "Neem and Sandalwood Cooling Mask",
                "ingredients": [{"item": "neem powder", "amount": "1/2 tsp", "preparation": "dry"}, {"item": "sandalwood powder", "amount": "1 tsp", "preparation": "dry"}, {"item": "rose water", "amount": "to mix", "preparation": "cool"}],
                "preparation": "Mix neem and sandalwood with rose water to make a paste. Apply to acne. Leave until dry (15 mins), wash with cool water.",
                "dosage": "Apply every alternate day", "duration": "2 weeks", "expected_relief": "3 days"
            },
            "kapha": {
                "name": "Turmeric, Honey, and Lemon Spot Treatment",
                "ingredients": [{"item": "turmeric", "amount": "1/4 tsp", "preparation": "powder"}, {"item": "honey", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "lemon juice", "amount": "2 drops", "preparation": "fresh"}],
                "preparation": "Mix into a thick paste. Apply ONLY as a spot treatment directly on deep cystic acne. Leave for 20 mins, wash with warm water.",
                "dosage": "Once daily on spots", "duration": "5 days", "expected_relief": "2-3 days"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult a dermatologist if acne is severely cystic or leaves deep scars.", "source": "Lad", "safety_tier": "home_safe"
    },

    # ── MENTAL AND EMOTIONAL (7) ─────────
    {
        "id": "anxiety", "symptom_id": "anxiety", "symptom_display": "Anxiety", "symptom_category": "mental",
        "dosha_cause": {"vata": "overthinking, fear, ungroundedness", "pitta": "performance anxiety, frustration, control", "kapha": "attachment anxiety, emotional heaviness"},
        "remedies": {
            "vata": {
                "name": "Ashwagandha Milk and Warm Oil Crown Application",
                "ingredients": [{"item": "ashwagandha", "amount": "1/2 tsp", "preparation": "in warm milk"}, {"item": "warm sesame oil", "amount": "1 tsp", "preparation": "warmed"}],
                "preparation": "Drink ashwagandha milk. Rub warm sesame oil generously on the crown of the head and soles of feet to instantly ground Vata.",
                "dosage": "Once daily in evening", "duration": "14 days", "expected_relief": "1 day"
            },
            "pitta": {
                "name": "Brahmi Tea and Cooling Breath (Sheetali)",
                "ingredients": [{"item": "brahmi powder", "amount": "1/2 tsp", "preparation": "steeped"}, {"item": "coriander water", "amount": "1 cup", "preparation": "cool"}],
                "preparation": "Drink brahmi steeped in hot water (let it cool). Practice Sheetali pranayama (rolling tongue, inhaling cool air) for 5 minutes.",
                "dosage": "Once daily", "duration": "Ongoing", "expected_relief": "Immediate for breathwork"
            },
            "kapha": {
                "name": "Ginger Tea and Vigorous Walking",
                "ingredients": [{"item": "ginger tea", "amount": "1 cup", "preparation": "hot"}, {"item": "movement", "amount": "30 mins", "preparation": "brisk"}],
                "preparation": "Drink strong hot ginger tea to break stagnation. Force yourself to take a 30-minute brisk walk; physical movement breaks Kapha mental loops.",
                "dosage": "Daily morning", "duration": "Ongoing", "expected_relief": "1-2 days"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Practice deep abdominal breathing and gentle foot massages. Avoid Ashwagandha.", "drug_interactions": ["sedatives", "thyroid_medication"], "severity_gate": "moderate", "consult_doctor_if": "Consult a professional if anxiety causes panic attacks or severely impacts life.", "source": "Classical", "safety_tier": "use_with_caution"
    },

    # ── RESPIRATORY (8) ──────────────────
    {
        "id": "cough_wet", "symptom_id": "cough_wet", "symptom_display": "Wet/Mucus Cough", "symptom_category": "respiratory",
        "dosha_cause": {"vata": "drying mucus causing rattling", "pitta": "yellow/green mucus with heat", "kapha": "thick, white, sticky, abundant mucus"},
        "remedies": {
            "vata": {
                "name": "Warm Milk with Turmeric and Ghee",
                "ingredients": [{"item": "milk", "amount": "1 cup", "preparation": "warm"}, {"item": "turmeric", "amount": "1/2 tsp", "preparation": "powder"}, {"item": "ghee", "amount": "1/2 tsp", "preparation": "melted"}],
                "preparation": "Simmer milk, turmeric, and ghee. Drink warm before bed to soothe the dry rattling in the chest.",
                "dosage": "Once daily at night", "duration": "3-5 days", "expected_relief": "2 days"
            },
            "pitta": {
                "name": "Sitopaladi Churna with Honey",
                "ingredients": [{"item": "sitopaladi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix sitopaladi and honey into a paste. Lick it slowly off a spoon. This clears hot, infected mucus safely.",
                "dosage": "3 times daily", "duration": "5 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Trikatu and Honey Strong Paste",
                "ingredients": [{"item": "trikatu powder (ginger, black pepper, pippali)", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix trikatu and honey. Consume directly. Do NOT drink milk or eat heavy foods. This burns away thick, stubborn Kapha mucus.",
                "dosage": "Twice daily after food", "duration": "4 days", "expected_relief": "1-2 days"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Use only warm water with a pinch of turmeric. Avoid Trikatu.", "drug_interactions": [], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if mucus is bloody, cough lasts > 2 weeks, or there is breathing difficulty.", "source": "Classical", "safety_tier": "use_with_caution"
    },

    # ── IMMUNITY AND GENERAL (7) ─────────
    {
        "id": "low_immunity", "symptom_id": "low_immunity", "symptom_display": "Low Immunity (Ojas)", "symptom_category": "immunity",
        "dosha_cause": {"vata": "depletion, weight loss, stress", "pitta": "burnout, chronic inflammation", "kapha": "sluggishness, poor metabolism preventing nutrient absorption"},
        "remedies": {
            "vata": {
                "name": "Ojas Building Almond and Ashwagandha Milk",
                "ingredients": [{"item": "almonds", "amount": "10", "preparation": "soaked and peeled"}, {"item": "ashwagandha", "amount": "1/2 tsp", "preparation": "powder"}, {"item": "milk", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Blend soaked almonds with warm milk and ashwagandha. Simmer for 3 mins. Drink in the morning to build deep tissue strength.",
                "dosage": "Once daily", "duration": "30 days", "expected_relief": "2 weeks"
            },
            "pitta": {
                "name": "Amalaki Rasayana (Chyawanprash)",
                "ingredients": [{"item": "chyawanprash (amalaki jam)", "amount": "1 tsp", "preparation": "ready-made"}],
                "preparation": "Take 1 tsp of authentic Chyawanprash (rich in Vitamin C and Pitta-cooling herbs) followed by a sip of room temp water.",
                "dosage": "Once daily in morning", "duration": "30 days", "expected_relief": "2 weeks"
            },
            "kapha": {
                "name": "Tulsi and Guduchi Decoction",
                "ingredients": [{"item": "tulsi leaves", "amount": "10", "preparation": "fresh"}, {"item": "guduchi powder", "amount": "1/2 tsp", "preparation": "raw"}],
                "preparation": "Boil tulsi and guduchi in 2 cups water until reduced to 1 cup. Drink warm. This builds immunity while scraping away heavy Kapha toxins.",
                "dosage": "Once daily", "duration": "21 days", "expected_relief": "1-2 weeks"
            }
        },
        "universal_remedy": None, "contraindications": ["active_infection"], "pregnancy_safe": False, "pregnancy_alternative": "Eat 5 soaked almonds and 1 tsp of mild Chyawanprash.", "drug_interactions": ["immunosuppressants"], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if you are constantly falling severely ill.", "source": "Classical", "safety_tier": "home_safe"
    },

    # ── DIGESTIVE continued (9) ──────────────────────────────────────────────
    {
        "id": "nausea", "symptom_id": "nausea", "symptom_display": "Nausea / Vomiting Sensation", "symptom_category": "digestive",
        "dosha_cause": {"vata": "motion sickness, fear, dry nausea with no relief", "pitta": "bile reflux, hot acid surge, food poisoning onset", "kapha": "heavy food, mucus buildup, sticky nausea worse in morning"},
        "remedies": {
            "vata": {
                "name": "Warm Ginger and Hing Decoction",
                "ingredients": [{"item": "fresh ginger", "amount": "1/2 inch", "preparation": "grated"}, {"item": "hing (asafoetida)", "amount": "1 small pinch", "preparation": "raw"}, {"item": "rock salt", "amount": "1 pinch", "preparation": "raw"}],
                "preparation": "Boil grated ginger in 1 cup water for 5 minutes. Add hing and rock salt. Sip very slowly while warm. Do not drink cold water after.",
                "dosage": "Sip 1/4 cup every 30 minutes", "duration": "1 day", "expected_relief": "Within 30 minutes"
            },
            "pitta": {
                "name": "Coriander and Mint Cooling Infusion",
                "ingredients": [{"item": "coriander seeds", "amount": "1 tsp", "preparation": "crushed"}, {"item": "mint leaves", "amount": "8", "preparation": "fresh"}, {"item": "mishri (rock sugar)", "amount": "1/2 tsp", "preparation": "raw"}],
                "preparation": "Steep coriander and mint in 1 cup of hot water. Cool to room temperature. Add mishri and sip slowly. Avoid spicy or acidic foods immediately.",
                "dosage": "1 cup every hour as needed", "duration": "1 day", "expected_relief": "Within 20 minutes"
            },
            "kapha": {
                "name": "Dry Ginger and Lemon Shot",
                "ingredients": [{"item": "dry ginger (sonth) powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "lemon juice", "amount": "1 tsp", "preparation": "fresh"}, {"item": "black salt", "amount": "1 pinch", "preparation": "raw"}],
                "preparation": "Mix all in 2 tbsp of warm water. Take in one shot. Wait 15 minutes before eating. Helps burn away sticky Kapha causing morning nausea.",
                "dosage": "Once, then again after 1 hour if needed", "duration": "1 day", "expected_relief": "15–30 minutes"
            }
        },
        "universal_remedy": None, "contraindications": ["severe_vomiting_with_blood"], "pregnancy_safe": False, "pregnancy_alternative": "Ginger tea with mishri only — avoid hing and strong spices.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if vomiting is projectile, contains blood, or persists beyond 24 hours.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "diarrhea", "symptom_id": "diarrhea", "symptom_display": "Diarrhea (Atisara)", "symptom_category": "digestive",
        "dosha_cause": {"vata": "watery, frequent, painful stools with gas and griping", "pitta": "burning, yellow-green stools, fever, thirst, infection", "kapha": "white mucousy stools, slow onset, heaviness, nausea"},
        "remedies": {
            "vata": {
                "name": "Bael Fruit (Aegle marmelos) Pulp with Nutmeg",
                "ingredients": [{"item": "ripe bael fruit pulp", "amount": "2 tbsp", "preparation": "scooped out"}, {"item": "nutmeg powder", "amount": "1 small pinch", "preparation": "freshly grated"}, {"item": "mishri", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix bael pulp with a tiny pinch of nutmeg and mishri. Eat slowly. Bael is the most effective classical Grahi (absorbent) for Vata diarrhea. Follow with rice water.",
                "dosage": "Twice daily, after each bout", "duration": "2 days", "expected_relief": "2–4 hours"
            },
            "pitta": {
                "name": "Pomegranate Juice with Coriander",
                "ingredients": [{"item": "pomegranate juice", "amount": "1/2 cup", "preparation": "fresh"}, {"item": "coriander powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "mishri", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix fresh pomegranate juice with coriander and mishri. Drink at room temperature (not cold). Pomegranate (Dadima) is the classic Pitta diarrhea remedy in Charaka Samhita, Chikitsa Sthana.",
                "dosage": "3 times daily", "duration": "2 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Trikatu with Honey and Hing",
                "ingredients": [{"item": "dry ginger powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "black pepper", "amount": "2 pinches", "preparation": "ground"}, {"item": "hing", "amount": "1 small pinch", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix all into a paste with honey. Consume directly followed by warm water. Burns away the mucus (Kapha) causing thick, sticky stools.",
                "dosage": "Twice daily before meals", "duration": "2 days", "expected_relief": "Same day"
            }
        },
        "universal_remedy": None, "contraindications": ["dysentery", "dehydration_severe"], "pregnancy_safe": True, "pregnancy_alternative": "Bael pulp with mishri only. Stay on ORS and rice water.", "drug_interactions": [], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if stools contain blood, diarrhea exceeds 6 times per day, or signs of dehydration appear.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "loss_of_appetite", "symptom_id": "loss_of_appetite", "symptom_display": "Loss of Appetite (Arochaka)", "symptom_category": "digestive",
        "dosha_cause": {"vata": "anxiety, irregular meals, nervous system suppression of hunger", "pitta": "excess acid, heat suppressing appetite, bitter taste in mouth", "kapha": "Ama accumulation, heavy undigested food blocking new hunger signals"},
        "remedies": {
            "vata": {
                "name": "Hingvastak Churna with Ghee",
                "ingredients": [{"item": "hingvastak churna", "amount": "1/4 tsp", "preparation": "ready-made"}, {"item": "ghee", "amount": "1/2 tsp", "preparation": "warm"}],
                "preparation": "Mix hingvastak churna with warm ghee. Take 15–20 minutes before lunch. This kindles the digestive fire (Agni Deepana) and removes Vata from the gut.",
                "dosage": "Before main meals", "duration": "5 days", "expected_relief": "2 days"
            },
            "pitta": {
                "name": "Amalaki and Mishri Pre-Meal Tonic",
                "ingredients": [{"item": "amalaki (amla) powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}, {"item": "water", "amount": "1/2 cup", "preparation": "room temp"}],
                "preparation": "Mix amla and mishri in water. Drink 20 minutes before meals. Amla pacifies excess Pitta heat that suppresses appetite without further heating the gut.",
                "dosage": "Before lunch and dinner", "duration": "4 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Trikatu and Lemon Appetiser",
                "ingredients": [{"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "ready-made or homemade"}, {"item": "lemon juice", "amount": "1/2 tsp", "preparation": "fresh"}, {"item": "rock salt", "amount": "1 pinch", "preparation": "raw"}],
                "preparation": "Mix trikatu, lemon, and rock salt. Take directly on the tongue 15 minutes before meals. The pungent-sour-salty combination is the strongest classical Deepana (appetite stimulant).",
                "dosage": "Before lunch and dinner", "duration": "4 days", "expected_relief": "Same day"
            }
        },
        "universal_remedy": None, "contraindications": ["hyperacidity", "ulcer"], "pregnancy_safe": False, "pregnancy_alternative": "Saunf (fennel) water before meals. Ginger slice with rock salt 15 min before eating.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if appetite loss persists beyond 1 week or is accompanied by weight loss.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "hemorrhoids", "symptom_id": "hemorrhoids", "symptom_display": "Piles / Hemorrhoids (Arsha)", "symptom_category": "digestive",
        "dosha_cause": {"vata": "dry, hard piles with severe pain, no bleeding, constipation", "pitta": "bleeding piles, burning sensation, inflammation, soft mass", "kapha": "large, mucousy, non-bleeding piles, heavy feeling in rectum"},
        "remedies": {
            "vata": {
                "name": "Triphala Sitz Bath and Castor Oil",
                "ingredients": [{"item": "triphala powder", "amount": "2 tsp", "preparation": "boiled in 1L water"}, {"item": "castor oil", "amount": "1 tbsp", "preparation": "warm"}, {"item": "turmeric", "amount": "1/2 tsp", "preparation": "added to bath"}],
                "preparation": "Boil triphala and turmeric in 1L water, cool to warm bath temperature. Sit in the bath for 15 minutes. Apply warm castor oil directly to the piles afterward.",
                "dosage": "Sitz bath once daily, castor oil twice daily", "duration": "7 days", "expected_relief": "3 days"
            },
            "pitta": {
                "name": "Yashtimadhu Powder with Ghee and Milk",
                "ingredients": [{"item": "yashtimadhu (licorice) powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "ghee", "amount": "1 tsp", "preparation": "melted"}, {"item": "milk", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Mix yashtimadhu and ghee into warm milk. Drink at night. Licorice cools Pitta, stops bleeding, and heals rectal mucosa.",
                "dosage": "Once daily at night", "duration": "7 days", "expected_relief": "3 days"
            },
            "kapha": {
                "name": "Haritaki with Hot Water",
                "ingredients": [{"item": "haritaki powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "hot water", "amount": "1 cup", "preparation": "hot"}, {"item": "rock salt", "amount": "1 pinch", "preparation": "raw"}],
                "preparation": "Mix haritaki in hot water with rock salt. Drink at bedtime. Haritaki is the pre-eminent classical herb for Kapha-type Arsha — it clears mucus, reduces mass, and regularises bowels.",
                "dosage": "Once daily at night", "duration": "10 days", "expected_relief": "4 days"
            }
        },
        "universal_remedy": None, "contraindications": ["heavy_bleeding", "thrombosed_piles"], "pregnancy_safe": False, "pregnancy_alternative": "Warm sesame oil applied externally. Avoid hing and spicy foods.", "drug_interactions": ["blood_thinners"], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if bleeding is heavy, piles are prolapsed and cannot be pushed back, or pain is severe.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "hyperacidity", "symptom_id": "hyperacidity", "symptom_display": "Hyperacidity (Amlapitta)", "symptom_category": "digestive",
        "dosha_cause": {"vata": "irregular meal timing causing acid spikes", "pitta": "excess Pitta in the stomach, sharp burning, acid taste in mouth", "kapha": "fermentation of undigested food, slow emptying, sour belching"},
        "remedies": {
            "vata": {
                "name": "Warm Jeera Water with Fennel",
                "ingredients": [{"item": "cumin seeds", "amount": "1/2 tsp", "preparation": "roasted"}, {"item": "fennel seeds", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "mishri", "amount": "1/2 tsp", "preparation": "raw"}],
                "preparation": "Boil both seeds in 1 cup water. Cool slightly. Add mishri. Sip between meals at regular intervals. Regularises Vata and prevents acid spikes from meal gaps.",
                "dosage": "2 cups daily between meals", "duration": "5 days", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Shatavari Powder in Cold Milk",
                "ingredients": [{"item": "shatavari powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "milk", "amount": "1 cup", "preparation": "cold or room temp"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Stir shatavari into room-temperature milk with mishri. Drink 30 minutes before meals. Shatavari with milk is the classic Pitta-Amlapitta treatment in Sharangadhara Samhita.",
                "dosage": "Twice daily before meals", "duration": "7 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Triphala and Ginger Before-Bed Cleanse",
                "ingredients": [{"item": "triphala churna", "amount": "1 tsp", "preparation": "raw"}, {"item": "ginger powder (sonth)", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "hot water", "amount": "1 cup", "preparation": "hot"}],
                "preparation": "Mix triphala and ginger in hot water. Drink 1 hour before sleeping on a light stomach. Clears the Kapha-fermentation causing sour, sluggish hyperacidity.",
                "dosage": "Once at night", "duration": "7 days", "expected_relief": "2 days"
            }
        },
        "universal_remedy": None, "contraindications": ["active_ulcer"], "pregnancy_safe": True, "pregnancy_alternative": "Shatavari with cold milk only. Avoid ginger-heavy preparations.", "drug_interactions": ["nsaids"], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor if there is burning chest pain, difficulty swallowing, or vomiting blood.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "liver_support", "symptom_id": "liver_support", "symptom_display": "Liver Support / Fatty Liver", "symptom_category": "digestive",
        "dosha_cause": {"vata": "poor fat metabolism, dry liver, variable digestion", "pitta": "excess heat and toxins in liver, jaundice tendency, inflammation", "kapha": "fat accumulation, sluggish bile, heaviness after meals"},
        "remedies": {
            "vata": {
                "name": "Punarnava and Castor Oil Decoction",
                "ingredients": [{"item": "punarnava powder", "amount": "1/2 tsp", "preparation": "boiled"}, {"item": "warm water", "amount": "1 cup", "preparation": "boiled"}, {"item": "castor oil", "amount": "1/2 tsp", "preparation": "added after boiling"}],
                "preparation": "Boil punarnava in water, cool to warm. Add castor oil and stir well. Drink in the morning. Punarnava (Boerhavia diffusa) rejuvenates liver tissue and reduces Vata-driven sluggishness.",
                "dosage": "Once daily in morning", "duration": "21 days", "expected_relief": "1 week"
            },
            "pitta": {
                "name": "Kutki and Neem Leaves Bitter Tonic",
                "ingredients": [{"item": "kutki (Picrorhiza kurroa) powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "fresh neem leaves", "amount": "5", "preparation": "chewed or juiced"}, {"item": "warm water", "amount": "1/2 cup", "preparation": "warm"}],
                "preparation": "Take kutki powder with warm water in the morning. Separately chew 5 fresh neem leaves or drink 1 tsp neem juice. Kutki is the foremost classical liver herb — deeply bitter, clears Pitta from Yakrit (liver).",
                "dosage": "Once daily in morning on empty stomach", "duration": "21 days", "expected_relief": "1 week"
            },
            "kapha": {
                "name": "Triphala and Haridra Morning Flush",
                "ingredients": [{"item": "triphala churna", "amount": "1 tsp", "preparation": "raw"}, {"item": "turmeric powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Mix triphala and turmeric in warm water. Drink first thing in the morning. This combination scrapes fat (Lekhana) from the liver and kindles bile flow.",
                "dosage": "Once daily on empty stomach", "duration": "30 days", "expected_relief": "2 weeks"
            }
        },
        "universal_remedy": None, "contraindications": ["jaundice_with_fever", "pregnancy"], "pregnancy_safe": False, "pregnancy_alternative": "Avoid bitter herbs. Use warm lemon water in the morning.", "drug_interactions": ["immunosuppressants", "diabetes_medication"], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if jaundice (yellow skin/eyes), dark urine, or severe fatigue appear.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "intestinal_worms", "symptom_id": "intestinal_worms", "symptom_display": "Intestinal Worms (Krimi Roga)", "symptom_category": "digestive",
        "dosha_cause": {"vata": "moving, colicky pain, emaciation", "pitta": "burning in anus, thin body, fever tendency", "kapha": "mucousy stools, itching in rectum, pot belly in children"},
        "remedies": {
            "vata": {
                "name": "Vidanga Powder with Warm Castor Oil",
                "ingredients": [{"item": "vidanga (Embelia ribes) powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1/2 cup", "preparation": "warm"}, {"item": "castor oil", "amount": "1 tsp", "preparation": "added after"}],
                "preparation": "Take vidanga powder with warm water. After 1 hour, take castor oil to flush the dead worms out. Vidanga is the primary classical Krimighna (anti-parasitic) herb.",
                "dosage": "Vidanga once in morning for 3 days, castor oil on day 3", "duration": "3 days", "expected_relief": "2 days"
            },
            "pitta": {
                "name": "Neem Leaf Decoction with Haridra",
                "ingredients": [{"item": "neem leaves", "amount": "10", "preparation": "fresh"}, {"item": "turmeric powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1 cup", "preparation": "boiled with neem"}],
                "preparation": "Boil neem leaves in 1 cup water until reduced to half. Add turmeric. Drink on empty stomach. Bitter-pungent combination kills worms and reduces the associated inflammation.",
                "dosage": "Once daily for 5 days in morning", "duration": "5 days", "expected_relief": "3 days"
            },
            "kapha": {
                "name": "Vacha and Hing Anti-Worm Paste",
                "ingredients": [{"item": "vacha (Acorus calamus) powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "hing", "amount": "1 pinch", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix vacha, hing, and honey into a paste. Take in the morning. This pungent combination breaks the mucus shield protecting Kapha-type worms.",
                "dosage": "Once daily in morning", "duration": "5 days", "expected_relief": "3 days"
            }
        },
        "universal_remedy": None, "contraindications": ["active_fever", "inflammatory_bowel_disease"], "pregnancy_safe": False, "pregnancy_alternative": "Consult a physician for safe anti-parasitic treatment during pregnancy.", "drug_interactions": [], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor for children, if worms are visible in stool, or if symptoms are severe.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "morning_sickness_mild", "symptom_id": "morning_sickness_mild", "symptom_display": "Morning Digestive Sluggishness", "symptom_category": "digestive",
        "dosha_cause": {"vata": "morning churning, empty-stomach anxiety", "pitta": "bile surge on waking, bitter-sour taste, heat", "kapha": "heaviness, coated tongue, sluggishness on waking"},
        "remedies": {
            "vata": {
                "name": "Warm Water with Ginger and Lime",
                "ingredients": [{"item": "warm water", "amount": "1 glass", "preparation": "warm (not hot)"}, {"item": "fresh ginger", "amount": "3 thin slices", "preparation": "raw"}, {"item": "lime juice", "amount": "1/2 tsp", "preparation": "fresh"}],
                "preparation": "Steep ginger slices in warm water for 3 minutes. Add lime juice and sip slowly upon waking before any other food or drink.",
                "dosage": "Every morning on waking", "duration": "Ongoing", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Coriander Seed Water with Mishri",
                "ingredients": [{"item": "coriander seeds", "amount": "1 tsp", "preparation": "soaked overnight"}, {"item": "mishri", "amount": "1/2 tsp", "preparation": "dissolved"}, {"item": "cool water", "amount": "1 glass", "preparation": "from soaking"}],
                "preparation": "Soak coriander seeds in water overnight. Strain in the morning. Dissolve mishri in the infused water. Drink first thing — cools Pitta bile surge before it builds.",
                "dosage": "Every morning", "duration": "Ongoing", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Dry Ginger, Honey, and Tulsi Morning Ritual",
                "ingredients": [{"item": "dry ginger (sonth) powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "tulsi leaves", "amount": "5", "preparation": "chewed"}],
                "preparation": "Take sonth and honey on the tongue first thing. Follow by chewing 5 fresh tulsi leaves. Cuts through morning Kapha and activates Agni for the day.",
                "dosage": "Every morning", "duration": "Ongoing", "expected_relief": "Same day"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Warm water with a tiny pinch of cardamom. Saunf tea.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if accompanied by severe nausea, vomiting, or weight loss.", "source": "Traditional", "safety_tier": "home_safe"
    },
    {
        "id": "uti_burning_urination", "symptom_id": "uti_burning_urination", "symptom_display": "Burning Urination / UTI Symptoms (Mutrakriccha)", "symptom_category": "digestive",
        "dosha_cause": {"vata": "scanty, painful, dry urination", "pitta": "burning, hot, yellow or orange urine, heat in pelvis", "kapha": "cloudy, mucousy urine, slow flow, heaviness in lower abdomen"},
        "remedies": {
            "vata": {
                "name": "Gokshura and Warm Water Decoction",
                "ingredients": [{"item": "gokshura (Tribulus terrestris) powder", "amount": "1 tsp", "preparation": "boiled"}, {"item": "warm water", "amount": "2 cups", "preparation": "boiled, reduced to 1 cup"}],
                "preparation": "Boil gokshura in 2 cups of water until reduced to 1 cup. Cool to warm. Drink slowly. Gokshura is the foremost classical Mutravirechana (urinary diuretic) for Vata-type UTI.",
                "dosage": "Twice daily", "duration": "5 days", "expected_relief": "2 days"
            },
            "pitta": {
                "name": "Coriander and Coconut Water Cooler",
                "ingredients": [{"item": "coriander seeds", "amount": "2 tsp", "preparation": "soaked in water overnight"}, {"item": "coconut water", "amount": "1 cup", "preparation": "fresh"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Strain the overnight coriander-seed water. Mix with coconut water and mishri. Drink cool (not iced). This cooling combination quenches the Pitta fire causing burning urination.",
                "dosage": "3 times daily", "duration": "5 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Punarnava and Dry Ginger Decoction",
                "ingredients": [{"item": "punarnava powder", "amount": "1 tsp", "preparation": "boiled"}, {"item": "dry ginger powder", "amount": "1/4 tsp", "preparation": "added after"}, {"item": "warm water", "amount": "1 cup", "preparation": "boiled"}],
                "preparation": "Boil punarnava in water. Cool to warm, add ginger. Drink. Punarnava drains Kapha from the urinary tract and sonth activates sluggish flow.",
                "dosage": "Twice daily", "duration": "5 days", "expected_relief": "2 days"
            }
        },
        "universal_remedy": None, "contraindications": ["kidney_stones", "severe_infection_with_fever"], "pregnancy_safe": False, "pregnancy_alternative": "Coconut water and barley water only. Consult a physician.", "drug_interactions": ["diuretics", "antihypertensives"], "severity_gate": "moderate", "consult_doctor_if": "Consult doctor immediately if there is fever, back pain, blood in urine, or symptoms do not improve in 2 days.", "source": "Classical", "safety_tier": "use_with_caution"
    },

    # ── RESPIRATORY continued (7) ────────────────────────────────────────────
    {
        "id": "dry_cough", "symptom_id": "dry_cough", "symptom_display": "Dry Cough (Shushka Kasa)", "symptom_category": "respiratory",
        "dosha_cause": {"vata": "dry, tickling, non-productive cough, worse at night", "pitta": "irritating cough with burning in throat, yellow sputum traces", "kapha": "dry cough with underlying mucus that won't come up"},
        "remedies": {
            "vata": {
                "name": "Ghee, Honey, and Pepper Lick",
                "ingredients": [{"item": "ghee", "amount": "1 tsp", "preparation": "warm"}, {"item": "raw honey", "amount": "1 tsp", "preparation": "raw (do NOT heat)"}, {"item": "black pepper", "amount": "3 pinches", "preparation": "freshly ground"}],
                "preparation": "Mix ghee, honey, and black pepper on a spoon. Lick it slowly, letting it coat the throat. Ghee lubricates the dry Vata cough while black pepper acts as Kaphahara. NEVER heat honey with ghee.",
                "dosage": "3 times daily", "duration": "4 days", "expected_relief": "1 day"
            },
            "pitta": {
                "name": "Yashtimadhu (Licorice) Milk",
                "ingredients": [{"item": "yashtimadhu (licorice) powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Stir yashtimadhu into warm milk with mishri. Drink slowly before bed. Licorice is the foremost Pitta-Kasa (Pitta cough) remedy in Charaka Samhita, Chikitsa Sthana — it soothes and heals inflamed airways.",
                "dosage": "Once at night, optionally also in the morning", "duration": "5 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Vasaka (Adhatoda) Leaf Juice with Honey",
                "ingredients": [{"item": "vasaka (Adhatoda vasica) leaves", "amount": "5–6", "preparation": "fresh, crushed for juice"}, {"item": "raw honey", "amount": "1 tsp", "preparation": "raw (never heat)"}, {"item": "dry ginger powder", "amount": "1/4 tsp", "preparation": "raw"}],
                "preparation": "Extract juice from vasaka leaves by crushing. Mix 1 tsp juice with honey and ginger. Take and do NOT drink water for 30 minutes. Vasaka is the classical Kasa-Shwasa (cough-asthma) herb.",
                "dosage": "Twice daily", "duration": "5 days", "expected_relief": "2 days"
            }
        },
        "universal_remedy": None, "contraindications": ["active_fever_above_101"], "pregnancy_safe": False, "pregnancy_alternative": "Yashtimadhu (licorice) milk only — safe and soothing during pregnancy.", "drug_interactions": ["antihypertensives"], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if cough persists beyond 2 weeks, causes breathlessness, or if blood is present.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "sore_throat", "symptom_id": "sore_throat", "symptom_display": "Sore Throat (Kantharoga)", "symptom_category": "respiratory",
        "dosha_cause": {"vata": "dry, rough throat, hoarseness, scratchy feeling", "pitta": "red, inflamed, burning throat, possible pus, fever", "kapha": "swollen, mucousy, painless or dull ache throat with post-nasal drip"},
        "remedies": {
            "vata": {
                "name": "Sesame Oil Gargle and Haridra Milk",
                "ingredients": [{"item": "sesame oil", "amount": "1 tbsp", "preparation": "warm"}, {"item": "turmeric powder", "amount": "1/2 tsp", "preparation": "in warm milk"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Gargle with warm sesame oil for 2 minutes, then spit. Separately, drink turmeric milk. Oil gargling (Kavala Graha) lubricates dry Vata throat.",
                "dosage": "Gargle twice daily, turmeric milk at night", "duration": "3 days", "expected_relief": "1 day"
            },
            "pitta": {
                "name": "Yashtimadhu and Triphala Gargle",
                "ingredients": [{"item": "yashtimadhu powder", "amount": "1/2 tsp", "preparation": "boiled"}, {"item": "triphala powder", "amount": "1/2 tsp", "preparation": "added after boiling"}, {"item": "water", "amount": "1 cup", "preparation": "boiled, cooled to warm"}],
                "preparation": "Boil yashtimadhu in water. Cool to warm, add triphala. Gargle vigorously for 2 minutes and spit. The bitter-astringent combination clears Pitta infection and reduces inflammation.",
                "dosage": "Gargle 3 times daily", "duration": "4 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Trikatu and Honey Gargle + Steam",
                "ingredients": [{"item": "trikatu churna", "amount": "1/2 tsp", "preparation": "dissolved in warm water"}, {"item": "rock salt", "amount": "1/4 tsp", "preparation": "dissolved"}, {"item": "warm water", "amount": "1 cup", "preparation": "warm"}, {"item": "eucalyptus oil", "amount": "2 drops", "preparation": "for steam"}],
                "preparation": "Gargle with the trikatu-rock salt water. Then steam with eucalyptus oil for 5 minutes. The pungent heat cuts Kapha mucus coating the throat.",
                "dosage": "Gargle 3 times daily, steam once daily", "duration": "4 days", "expected_relief": "Same day"
            }
        },
        "universal_remedy": None, "contraindications": ["strep_throat_with_high_fever"], "pregnancy_safe": True, "pregnancy_alternative": "Warm salt water gargle. Yashtimadhu milk. Avoid trikatu.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if fever is high (>101°F), throat has white patches, or symptoms worsen after 3 days.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "fever_mild", "symptom_id": "fever_mild", "symptom_display": "Mild Fever (Sama Jwara)", "symptom_category": "respiratory",
        "dosha_cause": {"vata": "variable fever, chills, shivering, bodyache, no sweating", "pitta": "high, burning fever, thirst, red eyes, sweating", "kapha": "low-grade, persistent fever, heaviness, drowsiness, no thirst"},
        "remedies": {
            "vata": {
                "name": "Dashamoola Decoction with Ginger",
                "ingredients": [{"item": "dashamoola powder", "amount": "1 tsp", "preparation": "boiled"}, {"item": "fresh ginger", "amount": "1/2 inch", "preparation": "grated, added after boiling"}, {"item": "water", "amount": "2 cups", "preparation": "reduced to 1 cup"}],
                "preparation": "Boil dashamoola in 2 cups water for 10 minutes, reduce to 1 cup. Remove from heat, add grated ginger. Strain and drink warm. Relieves bodyache and chills of Vata Jwara.",
                "dosage": "Twice daily", "duration": "3 days", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Sandalwood and Coriander Cooling Decoction",
                "ingredients": [{"item": "coriander seeds", "amount": "1 tbsp", "preparation": "crushed"}, {"item": "sandalwood powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}, {"item": "water", "amount": "2 cups", "preparation": "boiled"}],
                "preparation": "Boil coriander in water, cool. Add sandalwood and mishri. Drink at room temperature. Apply cool sandalwood paste to forehead. This is the classical Pitta Jwara (burning fever) protocol from Charaka Samhita, Chikitsa Sthana.",
                "dosage": "3 cups daily", "duration": "2 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Trikatu with Tulsi and Ginger Decoction",
                "ingredients": [{"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "added to decoction"}, {"item": "tulsi leaves", "amount": "10", "preparation": "fresh"}, {"item": "ginger", "amount": "1/2 inch", "preparation": "grated"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw, added after cooling"}],
                "preparation": "Boil tulsi and ginger in 2 cups water for 10 minutes. Strain. Cool to warm. Add trikatu and honey. Drink to burn away the Ama causing low-grade Kapha fever.",
                "dosage": "3 times daily", "duration": "3 days", "expected_relief": "Same day"
            }
        },
        "universal_remedy": None, "contraindications": ["pregnancy_with_fever", "high_fever_above_103"], "pregnancy_safe": False, "pregnancy_alternative": "Tulsi and ginger water with mishri only. Consult physician for fever during pregnancy.", "drug_interactions": ["antipyretics"], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if fever exceeds 102°F, lasts more than 3 days, is accompanied by severe headache, stiff neck, or rash.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "sinus_congestion", "symptom_id": "sinus_congestion", "symptom_display": "Sinus Congestion / Pratishyaya", "symptom_category": "respiratory",
        "dosha_cause": {"vata": "dry congestion, little discharge, headache, sneezing fits", "pitta": "yellow or green discharge, sinus infection, heat and facial pain", "kapha": "thick white mucus, persistent blockage, no pain, post-nasal drip"},
        "remedies": {
            "vata": {
                "name": "Anu Taila Nasya (Nasal Drops)",
                "ingredients": [{"item": "anu taila or plain sesame oil", "amount": "2 drops per nostril", "preparation": "warmed to body temp"}],
                "preparation": "Lie on your back, tilt head slightly back. Instil 2 drops of warm oil in each nostril and sniff gently. Stay lying for 1 minute. This is classical Pratimarsha Nasya for dry Vata congestion.",
                "dosage": "Once daily in morning", "duration": "5 days", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Neem Steam Inhalation with Turmeric",
                "ingredients": [{"item": "neem leaves", "amount": "handful", "preparation": "fresh or dried"}, {"item": "turmeric powder", "amount": "1/2 tsp", "preparation": "added to water"}, {"item": "boiling water", "amount": "1 bowl", "preparation": "hot"}],
                "preparation": "Add neem and turmeric to boiling water. Inhale steam with a towel over your head for 7 minutes. Clears infected Pitta mucus and reduces sinus inflammation.",
                "dosage": "Twice daily", "duration": "4 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Trikatu Nasya with Ginger Steam",
                "ingredients": [{"item": "dry ginger powder (sonth)", "amount": "1/4 tsp", "preparation": "sniffed gently"}, {"item": "eucalyptus oil", "amount": "3 drops", "preparation": "in steam bowl"}, {"item": "boiling water", "amount": "1 bowl", "preparation": "hot"}],
                "preparation": "First do eucalyptus steam for 5 minutes to loosen mucus. Then very carefully sniff a tiny amount of ginger powder (like smelling salts) to trigger clearing of deep Kapha mucus. Follow with blowing nose gently.",
                "dosage": "Steam twice daily, ginger sniff once daily", "duration": "4 days", "expected_relief": "Immediate for steam"
            }
        },
        "universal_remedy": None, "contraindications": ["deviated_nasal_septum_severe", "epistaxis"], "pregnancy_safe": True, "pregnancy_alternative": "Plain sesame oil Nasya and steam with plain water only.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if sinusitis is recurrent, or if accompanied by severe facial pain, fever, or vision changes.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "asthma_mild", "symptom_id": "asthma_mild", "symptom_display": "Mild Asthma / Breathing Difficulty (Tamaka Shwasa)", "symptom_category": "respiratory",
        "dosha_cause": {"vata": "spasmodic, variable, triggered by cold/dry air, anxiety", "pitta": "heat-triggered, burning in chest, worse with exertion", "kapha": "mucus-blocked airways, worse at night and in morning, heaviness in chest"},
        "remedies": {
            "vata": {
                "name": "Haridra, Ghee, and Black Pepper Milk",
                "ingredients": [{"item": "turmeric powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "ghee", "amount": "1/2 tsp", "preparation": "melted"}, {"item": "black pepper", "amount": "2 pinches", "preparation": "ground"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Combine all in warm milk. Drink slowly. The ghee lubricates spasming airways. Black pepper (piperine) carries turmeric deep into bronchial tissue. Best before sleep.",
                "dosage": "Once at night", "duration": "14 days", "expected_relief": "3 days"
            },
            "pitta": {
                "name": "Vasaka Leaf and Mishri Syrup",
                "ingredients": [{"item": "vasaka (Adhatoda vasica) leaves", "amount": "5", "preparation": "fresh juice"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}, {"item": "water", "amount": "2 tbsp", "preparation": "room temp"}],
                "preparation": "Extract fresh vasaka juice (1 tsp), mix with mishri and water. Take slowly. Vasaka is the definitive Pitta-Shwasa (asthma) herb — bronchodilatory, anti-inflammatory.",
                "dosage": "Twice daily", "duration": "14 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Sitopaladi with Trikatu and Honey",
                "ingredients": [{"item": "sitopaladi churna", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix sitopaladi, trikatu, and honey into a paste. Lick slowly off a spoon 3 times per day. This is the classical Kapha-Kasa-Shwasa treatment combination from Ashtanga Hridayam, Chikitsa Sthana.",
                "dosage": "3 times daily", "duration": "21 days", "expected_relief": "3 days"
            }
        },
        "universal_remedy": None, "contraindications": ["acute_asthma_attack_use_inhaler"], "pregnancy_safe": False, "pregnancy_alternative": "Turmeric milk only. Avoid trikatu. Consult physician.", "drug_interactions": ["bronchodilators", "steroids"], "severity_gate": "moderate", "consult_doctor_if": "Use prescribed inhaler for any acute attack. Consult doctor if asthma is not well-controlled or worsening.", "source": "Classical", "safety_tier": "use_with_caution"
    },

    # ── SKIN continued (8) ──────────────────────────────────────────────────
    {
        "id": "eczema", "symptom_id": "eczema", "symptom_display": "Eczema / Atopic Dermatitis (Vicharchika)", "symptom_category": "skin",
        "dosha_cause": {"vata": "dry, flaky, cracked eczema, intense itching, no oozing", "pitta": "red, inflamed, oozing, burning eczema, triggered by heat", "kapha": "moist, weeping, thickened, itchy eczema, slow to heal"},
        "remedies": {
            "vata": {
                "name": "Warm Coconut Oil and Neem Leaf Paste",
                "ingredients": [{"item": "coconut oil", "amount": "2 tbsp", "preparation": "warm"}, {"item": "neem powder", "amount": "1 tsp", "preparation": "mixed into oil"}],
                "preparation": "Mix neem powder into warm coconut oil. Apply generously to the dry eczema patches and massage gently. Leave overnight. The combination moisturises Vata dryness and kills the microbial trigger.",
                "dosage": "Apply every night", "duration": "14 days", "expected_relief": "5 days"
            },
            "pitta": {
                "name": "Chandana (Sandalwood) and Aloe Vera Compress",
                "ingredients": [{"item": "fresh aloe vera gel", "amount": "2 tbsp", "preparation": "fresh from leaf"}, {"item": "sandalwood powder", "amount": "1 tsp", "preparation": "mixed into gel"}, {"item": "turmeric powder", "amount": "1/4 tsp", "preparation": "mixed in"}],
                "preparation": "Mix sandalwood and turmeric into fresh aloe gel. Apply thickly to oozing patches and let dry. Rinse with cool water. Apply twice daily. This is the classical Pitta-Kushtha (Pitta skin disease) cooling application.",
                "dosage": "Apply twice daily", "duration": "14 days", "expected_relief": "3 days"
            },
            "kapha": {
                "name": "Neem Decoction Wash with Haridra",
                "ingredients": [{"item": "neem leaves (fresh or dried)", "amount": "handful", "preparation": "boiled in 2L water"}, {"item": "turmeric powder", "amount": "1 tsp", "preparation": "added to boiling water"}],
                "preparation": "Boil neem and turmeric in 2L water. Cool to warm. Wash the affected areas daily. Internally, drink 1 tsp neem juice fasting to address Kapha toxin load from inside.",
                "dosage": "Wash daily, neem juice once daily on empty stomach", "duration": "21 days", "expected_relief": "1 week"
            }
        },
        "universal_remedy": None, "contraindications": ["infected_open_wounds"], "pregnancy_safe": False, "pregnancy_alternative": "Plain coconut oil externally. Avoid internal neem during pregnancy.", "drug_interactions": ["immunosuppressants"], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if eczema is severely infected, covers large body area, or does not respond in 2 weeks.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "hair_fall", "symptom_id": "hair_fall", "symptom_display": "Hair Fall (Khalitya / Indralupta)", "symptom_category": "skin",
        "dosha_cause": {"vata": "dry, brittle hair, diffuse thinning, split ends", "pitta": "premature greying, hot scalp, hair fall after fever or stress", "kapha": "oily scalp, dandruff-triggered hair fall, thick but excessive shedding"},
        "remedies": {
            "vata": {
                "name": "Warm Bhringraj Oil Head Massage",
                "ingredients": [{"item": "bhringraj oil (or Mahabhringraj tail)", "amount": "2 tbsp", "preparation": "warm"}, {"item": "sesame oil", "amount": "1 tbsp", "preparation": "mixed if bhringraj unavailable"}],
                "preparation": "Warm the oil and massage deeply into scalp for 15 minutes using circular motions. Leave for at least 1 hour (or overnight). Wash with a mild shikakai-based shampoo. Bhringraj is the foremost classical herb for Keshya (hair health) — Ashtanga Hridayam, Uttara Sthana.",
                "dosage": "3 times per week", "duration": "60 days", "expected_relief": "3 weeks"
            },
            "pitta": {
                "name": "Amalaki and Brahmi Cooling Hair Mask",
                "ingredients": [{"item": "amla (amalaki) powder", "amount": "2 tsp", "preparation": "mixed with water"}, {"item": "brahmi powder", "amount": "1 tsp", "preparation": "mixed"}, {"item": "rose water", "amount": "to mix", "preparation": "cool"}],
                "preparation": "Mix amla and brahmi powders with rose water to make a paste. Apply to scalp and hair. Leave for 30–45 minutes. Wash with cool water. Also take amla juice (1 tbsp) internally daily.",
                "dosage": "Hair mask twice weekly, amla juice daily", "duration": "60 days", "expected_relief": "3 weeks"
            },
            "kapha": {
                "name": "Neem and Mustard Oil Scalp Treatment",
                "ingredients": [{"item": "mustard oil", "amount": "2 tbsp", "preparation": "warm"}, {"item": "neem powder", "amount": "1 tsp", "preparation": "mixed into oil"}, {"item": "camphor", "amount": "1 small piece", "preparation": "dissolved in warm oil"}],
                "preparation": "Mix neem powder and dissolved camphor into warm mustard oil. Massage vigorously into the scalp. Leave for 1 hour. Wash well with a clarifying shampoo. The pungent combination dries excess Kapha from the scalp.",
                "dosage": "Twice per week", "duration": "60 days", "expected_relief": "3 weeks"
            }
        },
        "universal_remedy": None, "contraindications": ["alopecia_areata_autoimmune"], "pregnancy_safe": True, "pregnancy_alternative": "Bhringraj or coconut oil massage only. Avoid camphor and mustard oil.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult a dermatologist if hair fall is sudden, patchy (alopecia areata), or accompanied by scalp infection.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "dry_skin", "symptom_id": "dry_skin", "symptom_display": "Dry Skin / Rough Complexion", "symptom_category": "skin",
        "dosha_cause": {"vata": "severely dry, flaky, rough, cracked skin — Vata constitution or aggravation", "pitta": "sensitive dry skin with redness and burning", "kapha": "dull, pale, uneven skin tone despite some oiliness"},
        "remedies": {
            "vata": {
                "name": "Sesame Oil Abhyanga (Full-Body Self-Massage)",
                "ingredients": [{"item": "cold-pressed sesame oil", "amount": "1/4 cup", "preparation": "warmed to body temp"}],
                "preparation": "Warm sesame oil. Apply from head to toe before bathing. Massage in the direction of hair growth with gentle circular motions on joints. Leave for 15–20 minutes, then bathe with warm water. Sesame oil is the foremost Vata-pacifying unctuous substance in Ayurveda — feeds Rasa and Rakta Dhatu.",
                "dosage": "Daily (or at minimum 3 times per week)", "duration": "Ongoing", "expected_relief": "3 days"
            },
            "pitta": {
                "name": "Coconut Oil with Rose and Sandalwood",
                "ingredients": [{"item": "cold-pressed coconut oil", "amount": "2 tbsp", "preparation": "room temp"}, {"item": "sandalwood powder", "amount": "1/2 tsp", "preparation": "mixed"}, {"item": "rose water", "amount": "5 drops", "preparation": "mixed"}],
                "preparation": "Mix all into a face and body moisturiser. Apply after bathing on damp skin. Coconut oil is cooling (Sheeta Virya) and ideal for Pitta skin.",
                "dosage": "Daily after bath", "duration": "Ongoing", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Dry Garshana (Silk Glove Dry Brushing) with Turmeric",
                "ingredients": [{"item": "raw silk glove or dry loofah", "amount": "1", "preparation": "dry"}, {"item": "turmeric and besan (chickpea flour)", "amount": "1 tsp each", "preparation": "mixed"}],
                "preparation": "Before bathing, vigorously dry-brush the entire body for 5 minutes to stimulate lymph and remove dead skin. Then apply turmeric-besan paste and bathe. Garshana is the classical Kapha skin treatment for dull, stagnant complexion.",
                "dosage": "3 times per week", "duration": "Ongoing", "expected_relief": "1 week"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "Sesame or coconut oil massage is safe and recommended during pregnancy.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if dryness is accompanied by intense itching, thickening, or scales over large areas.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "urticaria_hives", "symptom_id": "urticaria_hives", "symptom_display": "Urticaria / Hives (Sheetapitta)", "symptom_category": "skin",
        "dosha_cause": {"vata": "fleeting hives from cold exposure, dry patches", "pitta": "red, burning, intensely itchy hives from heat or food allergy", "kapha": "pale, cold, swollen hives, slow to develop and resolve"},
        "remedies": {
            "vata": {
                "name": "Haridra Milk and Warm Sesame Oil Rub",
                "ingredients": [{"item": "turmeric powder", "amount": "1/2 tsp", "preparation": "in warm milk"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "sesame oil", "amount": "1 tsp", "preparation": "warmed for external application"}],
                "preparation": "Drink turmeric milk internally. Apply warm sesame oil directly on the affected skin areas to counter the cold, dry Vata trigger.",
                "dosage": "Internally twice daily, oil apply as needed", "duration": "3 days", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Neem Juice and Coriander Cooler",
                "ingredients": [{"item": "neem juice (from leaves)", "amount": "1 tsp", "preparation": "fresh"}, {"item": "coriander seed water", "amount": "1 cup", "preparation": "soaked overnight, strained"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Drink neem juice and coriander water (with mishri) first thing in the morning. The bitter-cooling combination directly addresses the Pitta Rakta (blood heat) causing burning hives. Apply cool aloe vera gel to affected areas.",
                "dosage": "Internal drink once daily, aloe as needed", "duration": "5 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Trikatu with Nim and Turmeric",
                "ingredients": [{"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "neem powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "turmeric powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix all powders with honey. Take internally. Externally, apply a warm paste of turmeric and neem powder to the hives.",
                "dosage": "Internal twice daily, external once daily", "duration": "5 days", "expected_relief": "2 days"
            }
        },
        "universal_remedy": None, "contraindications": ["anaphylaxis_use_epipen_immediately"], "pregnancy_safe": False, "pregnancy_alternative": "Cool aloe vera gel externally only. Consult physician for urticaria during pregnancy.", "drug_interactions": ["antihistamines", "immunosuppressants"], "severity_gate": "moderate", "consult_doctor_if": "Seek emergency care for throat swelling, difficulty breathing, or severe allergic reaction.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "wound_healing", "symptom_id": "wound_healing", "symptom_display": "Minor Wound / Slow Healing Cuts (Vrana)", "symptom_category": "skin",
        "dosha_cause": {"vata": "dry wound edges, slow granulation, pain", "pitta": "infected wound, pus, redness, warmth", "kapha": "swollen wound, excess exudate, slow healing, cold area"},
        "remedies": {
            "vata": {
                "name": "Ghee and Turmeric Wound Dressing",
                "ingredients": [{"item": "pure ghee", "amount": "1 tsp", "preparation": "melted"}, {"item": "turmeric powder", "amount": "1/4 tsp", "preparation": "mixed into ghee"}],
                "preparation": "After cleaning the wound with plain water, apply a small amount of ghee-turmeric paste. Cover lightly. Change twice daily. Classical Sandhaniya (tissue-joining) application — ghee is the foremost wound healer in Ayurveda.",
                "dosage": "Apply twice daily", "duration": "7 days", "expected_relief": "3 days"
            },
            "pitta": {
                "name": "Neem and Honey Antibacterial Dressing",
                "ingredients": [{"item": "neem powder", "amount": "1/2 tsp", "preparation": "mixed into honey"}, {"item": "raw honey (manuka preferred)", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix neem into raw honey. Apply to the infected wound. Honey is a proven Shothahara (anti-inflammatory) and natural antimicrobial. Neem is the classical Krimighna (anti-infective) topical.",
                "dosage": "Change dressing twice daily", "duration": "5 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Turmeric and Haldi-Sesame Oil Compress",
                "ingredients": [{"item": "turmeric powder", "amount": "1 tsp", "preparation": "mixed with sesame oil"}, {"item": "sesame oil", "amount": "1 tsp", "preparation": "warm"}, {"item": "guggulu powder", "amount": "1/4 tsp", "preparation": "optional, mixed in"}],
                "preparation": "Make a warm paste with turmeric, sesame oil, and guggulu. Apply to the swollen wound area. Cover with cloth. Change twice daily. Guggulu is the classical Shotha-nashana (anti-oedema) herb.",
                "dosage": "Twice daily", "duration": "7 days", "expected_relief": "3 days"
            }
        },
        "universal_remedy": None, "contraindications": ["deep_wounds_require_stitches", "diabetic_wounds"], "pregnancy_safe": True, "pregnancy_alternative": "Ghee and turmeric dressing is safe. Avoid guggulu and neem internally.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult doctor for deep wounds, animal bites, wounds that do not heal in 2 weeks, or signs of serious infection (red streaks, pus).", "source": "Classical", "safety_tier": "home_safe"
    },

    # ── MENTAL / EMOTIONAL continued (6) ────────────────────────────────────
    {
        "id": "depression_mild", "symptom_id": "depression_mild", "symptom_display": "Mild Depression / Low Mood (Vishada)", "symptom_category": "mental",
        "dosha_cause": {"vata": "existential sadness, fear, emptiness, isolation, insomnia", "pitta": "frustration, self-criticism, irritability, burnout masking depression", "kapha": "lethargy, heaviness, hopelessness, excessive sleep, withdrawal"},
        "remedies": {
            "vata": {
                "name": "Ashwagandha and Brahmi Milk with Jatamansi",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "boiled in milk"}, {"item": "brahmi powder", "amount": "1/4 tsp", "preparation": "added after"}, {"item": "jatamansi powder", "amount": "1/4 tsp", "preparation": "added after"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Boil ashwagandha in milk for 3 minutes. Cool to warm. Add brahmi, jatamansi, and mishri. Drink before bed. This Medhya Rasayana (mind-rejuvenating tonic) combination is described in Charaka Samhita, Chikitsa Sthana for Unmada (mental disorders).",
                "dosage": "Once at night", "duration": "30 days", "expected_relief": "1 week"
            },
            "pitta": {
                "name": "Shatavari, Brahmi, and Rose Petal Cooler",
                "ingredients": [{"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "brahmi powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "rose petals", "amount": "1 tsp", "preparation": "dried"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}, {"item": "cool milk", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Mix shatavari, brahmi, and rose in cool milk with mishri. Drink at room temperature in the afternoon or evening. Cools the Pitta frustration-depression while nourishing Ojas.",
                "dosage": "Once daily", "duration": "30 days", "expected_relief": "1 week"
            },
            "kapha": {
                "name": "Trikatu, Brahmi, and Honey Morning Stimulant",
                "ingredients": [{"item": "brahmi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1/2 cup", "preparation": "warm"}],
                "preparation": "Mix brahmi, trikatu, and honey in warm water. Drink every morning. Force brisk physical activity afterward for 30 minutes. Kapha depression requires active, warming, stimulating intervention — not rest.",
                "dosage": "Every morning", "duration": "30 days", "expected_relief": "1 week"
            }
        },
        "universal_remedy": None, "contraindications": ["active_suicidal_ideation_seek_emergency_care"], "pregnancy_safe": False, "pregnancy_alternative": "Brahmi powder with warm milk and mishri only. Avoid ashwagandha and trikatu. Seek professional support.", "drug_interactions": ["antidepressants", "sedatives", "antiepileptics"], "severity_gate": "moderate", "consult_doctor_if": "Always consult a mental health professional for clinical depression. These remedies support mild low mood only. If feeling suicidal, seek immediate help.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "brain_fog", "symptom_id": "brain_fog", "symptom_display": "Brain Fog / Poor Concentration", "symptom_category": "mental",
        "dosha_cause": {"vata": "scattered thinking, forgetfulness, mental overload, poor retention", "pitta": "mental burnout from overwork, eye strain, sharp focus that crashes", "kapha": "dull intellect, slow processing, heaviness in head, post-meal fogginess"},
        "remedies": {
            "vata": {
                "name": "Brahmi and Ashwagandha Medhya Rasayana",
                "ingredients": [{"item": "brahmi (Bacopa monnieri) powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Mix brahmi and ashwagandha in warm milk with mishri. Drink every morning. Brahmi is the foremost Medhya (intellect-enhancing) herb in classical Ayurveda, cited in Charaka Samhita, Chikitsa Sthana for improving Smriti (memory) and Dhi (intellect).",
                "dosage": "Every morning", "duration": "60 days", "expected_relief": "2 weeks"
            },
            "pitta": {
                "name": "Shankhapushpi and Amalaki Cooling Tonic",
                "ingredients": [{"item": "shankhapushpi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "amla (amalaki) juice", "amount": "1 tbsp", "preparation": "fresh or packaged"}, {"item": "mishri", "amount": "1/2 tsp", "preparation": "dissolved"}, {"item": "water", "amount": "1/2 cup", "preparation": "room temp"}],
                "preparation": "Mix shankhapushpi powder with amla juice, mishri, and water. Drink in the morning before food. Shankhapushpi is the classical Pitta-Medhya herb — cools the overheated, burned-out Pitta mind.",
                "dosage": "Every morning", "duration": "60 days", "expected_relief": "2 weeks"
            },
            "kapha": {
                "name": "Vacha and Trikatu Mental Activator",
                "ingredients": [{"item": "vacha (Acorus calamus) powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix vacha, trikatu, and honey. Take every morning. Vacha is the classical Kapha-Medhya herb — the most stimulating of the four Medhya Rasayanas. It cuts through Kapha dullness and activates Manas (mind).",
                "dosage": "Every morning on empty stomach", "duration": "30 days", "expected_relief": "1 week"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Brahmi powder with warm milk and mishri. Avoid vacha.", "drug_interactions": ["sedatives", "antiepileptics", "antidepressants"], "severity_gate": "mild", "consult_doctor_if": "Consult doctor if brain fog is sudden, severe, or accompanied by memory loss, vision changes, or neurological symptoms.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "irritability", "symptom_id": "irritability", "symptom_display": "Irritability / Anger Management (Manas Pitta)", "symptom_category": "mental",
        "dosha_cause": {"vata": "irritability from anxiety, fear, uncertainty, and overwhelm", "pitta": "classic Pitta anger — hot, sharp, critical, controlling", "kapha": "slow-building resentment, stubborn anger, sulking, emotional heaviness"},
        "remedies": {
            "vata": {
                "name": "Ashwagandha and Jatamansi Calming Milk",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "jatamansi (Nardostachys jatamansi) powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Mix herbs in warm milk with mishri. Drink in the evening. Jatamansi is the foremost Vata-Manas (anxious mind) sedative herb in classical Ayurveda.",
                "dosage": "Once daily in the evening", "duration": "21 days", "expected_relief": "3 days"
            },
            "pitta": {
                "name": "Brahmi, Shatavari, and Mishri Cool-Down Drink",
                "ingredients": [{"item": "brahmi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "mishri", "amount": "2 tsp", "preparation": "dissolved"}, {"item": "cool water or coconut water", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Mix brahmi and shatavari in cool water with plenty of mishri. Drink in the afternoon when Pitta peaks. This is the most effective classical formula for Pitta Manas (anger, irritability).",
                "dosage": "Once daily in afternoon", "duration": "21 days", "expected_relief": "3 days"
            },
            "kapha": {
                "name": "Ginger Tea and Physical Release",
                "ingredients": [{"item": "fresh ginger", "amount": "1 inch", "preparation": "grated"}, {"item": "tulsi leaves", "amount": "5", "preparation": "fresh"}, {"item": "black pepper", "amount": "2 pinches", "preparation": "ground"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Boil ginger and tulsi in 1 cup water for 5 minutes. Strain. Cool to warm. Add honey and pepper. Drink. Then engage in 20 minutes of vigorous physical activity to move stagnant Kapha-type emotional energy.",
                "dosage": "Morning daily", "duration": "21 days", "expected_relief": "Same day"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Brahmi milk with mishri. Practice Chandra Bhedana (left nostril breathing) for 10 minutes.", "drug_interactions": ["sedatives", "antidepressants"], "severity_gate": "mild", "consult_doctor_if": "Consult a mental health professional if anger is causing harm to relationships or is uncontrollable.", "source": "Classical", "safety_tier": "home_safe"
    },

    # ── WOMEN'S HEALTH (5) ──────────────────────────────────────────────────
    {
        "id": "pcos_support", "symptom_id": "pcos_support", "symptom_display": "PCOS Support (Artava Dushti)", "symptom_category": "womens_health",
        "dosha_cause": {"vata": "irregular or absent periods, pain, anxiety-driven hormonal imbalance", "pitta": "heavy periods, acne, hair loss, insulin resistance, inflammation", "kapha": "classic PCOS — weight gain, cysts, oligomenorrhea, lethargy, thick discharge"},
        "remedies": {
            "vata": {
                "name": "Shatavari and Ashwagandha Tonic with Sesame",
                "ingredients": [{"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "ashwagandha powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "sesame seeds (black)", "amount": "1 tsp", "preparation": "roasted, powdered"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Mix all in warm milk with mishri. Drink every night. Shatavari is the foremost classical Stanya (hormonal) herb, cited in Charaka Samhita, Chikitsa Sthana for all female reproductive disorders.",
                "dosage": "Once daily at night", "duration": "90 days", "expected_relief": "1 month"
            },
            "pitta": {
                "name": "Shatavari with Amalaki and Aloe Vera",
                "ingredients": [{"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "amla juice", "amount": "1 tbsp", "preparation": "fresh"}, {"item": "aloe vera juice", "amount": "2 tbsp", "preparation": "food grade"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}, {"item": "water", "amount": "1/2 cup", "preparation": "room temp"}],
                "preparation": "Mix shatavari, amla, and aloe vera in water with mishri. Drink in the morning. This cooling combination addresses Pitta-driven PCOS with acne, hair loss, and heavy periods.",
                "dosage": "Once daily in morning", "duration": "90 days", "expected_relief": "1 month"
            },
            "kapha": {
                "name": "Trikatu, Kanchanara, and Turmeric Kapha-Clearing Formula",
                "ingredients": [{"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "kanchanara (Bauhinia variegata) powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "turmeric powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1/2 cup", "preparation": "warm"}],
                "preparation": "Mix all powders with honey and warm water. Drink every morning on empty stomach. Kanchanara is the classical herb for Kapha-type cyst and glandular conditions (Granthi) — described in Ashtanga Hridayam, Chikitsa Sthana.",
                "dosage": "Once daily in morning on empty stomach", "duration": "90 days", "expected_relief": "1 month"
            }
        },
        "universal_remedy": None, "contraindications": ["pregnancy", "active_hormonal_treatment_consult_first"], "pregnancy_safe": False, "pregnancy_alternative": "Not applicable during pregnancy.", "drug_interactions": ["hormone_therapy", "diabetes_medication"], "severity_gate": "mild", "consult_doctor_if": "Work alongside a gynaecologist for PCOS. These are supportive remedies, not a replacement for hormonal management.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "dysmenorrhea", "symptom_id": "dysmenorrhea", "symptom_display": "Dysmenorrhea / Painful Periods", "symptom_category": "womens_health",
        "dosha_cause": {"vata": "severe spasmodic pain, scanty flow, constipation, fear and anxiety", "pitta": "burning pain, heavy flow, fever, irritability", "kapha": "dull bearing-down pain, heavy flow, bloating, nausea"},
        "remedies": {
            "vata": {
                "name": "Dashamoola and Castor Oil Decoction",
                "ingredients": [{"item": "dashamoola powder", "amount": "1 tsp", "preparation": "boiled"}, {"item": "castor oil", "amount": "1 tsp", "preparation": "added after cooling"}, {"item": "warm water", "amount": "1 cup", "preparation": "boiled"}],
                "preparation": "Boil dashamoola in 2 cups of water for 10 minutes. Cool to warm. Add castor oil and mix well. Drink the night before periods are expected. Dashamoola is the classical Vata-analgesic formula for spasmodic dysmenorrhea.",
                "dosage": "Twice daily from 2 days before period onset", "duration": "Per cycle, 5 days", "expected_relief": "Within hours"
            },
            "pitta": {
                "name": "Shatavari and Pomegranate Decoction",
                "ingredients": [{"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "pomegranate juice", "amount": "1/2 cup", "preparation": "fresh"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Mix shatavari powder in pomegranate juice with mishri. Drink at room temperature. Pomegranate (Dadima) cools Pitta heat during periods. Shatavari reduces inflammatory Pitta dysmenorrhea.",
                "dosage": "Twice daily during menses", "duration": "Per cycle, 4 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Ajwain, Hing, and Ginger Hot Decoction",
                "ingredients": [{"item": "ajwain (carom) seeds", "amount": "1 tsp", "preparation": "roasted"}, {"item": "hing (asafoetida)", "amount": "1 large pinch", "preparation": "raw"}, {"item": "ginger powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "rock salt", "amount": "1 pinch", "preparation": "raw"}, {"item": "hot water", "amount": "1 cup", "preparation": "hot"}],
                "preparation": "Boil ajwain in hot water for 3 minutes. Remove from heat. Add hing, ginger, and rock salt. Drink very hot. This combination is the most powerful classical Vata-Kapha Anulomana (downward-moving) blend for Kapha dysmenorrhea.",
                "dosage": "Every 4–6 hours during peak pain", "duration": "Per cycle, 3 days", "expected_relief": "Within 30–60 minutes"
            }
        },
        "universal_remedy": None, "contraindications": ["endometriosis_severe_consult_gynae"], "pregnancy_safe": False, "pregnancy_alternative": "Not for use during pregnancy.", "drug_interactions": ["nsaids", "blood_thinners"], "severity_gate": "moderate", "consult_doctor_if": "Consult a gynaecologist if pain is disabling, if you suspect endometriosis, fibroids, or if periods are very irregular.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "leucorrhoea", "symptom_id": "leucorrhoea", "symptom_display": "Leucorrhoea / White Discharge (Shveta Pradara)", "symptom_category": "womens_health",
        "dosha_cause": {"vata": "scanty, dry, brownish, itching discharge", "pitta": "yellow, offensive, burning discharge with inflammation", "kapha": "thick, white, heavy, odourless, copious discharge"},
        "remedies": {
            "vata": {
                "name": "Shatavari Ghrita with Warm Milk",
                "ingredients": [{"item": "shatavari powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "ghee", "amount": "1/2 tsp", "preparation": "melted"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Mix shatavari and ghee into warm milk with mishri. Drink twice daily. Shatavari with ghee is the classical Stanya-Artava (reproductive tissue nourishing) tonic for Vata Pradara.",
                "dosage": "Twice daily", "duration": "30 days", "expected_relief": "1 week"
            },
            "pitta": {
                "name": "Lodhra and Amalaki Anti-Infection Decoction",
                "ingredients": [{"item": "lodhra (Symplocos racemosa) powder", "amount": "1/2 tsp", "preparation": "boiled"}, {"item": "amla powder", "amount": "1/2 tsp", "preparation": "added after"}, {"item": "water", "amount": "2 cups", "preparation": "boiled, reduced to 1 cup"}],
                "preparation": "Boil lodhra in 2 cups water, reduce to 1 cup. Cool to warm. Add amla powder and drink. Lodhra is the classical herb for Pitta-type gynaecological discharge in Ashtanga Hridayam, Chikitsa Sthana.",
                "dosage": "Once daily in morning", "duration": "30 days", "expected_relief": "1 week"
            },
            "kapha": {
                "name": "Ashoka Bark Decoction",
                "ingredients": [{"item": "ashoka (Saraca asoca) bark powder", "amount": "1 tsp", "preparation": "boiled"}, {"item": "water", "amount": "2 cups", "preparation": "boiled, reduced to 1 cup"}],
                "preparation": "Boil ashoka bark in 2 cups water for 15 minutes, reduce to 1 cup. Strain. Drink warm. Ashoka is the most important classical herb for all Kapha gynaecological conditions, cited across Charaka and Ashtanga Hridayam. Externally, use triphala sitz bath.",
                "dosage": "Once daily in morning on empty stomach", "duration": "30 days", "expected_relief": "1 week"
            }
        },
        "universal_remedy": None, "contraindications": ["pregnancy", "active_infection_needs_antibiotics"], "pregnancy_safe": False, "pregnancy_alternative": "Consult a physician. Shatavari milk can be continued safely.", "drug_interactions": [], "severity_gate": "moderate", "consult_doctor_if": "Consult a gynaecologist if discharge has offensive odour, is accompanied by itching, sores, or fever — may indicate infection needing antibiotic treatment.", "source": "Classical", "safety_tier": "use_with_caution"
    },

    # ── IMMUNITY / SEASONAL / GENERAL (7) ───────────────────────────────────
    {
        "id": "seasonal_detox", "symptom_id": "seasonal_detox", "symptom_display": "Seasonal Detox / Ritucharya Cleanse", "symptom_category": "immunity",
        "dosha_cause": {"vata": "dryness and toxin accumulation in autumn-winter transition", "pitta": "heat toxins accumulated in summer needing autumn release", "kapha": "Kapha Ama accumulated in winter needing spring detox (Vasanta Shodhana)"},
        "remedies": {
            "vata": {
                "name": "Triphala and Bala Oil Autumn Cleanse",
                "ingredients": [{"item": "triphala churna", "amount": "1 tsp", "preparation": "raw"}, {"item": "sesame or Bala taila", "amount": "1 tbsp", "preparation": "warm, for Abhyanga"}, {"item": "warm water", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Take triphala in warm water every night for 14 days. Daily warm sesame oil Abhyanga (self-massage) before bathing. Light, cooked, oily foods for the duration.",
                "dosage": "Triphala nightly for 14 days", "duration": "14 days", "expected_relief": "1 week"
            },
            "pitta": {
                "name": "Amalaki and Guduchi Summer-End Detox",
                "ingredients": [{"item": "amla juice or powder", "amount": "1 tbsp juice / 1/2 tsp powder", "preparation": "raw"}, {"item": "guduchi (Tinospora cordifolia) powder", "amount": "1/2 tsp", "preparation": "boiled or raw"}, {"item": "water", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Take amla and guduchi in water every morning for 21 days. Avoid spicy, fermented, and fried foods. This cools Pitta heat toxins accumulated in summer.",
                "dosage": "Once daily in morning for 21 days", "duration": "21 days", "expected_relief": "1 week"
            },
            "kapha": {
                "name": "Trikatu and Haritaki Spring Kapha Purge",
                "ingredients": [{"item": "haritaki powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Mix haritaki and trikatu with honey. Wash down with warm water. Take every morning for 14–21 days in spring. This is the foundational Vasanta Shodhana (spring purification) for Kapha — described in Ashtanga Hridayam, Sutrasthana, Ritucharya chapter.",
                "dosage": "Once daily in morning for 14–21 days", "duration": "14 days", "expected_relief": "3 days"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Light, easily digestible foods. Triphala is generally avoided in pregnancy — use warm lemon water instead.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "For full Panchakarma-level seasonal detox, consult a qualified Vaidya.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "allergic_rhinitis", "symptom_id": "allergic_rhinitis", "symptom_display": "Allergic Rhinitis / Hay Fever (Vataja Pratishyaya)", "symptom_category": "immunity",
        "dosha_cause": {"vata": "dry, sneezing fits, clear watery discharge, triggered by dust/cold", "pitta": "burning nasal discharge, red eyes, skin rash with allergy", "kapha": "thick, white mucus, blocked nose, post-nasal drip, persistent"},
        "remedies": {
            "vata": {
                "name": "Nasya with Sesame Oil and Turmeric Steam",
                "ingredients": [{"item": "plain sesame oil", "amount": "2 drops per nostril", "preparation": "warm"}, {"item": "turmeric powder", "amount": "1/2 tsp", "preparation": "for steam"}, {"item": "hot water", "amount": "bowl", "preparation": "for steam"}],
                "preparation": "Steam with turmeric water for 5 minutes. Then instil 2 drops of warm sesame oil in each nostril and sniff gently. This is Pratimarsha Nasya for Vata Pratishyaya.",
                "dosage": "Steam twice daily, Nasya once daily in morning", "duration": "10 days", "expected_relief": "2 days"
            },
            "pitta": {
                "name": "Guduchi, Amalaki, and Neem Anti-Allergy Drink",
                "ingredients": [{"item": "guduchi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "amla powder or juice", "amount": "1/2 tsp / 1 tbsp", "preparation": "raw"}, {"item": "neem juice", "amount": "1/2 tsp", "preparation": "fresh"}, {"item": "water", "amount": "1 cup", "preparation": "room temp"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Mix all in water. Drink every morning on empty stomach. This Rasayana combination modulates the immune response and cools Pitta-triggered allergic inflammation. Guduchi is a classical immune-modulator.",
                "dosage": "Once daily in morning for 21 days", "duration": "21 days", "expected_relief": "1 week"
            },
            "kapha": {
                "name": "Sitopaladi and Trikatu Honey Paste",
                "ingredients": [{"item": "sitopaladi churna", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Mix sitopaladi, trikatu, and honey. Lick slowly 3 times per day. This combination clears the thick Kapha mucus and sensitises the immune response to stop overreacting.",
                "dosage": "3 times daily", "duration": "14 days", "expected_relief": "3 days"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Plain sesame oil Nasya and turmeric steam only. Avoid sitopaladi-trikatu formula.", "drug_interactions": ["antihistamines", "immunosuppressants"], "severity_gate": "mild", "consult_doctor_if": "Consult a doctor if allergic rhinitis triggers asthma, if there is fever, or if symptoms are year-round and severely impacting quality of life.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "ojas_building", "symptom_id": "ojas_building", "symptom_display": "General Debility / Ojas Building (Kshaya)", "symptom_category": "immunity",
        "dosha_cause": {"vata": "post-illness weakness, depletion, cachexia, emaciation", "pitta": "burnout, ojas depleted by overwork, fever, or infection", "kapha": "chronic sluggishness, lack of vitality, ojas blocked by Ama rather than depleted"},
        "remedies": {
            "vata": {
                "name": "Ashtavarga Milk (Brimhana Rasayana)",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "bala (Sida cordifolia) powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "ghee", "amount": "1 tsp", "preparation": "melted"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "mishri", "amount": "2 tsp", "preparation": "dissolved"}],
                "preparation": "Mix all herbs and ghee into warm milk with mishri. Drink every morning and night. This is the Brimhana (tissue-building) Rasayana protocol for Vata-Kshaya. Rest is essential alongside.",
                "dosage": "Twice daily", "duration": "60 days", "expected_relief": "2 weeks"
            },
            "pitta": {
                "name": "Chyawanprash and Shatavari Post-Illness Rebuild",
                "ingredients": [{"item": "authentic Chyawanprash", "amount": "1 tsp", "preparation": "ready-made"}, {"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "cool milk", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Take Chyawanprash first, wash down with shatavari mixed in room-temperature milk. The Chyawanprash (richest classical Rasayana) rebuilds Pitta Ojas without further heating.",
                "dosage": "Once in morning", "duration": "60 days", "expected_relief": "2 weeks"
            },
            "kapha": {
                "name": "Trikatu, Guduchi, and Honey Ama-Clearing Tonic",
                "ingredients": [{"item": "guduchi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1/2 cup", "preparation": "warm"}],
                "preparation": "Mix guduchi, trikatu, and honey in warm water. Drink every morning. For Kapha, the debility is from Ama blocking Ojas, not true depletion — clearing Ama reveals the underlying vitality.",
                "dosage": "Once daily in morning", "duration": "30 days", "expected_relief": "1 week"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Chyawanprash (1 tsp) with warm milk. Shatavari milk. Ashwagandha is generally considered safe but verify with physician.", "drug_interactions": ["immunosuppressants", "thyroid_medication"], "severity_gate": "mild", "consult_doctor_if": "Consult a doctor if debility is from a known underlying condition, or if weakness is sudden, severe, or progressive.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "eye_strain", "symptom_id": "eye_strain", "symptom_display": "Eye Strain / Dry Eyes (Akshi Roga)", "symptom_category": "immunity",
        "dosha_cause": {"vata": "dry, gritty, tired eyes, twitching, reduced vision from screens", "pitta": "red, burning, light-sensitive eyes, frequent eye infections", "kapha": "sticky discharge in morning, heavy eyelids, watery yet mucousy eyes"},
        "remedies": {
            "vata": {
                "name": "Rose Water Eye Wash and Triphala Eyecup",
                "ingredients": [{"item": "pure rose water", "amount": "few drops per eye", "preparation": "distilled, refrigerator-cool"}, {"item": "triphala powder", "amount": "1 tsp", "preparation": "boiled in 1 cup water, strained perfectly"}],
                "preparation": "Apply 1–2 drops of cold rose water to each eye using a dropper. For the triphala eyewash, strain the cooled triphala water through a very fine cloth until crystal clear. Wash eyes using an eyecup once daily. Rose water is the classical external Akshi Tarpana for Vata eyes.",
                "dosage": "Rose water as needed, triphala wash once daily", "duration": "14 days", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Cucumber and Aloe Vera Eye Pads",
                "ingredients": [{"item": "fresh cucumber", "amount": "2 slices", "preparation": "refrigerator-cold"}, {"item": "fresh aloe vera gel", "amount": "a small amount", "preparation": "pure gel, no additives"}],
                "preparation": "Lie down. Apply cold cucumber slices to closed eyes for 15 minutes. Follow with a thin layer of pure aloe vera gel around (not in) the eyes. The cooling Sheeta Guna of cucumber directly pacifies Pitta eye heat.",
                "dosage": "Once daily, especially before sleep", "duration": "Ongoing", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Triphala Eye Wash and Trikatu Internally",
                "ingredients": [{"item": "triphala powder", "amount": "1 tsp", "preparation": "boiled, strained"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "internally with honey"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}],
                "preparation": "Do the triphala eyewash (as above) once daily. Internally, take trikatu with honey each morning to reduce the Kapha mucus production that manifests in sticky eyes.",
                "dosage": "Eyewash once daily, internal trikatu-honey once daily", "duration": "14 days", "expected_relief": "2 days"
            }
        },
        "universal_remedy": None, "contraindications": ["active_eye_infection_conjunctivitis"], "pregnancy_safe": True, "pregnancy_alternative": "Cold rose water drops and cucumber pads only. Avoid internal trikatu.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult an ophthalmologist for sudden vision changes, severe pain in the eye, or any eye infection.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "postpartum_weakness", "symptom_id": "postpartum_weakness", "symptom_display": "Postpartum Recovery / Weakness (Sutika Paricharya)", "symptom_category": "womens_health",
        "dosha_cause": {"vata": "primary postpartum state — Vata is always aggravated after delivery causing dryness, pain, weakness", "pitta": "heavy postpartum bleeding, fever, infection, hot flushes", "kapha": "slow recovery, weight retention, depression, breast milk issues"},
        "remedies": {
            "vata": {
                "name": "Sutika Rasayana — Dashamoola, Shatavari, Ghee Milk",
                "ingredients": [{"item": "dashamoola powder", "amount": "1 tsp", "preparation": "boiled in milk"}, {"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "added after"}, {"item": "ghee", "amount": "1 tsp", "preparation": "melted"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "mishri", "amount": "2 tsp", "preparation": "dissolved"}],
                "preparation": "Boil dashamoola in milk for 3 minutes. Cool to warm. Add shatavari, ghee, and mishri. Drink every night. This is the foundational Vata-pacifying Sutika paricharya (postpartum care) formula from Ashtanga Hridayam, Sharir Sthana.",
                "dosage": "Once at night, every night", "duration": "40 days (traditional Sutika period)", "expected_relief": "1 week"
            },
            "pitta": {
                "name": "Amalaki, Shatavari, and Lodhra Recovery Tonic",
                "ingredients": [{"item": "amla powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "mishri", "amount": "2 tsp", "preparation": "dissolved"}, {"item": "cool milk", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Mix amla and shatavari in room-temperature milk with mishri. Drink in the morning. This cooling Pitta-managing tonic stops excessive bleeding, fever tendency, and rebuilds Rakta Dhatu.",
                "dosage": "Once daily in morning", "duration": "40 days", "expected_relief": "1 week"
            },
            "kapha": {
                "name": "Puerperal Recovery — Ashwagandha, Shatavari, Trikatu",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw, added when cooled to warm"}],
                "preparation": "Mix ashwagandha and shatavari in warm milk. Add trikatu and honey when slightly cooled. Drink every morning. This Kapha-clearing, tissue-building combination counters postpartum lethargy and promotes milk quality.",
                "dosage": "Once daily in morning", "duration": "40 days", "expected_relief": "1 week"
            }
        },
        "universal_remedy": None, "contraindications": ["postpartum_infection_seek_medical_care_first"], "pregnancy_safe": False, "pregnancy_alternative": "These are specifically for AFTER delivery. Not for use during pregnancy.", "drug_interactions": ["hormone_therapy"], "severity_gate": "mild", "consult_doctor_if": "Consult a physician immediately for postpartum fever, excessive bleeding, signs of infection, or severe postpartum depression.", "source": "Classical", "safety_tier": "use_with_caution"
    },

    # ── PAIN continued ────────────────────────────────────────────────────────
    {
        "id": "sciatica", "symptom_id": "sciatica", "symptom_display": "Sciatica / Radiating Back Pain (Gridhrasi)", "symptom_category": "pain",
        "dosha_cause": {"vata": "shooting, electric sciatic pain down the leg, worse at night and cold", "pitta": "burning sciatic nerve pain with inflammation and heat", "kapha": "dull, heavy, chronic sciatic pain with hip stiffness"},
        "remedies": {
            "vata": {
                "name": "Bala Taila Abhyanga with Castor Oil",
                "ingredients": [{"item": "bala taila or sesame oil", "amount": "3 tbsp", "preparation": "warm"}, {"item": "castor oil", "amount": "1 tsp", "preparation": "taken internally at bedtime"}],
                "preparation": "Deeply massage warm oil along the lower back, buttock, and sciatic nerve path for 20 minutes. Separately, take castor oil in warm water at bedtime. Castor oil is the classical Vata-anulomana for Gridhrasi — described in Ashtanga Hridayam, Chikitsa Sthana.",
                "dosage": "Massage daily, castor oil at bedtime", "duration": "14 days", "expected_relief": "3 days"
            },
            "pitta": {
                "name": "Nirgundi Leaf Poultice with Aloe",
                "ingredients": [{"item": "nirgundi (Vitex negundo) leaves", "amount": "handful", "preparation": "fresh, crushed"}, {"item": "turmeric powder", "amount": "1/2 tsp", "preparation": "mixed"}, {"item": "aloe vera gel", "amount": "1 tbsp", "preparation": "mixed"}],
                "preparation": "Lightly warm the crushed nirgundi leaves. Mix in turmeric and aloe. Apply as a poultice directly over the sciatic path. Cover with cloth and leave for 30 minutes. Nirgundi is the primary anti-inflammatory nerve-pain herb.",
                "dosage": "Twice daily", "duration": "14 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Rasna and Shallaki Decoction",
                "ingredients": [{"item": "rasna (Alpinia galanga) powder", "amount": "1 tsp", "preparation": "boiled"}, {"item": "shallaki (Boswellia serrata) powder", "amount": "1/2 tsp", "preparation": "added after"}, {"item": "water", "amount": "2 cups", "preparation": "reduced to 1 cup"}],
                "preparation": "Boil rasna in water for 10 minutes. Cool to warm. Add shallaki. Drink. Apply warm mustard oil massage to the hip and leg vigorously. Rasna is the classical Kapha-Vata Shothahara for heavy chronic joint-nerve pain.",
                "dosage": "Decoction twice daily, massage once daily", "duration": "21 days", "expected_relief": "5 days"
            }
        },
        "universal_remedy": None, "contraindications": ["herniated_disc_severe"], "pregnancy_safe": False, "pregnancy_alternative": "Warm sesame oil massage only. Avoid castor oil and shallaki.", "drug_interactions": ["nsaids", "anticoagulants"], "severity_gate": "moderate", "consult_doctor_if": "Consult a doctor if pain is associated with bladder/bowel problems, progressive leg weakness, or follows spine injury.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "edema", "symptom_id": "edema", "symptom_display": "Water Retention / Oedema (Shopha)", "symptom_category": "pain",
        "dosha_cause": {"vata": "cold pitting oedema in extremities from poor circulation and fear", "pitta": "hot, red, inflamed oedema from infection or inflammatory cause", "kapha": "classic Kapha oedema — cold, pitting, worst in morning, symmetrical"},
        "remedies": {
            "vata": {
                "name": "Sesame Oil Lymph Massage with Punarnava",
                "ingredients": [{"item": "sesame oil", "amount": "2 tbsp", "preparation": "warm"}, {"item": "punarnava powder", "amount": "1/2 tsp", "preparation": "boiled in 1 cup water"}],
                "preparation": "Massage warm sesame oil toward the heart (upward) on swollen areas for 15 minutes. Drink punarnava decoction. Punarnava (Boerhavia diffusa) is the classical diuretic and anti-oedema herb.",
                "dosage": "Massage once daily, punarnava twice daily", "duration": "7 days", "expected_relief": "2 days"
            },
            "pitta": {
                "name": "Gokshura and Coriander Cooling Diuretic",
                "ingredients": [{"item": "gokshura powder", "amount": "1/2 tsp", "preparation": "boiled with coriander"}, {"item": "coriander seeds", "amount": "1 tsp", "preparation": "boiled"}, {"item": "water", "amount": "2 cups", "preparation": "reduced to 1 cup"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Boil gokshura and coriander in 2 cups water. Reduce to 1 cup. Add mishri. Drink at room temperature. Gokshura is a Sheeta diuretic ideal for Pitta oedema.",
                "dosage": "Twice daily", "duration": "7 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Punarnava, Dry Ginger, and Trikatu Decoction",
                "ingredients": [{"item": "punarnava powder", "amount": "1 tsp", "preparation": "boiled"}, {"item": "dry ginger powder", "amount": "1/4 tsp", "preparation": "added after"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "added after"}, {"item": "water", "amount": "2 cups", "preparation": "reduced to 1 cup"}],
                "preparation": "Boil punarnava in 2 cups water. Cool to warm. Add ginger and trikatu. Drink on empty stomach. The Ushna-Deepana combination directly drains Kapha oedema by activating lymph flow.",
                "dosage": "Twice daily on empty stomach", "duration": "10 days", "expected_relief": "3 days"
            }
        },
        "universal_remedy": None, "contraindications": ["cardiac_oedema", "renal_failure"], "pregnancy_safe": False, "pregnancy_alternative": "Consult a physician for oedema in pregnancy.", "drug_interactions": ["diuretics", "antihypertensives"], "severity_gate": "moderate", "consult_doctor_if": "Consult a doctor immediately for sudden severe one-sided oedema, oedema with breathlessness, or oedema in pregnancy.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "mouth_ulcers", "symptom_id": "mouth_ulcers", "symptom_display": "Mouth Ulcers (Mukha Pakka)", "symptom_category": "pain",
        "dosha_cause": {"vata": "dry painful ulcers on tongue/cheeks, from stress or B12 deficiency", "pitta": "red, burning, very painful Pitta ulcers from excess heat and acidity", "kapha": "pale, mildly painful ulcers with white coating, slow to heal"},
        "remedies": {
            "vata": {
                "name": "Ghee and Yashtimadhu Application",
                "ingredients": [{"item": "pure ghee", "amount": "1/2 tsp", "preparation": "room temp"}, {"item": "yashtimadhu (licorice) powder", "amount": "1/4 tsp", "preparation": "mixed with ghee"}],
                "preparation": "Mix ghee and yashtimadhu into a paste. Apply directly to the ulcer. Do not eat or drink for 30 minutes. Repeat 3 times daily. Internally, drink warm milk with ghee before bed.",
                "dosage": "3 times daily", "duration": "4 days", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Honey and Turmeric Direct Application",
                "ingredients": [{"item": "raw honey", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "turmeric powder", "amount": "1/4 tsp", "preparation": "mixed"}],
                "preparation": "Mix honey and turmeric into a paste. Apply directly to the burning ulcer 4 times daily. Internally, drink coriander water with mishri to reduce systemic Pitta.",
                "dosage": "4 times daily topically", "duration": "3 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Triphala Mouthwash with Rock Salt",
                "ingredients": [{"item": "triphala powder", "amount": "1 tsp", "preparation": "boiled in 1 cup water, strained"}, {"item": "rock salt", "amount": "1/4 tsp", "preparation": "dissolved"}],
                "preparation": "Boil triphala in water for 5 minutes. Cool to warm. Add rock salt. Swish vigorously for 2 minutes and spit. Repeat 3 times daily. Triphala Kavala is the classical Kapha Mukha Roga treatment.",
                "dosage": "Mouthwash 3 times daily", "duration": "5 days", "expected_relief": "2 days"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "Honey-turmeric application and triphala mouthwash are both safe.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult a doctor if ulcers persist beyond 2 weeks, are very large, recur frequently, or are accompanied by difficulty swallowing.", "source": "Classical", "safety_tier": "home_safe"
    },

    # ── ENERGY / METABOLIC continued ─────────────────────────────────────────
    {
        "id": "anemia_mild", "symptom_id": "anemia_mild", "symptom_display": "Mild Anaemia / Iron Deficiency (Pandu Roga)", "symptom_category": "energy",
        "dosha_cause": {"vata": "Vata Pandu — pale, dry, palpitations, breathless on exertion, emaciation", "pitta": "Pitta Pandu — yellow-green tinge, bleeding tendency, burning", "kapha": "Kapha Pandu — whitish, oedematous, cold, slow, fatty face"},
        "remedies": {
            "vata": {
                "name": "Draksha and Pomegranate Blood Tonic",
                "ingredients": [{"item": "black raisins (draksha)", "amount": "10", "preparation": "soaked overnight"}, {"item": "pomegranate juice", "amount": "1/2 cup", "preparation": "fresh"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Eat soaked raisins every morning. Drink pomegranate juice with mishri. Draksha is the classical Rakta Vardhana (blood-building) food from Charaka Samhita, Chikitsa Sthana, Pandu Roga chapter.",
                "dosage": "Raisins every morning, juice twice daily", "duration": "30 days", "expected_relief": "2 weeks"
            },
            "pitta": {
                "name": "Amalaki Juice and Guduchi Decoction",
                "ingredients": [{"item": "fresh amla juice", "amount": "2 tbsp", "preparation": "fresh"}, {"item": "guduchi powder", "amount": "1/2 tsp", "preparation": "boiled"}, {"item": "water", "amount": "1 cup", "preparation": "boiled"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Drink amla juice in the morning (Vitamin C enhances iron absorption). Evening: drink guduchi decoction with mishri. Guduchi cools Pitta inflammation driving blood loss.",
                "dosage": "Amla morning, guduchi evening", "duration": "30 days", "expected_relief": "2 weeks"
            },
            "kapha": {
                "name": "Punarnava, Trikatu, and Beet-Carrot Juice",
                "ingredients": [{"item": "punarnava powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "beet and carrot juice", "amount": "1/2 cup each", "preparation": "fresh"}],
                "preparation": "Take punarnava and trikatu with honey every morning. Follow with fresh beet-carrot juice. Drains Kapha oedema, stimulates Agni for iron absorption, and directly supplies iron-rich juice.",
                "dosage": "Herbs once daily, juice twice daily", "duration": "30 days", "expected_relief": "2 weeks"
            }
        },
        "universal_remedy": None, "contraindications": ["severe_anaemia_hb_below_8"], "pregnancy_safe": True, "pregnancy_alternative": "Soaked raisins, pomegranate juice, and amla juice are safe. Avoid punarnava and trikatu.", "drug_interactions": ["iron_supplements"], "severity_gate": "moderate", "consult_doctor_if": "Consult a doctor to check haemoglobin. Severe anaemia (Hb < 8 g/dL) requires medical treatment.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "diabetes_lifestyle", "symptom_id": "diabetes_lifestyle", "symptom_display": "Diabetes Lifestyle Support (Prameha / Madhumeha)", "symptom_category": "energy",
        "dosha_cause": {"vata": "Type 1 or emaciated Prameha — thin, depleted, variable blood sugar", "pitta": "Pitta Prameha — medium build, burning urination, inflammation", "kapha": "Classic Type 2 — obese, sluggish, Ama-driven insulin resistance"},
        "remedies": {
            "vata": {
                "name": "Ashwagandha and Methi Seed Morning Protocol",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "shatavari powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "fenugreek (methi) seeds", "amount": "1/2 tsp", "preparation": "soaked overnight — drink the soaking water"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Drink the fenugreek soaking water on empty stomach. Mix ashwagandha and shatavari in warm milk and drink before bed. Fenugreek is the foremost classical anti-Prameha kitchen herb.",
                "dosage": "Methi water every morning, ashwagandha milk at night", "duration": "90 days", "expected_relief": "2 weeks"
            },
            "pitta": {
                "name": "Guduchi and Amalaki Anti-Prameha Tonic",
                "ingredients": [{"item": "guduchi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "amla powder or juice", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "water", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Mix guduchi and amla in water. Drink every morning on empty stomach. Guduchi is the foremost Pitta-Prameha herb — cited in Charaka Samhita, Chikitsa Sthana. Amla lowers postprandial glucose.",
                "dosage": "Once daily in morning on empty stomach", "duration": "90 days", "expected_relief": "2 weeks"
            },
            "kapha": {
                "name": "Bitter Gourd Juice and Trikatu Morning Ritual",
                "ingredients": [{"item": "bitter gourd (karela) juice", "amount": "60ml", "preparation": "fresh"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "mixed in juice"}, {"item": "methi seeds (soaked)", "amount": "1 tsp", "preparation": "soaked overnight, water consumed"}],
                "preparation": "Drink soaked fenugreek water first. Then drink karela juice with trikatu. Karela (Momordica charantia) directly reduces blood glucose. Trikatu kindles sluggish Agni causing insulin resistance.",
                "dosage": "Every morning on empty stomach", "duration": "90 days", "expected_relief": "2 weeks"
            }
        },
        "universal_remedy": None, "contraindications": ["hypoglycemia_risk", "type1_diabetes_on_insulin"], "pregnancy_safe": False, "pregnancy_alternative": "Soaked fenugreek water and amla juice only. Consult physician.", "drug_interactions": ["diabetes_medication", "blood_thinners"], "severity_gate": "moderate", "consult_doctor_if": "Supportive remedies alongside prescribed medication only — never stop diabetic medication without physician guidance.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "cholesterol_support", "symptom_id": "cholesterol_support", "symptom_display": "High Cholesterol Support (Medo Roga)", "symptom_category": "energy",
        "dosha_cause": {"vata": "variable cholesterol from irregular metabolism and stress", "pitta": "inflammatory dyslipidaemia, oxidised LDL, liver heat", "kapha": "classic Kapha Medo Roga — elevated LDL and triglycerides, overweight, sluggish"},
        "remedies": {
            "vata": {
                "name": "Arjuna Bark and Cinnamon Cardiac Tonic",
                "ingredients": [{"item": "arjuna (Terminalia arjuna) bark powder", "amount": "1 tsp", "preparation": "boiled"}, {"item": "cinnamon", "amount": "1 piece", "preparation": "added during boiling"}, {"item": "water", "amount": "2 cups", "preparation": "reduced to 1 cup"}],
                "preparation": "Boil arjuna bark and cinnamon in 2 cups water, reduce to 1 cup. Drink warm in the morning. Arjuna is the foremost classical Hridaya (cardiac) and lipid-modulating herb from Ashtanga Hridayam.",
                "dosage": "Once daily in morning", "duration": "90 days", "expected_relief": "1 month"
            },
            "pitta": {
                "name": "Guggulu with Amalaki Anti-Oxidant Protocol",
                "ingredients": [{"item": "pure guggulu resin", "amount": "1/4 tsp", "preparation": "raw with water"}, {"item": "amla powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Take guggulu and amla in warm water every morning. Guggulu is the definitive classical Medohara (fat-reducing) and lipid-lowering substance. Amla provides antioxidant protection against oxidised LDL.",
                "dosage": "Once daily in morning", "duration": "90 days", "expected_relief": "1 month"
            },
            "kapha": {
                "name": "Triphala and Trikatu Lekhana Protocol",
                "ingredients": [{"item": "triphala churna", "amount": "1 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1/2 cup", "preparation": "warm"}],
                "preparation": "Mix triphala, trikatu, and honey in warm water. Drink every morning on empty stomach. Triphala scrapes (Lekhana) accumulated lipids from channels; Trikatu kindles Agni to metabolise them.",
                "dosage": "Once daily every morning on empty stomach", "duration": "90 days", "expected_relief": "1 month"
            }
        },
        "universal_remedy": None, "contraindications": ["pregnancy", "autoimmune_disease"], "pregnancy_safe": False, "pregnancy_alternative": "Not recommended during pregnancy.", "drug_interactions": ["blood_thinners", "thyroid_medication", "statins"], "severity_gate": "mild", "consult_doctor_if": "Consult a doctor for lipid management, especially with very high LDL or pre-existing heart disease.", "source": "Classical", "safety_tier": "use_with_caution"
    },

    # ── SKIN continued ────────────────────────────────────────────────────────
    {
        "id": "skin_burns_mild", "symptom_id": "skin_burns_mild", "symptom_display": "Mild Burns / Sunburn (Dagdha Vrana)", "symptom_category": "skin",
        "dosha_cause": {"vata": "dry, tight, painful burn", "pitta": "red, intensely inflamed, blistering burn", "kapha": "mild burn with oedema and slow healing"},
        "remedies": {
            "vata": {
                "name": "Ghee and Aloe Vera Soothing Application",
                "ingredients": [{"item": "pure ghee", "amount": "1 tsp", "preparation": "room temp"}, {"item": "aloe vera gel", "amount": "2 tbsp", "preparation": "fresh, cool"}],
                "preparation": "Cool burn under cool running water for 10 minutes. Apply aloe vera gel generously. Let dry. Then apply a thin layer of ghee to prevent moisture loss. Ghee is the classical wound-healing (Sandhaniya) substance in Ayurveda.",
                "dosage": "Every 3–4 hours", "duration": "5 days", "expected_relief": "Immediate cooling"
            },
            "pitta": {
                "name": "Aloe and Sandalwood Cooling Paste",
                "ingredients": [{"item": "fresh aloe vera gel", "amount": "3 tbsp", "preparation": "directly from leaf"}, {"item": "sandalwood powder", "amount": "1 tsp", "preparation": "mixed"}, {"item": "turmeric powder", "amount": "1/4 tsp", "preparation": "mixed"}],
                "preparation": "Cool burn under water first. Apply thick aloe-sandalwood-turmeric paste every 3 hours. Sheeta (cooling) application is the classical Pitta-Dagdha protocol.",
                "dosage": "Every 3 hours", "duration": "5 days", "expected_relief": "Immediate"
            },
            "kapha": {
                "name": "Neem and Honey Anti-Oedema Dressing",
                "ingredients": [{"item": "neem powder", "amount": "1/2 tsp", "preparation": "mixed"}, {"item": "raw honey", "amount": "1 tsp", "preparation": "mixed into paste"}, {"item": "aloe vera gel", "amount": "1 tbsp", "preparation": "base"}],
                "preparation": "Cool burn under water. Mix neem, honey, and aloe. Apply and cover with clean gauze. Honey prevents infection and reduces Kapha oedema. Change every 4–6 hours.",
                "dosage": "Every 4–6 hours", "duration": "5 days", "expected_relief": "Immediate"
            }
        },
        "universal_remedy": None, "contraindications": ["second_degree_burns", "burns_on_face_or_genitals"], "pregnancy_safe": True, "pregnancy_alternative": "Aloe vera and ghee externally are safe.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Seek emergency care for large burns, blistering burns, burns on face/hands/feet, or chemical/electrical burns.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "oily_skin", "symptom_id": "oily_skin", "symptom_display": "Oily Skin / Enlarged Pores", "symptom_category": "skin",
        "dosha_cause": {"vata": "combination skin — oily T-zone with dry patches, stress-driven seborrhea", "pitta": "red, oily, acne-prone, heat-driven excess sebum", "kapha": "heavily oily, enlarged pores, constant shine, slow-healing skin"},
        "remedies": {
            "vata": {
                "name": "Multani Mitti and Rose Water Mask",
                "ingredients": [{"item": "multani mitti (fuller's earth)", "amount": "1 tbsp", "preparation": "powder"}, {"item": "rose water", "amount": "to mix", "preparation": "cool"}, {"item": "sandalwood powder", "amount": "1/2 tsp", "preparation": "added"}],
                "preparation": "Mix multani mitti and sandalwood with rose water. Apply to oily zones. Leave for 15 minutes. Wash with cool water. Absorbs excess sebum without over-drying.",
                "dosage": "Once or twice per week", "duration": "Ongoing", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Sandalwood and Neem Cooling Paste",
                "ingredients": [{"item": "sandalwood powder", "amount": "1 tsp", "preparation": "raw"}, {"item": "neem powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "rose water", "amount": "to mix", "preparation": "cool"}],
                "preparation": "Mix into a paste with rose water. Apply to face. Leave for 20 minutes. Wash with cool water. Internally, drink amla juice daily to reduce systemic Pitta driving sebum.",
                "dosage": "Mask twice weekly, internal remedy daily", "duration": "Ongoing", "expected_relief": "3 days"
            },
            "kapha": {
                "name": "Besan, Neem, and Turmeric Deep Pore Cleanse",
                "ingredients": [{"item": "besan (chickpea flour)", "amount": "2 tbsp", "preparation": "powder"}, {"item": "neem powder", "amount": "1/2 tsp", "preparation": "mixed"}, {"item": "turmeric powder", "amount": "1/4 tsp", "preparation": "mixed"}, {"item": "warm water", "amount": "to mix", "preparation": "warm"}],
                "preparation": "Mix into a paste. Apply to face, massage in circular motions for 2 minutes. Leave 10 minutes. Rinse. Use daily as a face wash. Besan scrubs Kapha sebum; neem controls microbial growth.",
                "dosage": "Daily face wash", "duration": "Ongoing", "expected_relief": "3 days"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "All external applications safe. Avoid neem juice internally.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult a dermatologist for severe seborrheic dermatitis or if rosacea is suspected.", "source": "Traditional", "safety_tier": "home_safe"
    },

    # ── IMMUNITY / GENERAL continued ─────────────────────────────────────────
    {
        "id": "vertigo", "symptom_id": "vertigo", "symptom_display": "Vertigo / Dizziness (Bhrama)", "symptom_category": "immunity",
        "dosha_cause": {"vata": "sudden spinning vertigo from anxiety, dehydration, or blood pressure drop", "pitta": "vertigo with heat, nausea, burning, associated with migraines", "kapha": "chronic dull dizziness from ear congestion or blocked channels"},
        "remedies": {
            "vata": {
                "name": "Brahmi Ghee Nasya",
                "ingredients": [{"item": "brahmi ghee or plain ghee", "amount": "2 drops per nostril", "preparation": "slightly warm"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved in water"}, {"item": "water", "amount": "1 glass", "preparation": "room temp"}],
                "preparation": "Instil warm brahmi ghee in each nostril, sniff gently. Lie down for 2 minutes. Drink mishri water. Brahmi Ghrita Nasya for Vata-Bhrama is described in Ashtanga Hridayam, Chikitsa Sthana.",
                "dosage": "Nasya once daily in morning", "duration": "7 days", "expected_relief": "2 days"
            },
            "pitta": {
                "name": "Shatavari and Coriander Cooling Drink",
                "ingredients": [{"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "coriander seed water", "amount": "1 cup", "preparation": "steeped"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Steep coriander seeds in hot water for 10 minutes. Cool. Add shatavari and mishri. Drink at room temperature. Apply cool rose water to the temples. Cools Pitta-driven dizziness.",
                "dosage": "Twice daily", "duration": "5 days", "expected_relief": "Same day"
            },
            "kapha": {
                "name": "Trikatu with Eucalyptus Steam",
                "ingredients": [{"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "with honey"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "eucalyptus oil", "amount": "3 drops", "preparation": "for steam"}, {"item": "hot water", "amount": "bowl", "preparation": "hot"}],
                "preparation": "Take trikatu with honey internally. Then do eucalyptus steam for 5 minutes to clear blocked ear-sinus channels causing Kapha dizziness.",
                "dosage": "Internal once daily, steam twice daily", "duration": "5 days", "expected_relief": "2 days"
            }
        },
        "universal_remedy": None, "contraindications": ["stroke_symptoms_seek_emergency"], "pregnancy_safe": False, "pregnancy_alternative": "Coriander water with mishri. Avoid Nasya and trikatu.", "drug_interactions": ["antihypertensives", "sedatives"], "severity_gate": "moderate", "consult_doctor_if": "Seek emergency care for sudden severe vertigo with hearing loss, facial drooping, slurred speech, or after head trauma.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "male_reproductive_weakness", "symptom_id": "male_reproductive_weakness", "symptom_display": "Male Vitality / Reproductive Weakness (Vajikarana)", "symptom_category": "immunity",
        "dosha_cause": {"vata": "low libido, erectile weakness, anxiety, depleted Shukra Dhatu", "pitta": "premature ejaculation, heat reducing sperm quality", "kapha": "low libido from heaviness and lethargy, excess weight, suppressed desire"},
        "remedies": {
            "vata": {
                "name": "Ashwagandha, Shilajit, and Ghee Vajikarana Milk",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "purified shilajit", "amount": "pea-sized piece", "preparation": "dissolved in warm milk"}, {"item": "warm whole milk", "amount": "1 cup", "preparation": "warm"}, {"item": "ghee", "amount": "1/2 tsp", "preparation": "melted"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}],
                "preparation": "Dissolve shilajit in warm milk. Add ashwagandha, ghee, and mishri. Drink every night before bed. This is the foundational Vajikarana formula from Charaka Samhita, Chikitsa Sthana, Vajikarana Adhyaya.",
                "dosage": "Once daily at night", "duration": "90 days", "expected_relief": "2 weeks"
            },
            "pitta": {
                "name": "Shatavari and Amalaki Cooling Tonic",
                "ingredients": [{"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "amla powder or juice", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}, {"item": "cold milk", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Mix shatavari and amla in cold milk with mishri. Drink every morning. Shatavari with amalaki reduces Pitta heat that destroys sperm motility and quality.",
                "dosage": "Once daily in morning", "duration": "90 days", "expected_relief": "2 weeks"
            },
            "kapha": {
                "name": "Ashwagandha, Trikatu, and Honey Morning Tonic",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1/2 cup", "preparation": "warm"}],
                "preparation": "Mix ashwagandha and trikatu with honey and warm water. Drink every morning. Follow with vigorous exercise for 30 minutes. Warming and stimulating — kindles desire and testosterone production in Kapha.",
                "dosage": "Once daily in morning", "duration": "90 days", "expected_relief": "2 weeks"
            }
        },
        "universal_remedy": None, "contraindications": ["autoimmune_disease", "hyperthyroid"], "pregnancy_safe": False, "pregnancy_alternative": "Not applicable.", "drug_interactions": ["thyroid_medication", "immunosuppressants", "antidepressants"], "severity_gate": "mild", "consult_doctor_if": "Consult a doctor if erectile dysfunction is sudden (may indicate cardiovascular disease), or if infertility persists beyond 1 year.", "source": "Classical", "safety_tier": "use_with_caution"
    },
    {
        "id": "common_cold", "symptom_id": "common_cold", "symptom_display": "Common Cold (Pratishyaya)", "symptom_category": "respiratory",
        "dosha_cause": {"vata": "sneezing, watery discharge, sore throat, dry body ache, no fever", "pitta": "yellow discharge, throat inflammation, low-grade fever, burning eyes", "kapha": "thick white mucus, heavy head, loss of taste/smell, congestion, drowsiness"},
        "remedies": {
            "vata": {
                "name": "Tulsi, Ginger, and Mishri Decoction",
                "ingredients": [{"item": "fresh tulsi leaves", "amount": "10", "preparation": "fresh"}, {"item": "fresh ginger", "amount": "1/2 inch", "preparation": "grated"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}, {"item": "water", "amount": "2 cups", "preparation": "boiled to 1 cup"}],
                "preparation": "Boil tulsi and ginger in 2 cups water until reduced to 1 cup. Strain. Add mishri. Drink warm. This is the most classical and widely cited cold remedy in Ayurveda — Tulsi-Sunthi (tulsi-ginger) combination, also noted in Ashtanga Hridayam, Chikitsa Sthana.",
                "dosage": "3 cups daily", "duration": "3 days", "expected_relief": "Same day"
            },
            "pitta": {
                "name": "Sitopaladi with Honey and Triphala Gargle",
                "ingredients": [{"item": "sitopaladi churna", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "triphala powder", "amount": "1/2 tsp", "preparation": "boiled for gargle"}],
                "preparation": "Take sitopaladi mixed with honey 3 times daily. Separately, gargle with warm triphala water. Sitopaladi clears Pitta-infected mucus; triphala gargle reduces throat inflammation.",
                "dosage": "Sitopaladi 3 times daily, gargle twice daily", "duration": "4 days", "expected_relief": "2 days"
            },
            "kapha": {
                "name": "Trikatu, Tulsi, and Honey Strong Decoction",
                "ingredients": [{"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "tulsi leaves", "amount": "10", "preparation": "fresh"}, {"item": "ginger", "amount": "1 inch", "preparation": "grated"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw, added after cooling"}, {"item": "water", "amount": "2 cups", "preparation": "boiled to 1 cup"}],
                "preparation": "Boil tulsi and ginger in water. Strain. Cool to warm. Add trikatu and honey. Drink hot. Follow with steam inhalation. This strong pungent combination burns Kapha mucus and clears congested channels.",
                "dosage": "3–4 times daily", "duration": "4 days", "expected_relief": "Same day"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": True, "pregnancy_alternative": "Tulsi-ginger-mishri tea with no trikatu. Warm water gargles. Steam inhalation with plain water.", "drug_interactions": [], "severity_gate": "mild", "consult_doctor_if": "Consult a doctor if cold is accompanied by high fever (>102°F), difficulty breathing, or symptoms persist beyond 7 days.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "stress_burnout", "symptom_id": "stress_burnout", "symptom_display": "Chronic Stress / Burnout (Sahasa-janya Vata)", "symptom_category": "mental",
        "dosha_cause": {"vata": "mental burnout, scattered thoughts, racing mind, inability to relax, insomnia from stress", "pitta": "work-driven burnout, perfectionism, anger, overheating, gut issues from stress", "kapha": "emotional withdrawal, overeating from stress, lethargy, emotional numbing"},
        "remedies": {
            "vata": {
                "name": "Ashwagandha, Jatamansi, and Warm Sesame Oil Crown Application",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1/2 tsp", "preparation": "in warm milk"}, {"item": "jatamansi powder", "amount": "1/4 tsp", "preparation": "in warm milk"}, {"item": "warm milk", "amount": "1 cup", "preparation": "warm"}, {"item": "warm sesame oil", "amount": "1 tsp", "preparation": "for crown and feet"}],
                "preparation": "Drink ashwagandha-jatamansi milk every evening. Apply warm sesame oil to the crown (Murdha Taila) and soles of feet for 10 minutes before sleeping. This combination is the foremost Vata-stress protocol — grounds the nervous system through both herb and oil application.",
                "dosage": "Milk once at night, oil application nightly", "duration": "30 days", "expected_relief": "3 days"
            },
            "pitta": {
                "name": "Brahmi, Shatavari, and Rose Petal Cooler",
                "ingredients": [{"item": "brahmi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "shatavari powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "dried rose petals", "amount": "1 tsp", "preparation": "steeped"}, {"item": "mishri", "amount": "2 tsp", "preparation": "dissolved"}, {"item": "cool milk", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Steep rose petals in warm milk. Cool. Add brahmi, shatavari, and mishri. Drink every afternoon (when Pitta peaks). Brahmi is the foremost Pitta-Manas (mind) cooler — pacifies overthinking, perfectionism, and competitive stress.",
                "dosage": "Once daily in afternoon", "duration": "30 days", "expected_relief": "3 days"
            },
            "kapha": {
                "name": "Trikatu, Brahmi, and Daily Movement Protocol",
                "ingredients": [{"item": "brahmi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}, {"item": "ginger tea", "amount": "1 cup", "preparation": "hot"}],
                "preparation": "Take brahmi and trikatu with honey in warm ginger tea every morning. Mandatorily follow with 30 minutes of vigorous physical activity. Kapha burnout is from stagnation — it requires activation and movement, not rest.",
                "dosage": "Every morning before movement", "duration": "30 days", "expected_relief": "1 week"
            }
        },
        "universal_remedy": None, "contraindications": [], "pregnancy_safe": False, "pregnancy_alternative": "Brahmi milk with mishri. Warm sesame oil foot massage. Avoid trikatu.", "drug_interactions": ["sedatives", "antidepressants", "thyroid_medication"], "severity_gate": "mild", "consult_doctor_if": "Consult a mental health professional if burnout is severe, leads to depression, inability to function, or suicidal thoughts.", "source": "Classical", "safety_tier": "home_safe"
    },
    {
        "id": "hypothyroid_support", "symptom_id": "hypothyroid_support", "symptom_display": "Hypothyroid Lifestyle Support (Galaganda)", "symptom_category": "energy",
        "dosha_cause": {"vata": "Vata-type hypothyroid — dry skin, constipation, cold intolerance, anxious", "pitta": "Pitta-type — hair loss, inflammatory component, heat-cold confusion", "kapha": "Classic Kapha Galaganda — weight gain, cold, sluggish, oedema, low mood, goitre tendency"},
        "remedies": {
            "vata": {
                "name": "Ashwagandha and Guggulu with Warm Water",
                "ingredients": [{"item": "ashwagandha powder", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "guggulu resin (purified)", "amount": "1/4 tsp", "preparation": "raw"}, {"item": "warm water", "amount": "1 cup", "preparation": "warm"}],
                "preparation": "Mix ashwagandha and guggulu in warm water. Drink every morning on empty stomach. Ashwagandha at low dose is cautiously used for Vata-hypothyroid as an adaptogen. Guggulu stimulates thyroid activity. NOTE: Monitor thyroid levels — may require medication dose adjustment.",
                "dosage": "Once daily in morning", "duration": "90 days with monitoring", "expected_relief": "1 month"
            },
            "pitta": {
                "name": "Brahmi and Amalaki Anti-Inflammatory Tonic",
                "ingredients": [{"item": "brahmi powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "amla powder or juice", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "mishri", "amount": "1 tsp", "preparation": "dissolved"}, {"item": "water", "amount": "1 cup", "preparation": "room temp"}],
                "preparation": "Mix brahmi and amla in water with mishri. Drink every morning. Brahmi reduces autoimmune inflammation in Pitta-type hypothyroid (Hashimoto's). Amla is an antioxidant that supports thyroid tissue health.",
                "dosage": "Once daily in morning", "duration": "90 days", "expected_relief": "1 month"
            },
            "kapha": {
                "name": "Kanchanara Guggulu Decoction and Trikatu",
                "ingredients": [{"item": "kanchanara (Bauhinia variegata) bark powder", "amount": "1 tsp", "preparation": "boiled"}, {"item": "trikatu churna", "amount": "1/4 tsp", "preparation": "added after"}, {"item": "water", "amount": "2 cups", "preparation": "reduced to 1 cup"}],
                "preparation": "Boil kanchanara in 2 cups water, reduce to 1 cup. Cool to warm. Add trikatu. Drink every morning on empty stomach. Kanchanara is the foremost classical herb for Gala-ganda (thyroid/goitre conditions) in Ashtanga Hridayam, Chikitsa Sthana. Vigorous daily exercise is essential.",
                "dosage": "Once daily on empty stomach", "duration": "90 days with monitoring", "expected_relief": "1 month"
            }
        },
        "universal_remedy": None, "contraindications": ["hyperthyroid_use_opposite_approach"], "pregnancy_safe": False, "pregnancy_alternative": "Consult physician for thyroid management during pregnancy — do not use guggulu or kanchanara.", "drug_interactions": ["thyroid_medication"], "severity_gate": "mild", "consult_doctor_if": "Always work alongside an endocrinologist. These are supportive lifestyle remedies — never stop thyroid medication. Monitor TSH every 3 months.", "source": "Classical", "safety_tier": "use_with_caution"
    },
]

async def seed_remedies():
    logger.info("Connecting to MongoDB to seed ayurvedic_remedies...")
    logger.info("Connecting to MongoDB to seed ayurvedic_remedies...")
    logger.info("Connecting to MongoDB to seed ayurvedic_remedies...")
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.ayura
    collection = db.kb_ayurvedic_remedies

    logger.info("Dropping existing collection...")
    await collection.drop()

    logger.info(f"Seeding {len(REMEDIES_DATA)} comprehensive remedy entries...")
    result = await collection.insert_many(REMEDIES_DATA)
    
    # Validation summary
    total = len(result.inserted_ids)
    categories = {}
    pregnancy_safe = 0
    home_safe = 0
    sources = {}

    for item in REMEDIES_DATA:
        cat = item.get("symptom_category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        
        if item.get("pregnancy_safe"):
            pregnancy_safe += 1
            
        tier = item.get("safety_tier", "unknown")
        if tier == "home_safe":
            home_safe += 1
            
        src = item.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    print("\n═══════════════════════════════════════")
    print(" REMEDIES SEED SUMMARY")
    print("═══════════════════════════════════════")
    print(f"Total remedies seeded: {total} (target: 60 — categories: pain, digestive, respiratory, skin, mental, women's health, immunity)")
    print(f"By category: {categories}")
    print(f"Pregnancy safe: {pregnancy_safe} / {total}")
    print(f"Home safe: {home_safe} / {total}")
    print(f"By source: {sources}")
    print("═══════════════════════════════════════\n")

if __name__ == "__main__":
    asyncio.run(seed_remedies())
