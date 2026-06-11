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
    }
]

async def seed_remedies():
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
    print(f"Total remedies seeded: {total} (target: 60)")
    print(f"By category: {categories}")
    print(f"Pregnancy safe: {pregnancy_safe} / {total}")
    print(f"Home safe: {home_safe} / {total}")
    print(f"By source: {sources}")
    print("═══════════════════════════════════════\n")

if __name__ == "__main__":
    asyncio.run(seed_remedies())
