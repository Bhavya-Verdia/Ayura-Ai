import json
import os
from pathlib import Path

# Setup paths
BASE_DIR = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"
KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)

# 1. YOGA POSES (High quality Ayurvedic tagging)
YOGA_POSES = [
    {
        "id": "y001",
        "name_english": "Downward-Facing Dog",
        "name_sanskrit": "Adho Mukha Svanasana",
        "difficulty": "beginner",
        "benefits": ["calms the brain", "energizes the body", "stretches shoulders and hamstrings"],
        "target_muscles": ["hamstrings", "calves", "shoulders", "hands"],
        "dosha_pacifying": ["pitta", "kapha"],
        "dosha_aggravating": ["vata"], 
        "contraindications": ["carpal_tunnel", "high_bp", "late_pregnancy"],
        "instructions": "Come onto your floor on your hands and knees. Lift knees away from floor.",
        "pose_type": "inversion"
    },
    {
        "id": "y002",
        "name_english": "Child's Pose",
        "name_sanskrit": "Balasana",
        "difficulty": "beginner",
        "benefits": ["relieves stress and fatigue", "stretches hips, thighs, and ankles"],
        "target_muscles": ["lower_back", "hips", "thighs"],
        "dosha_pacifying": ["vata", "pitta"],
        "dosha_aggravating": ["kapha"], 
        "contraindications": ["knee_injury", "pregnancy"],
        "instructions": "Kneel on the floor. Touch your big toes together and sit on heels.",
        "pose_type": "resting"
    },
    {
        "id": "y003",
        "name_english": "Cobra Pose",
        "name_sanskrit": "Bhujangasana",
        "difficulty": "beginner",
        "benefits": ["strengthens the spine", "stretches chest and lungs", "stimulates abdominal organs"],
        "target_muscles": ["spine", "chest", "abdomen"],
        "dosha_pacifying": ["kapha", "vata"],
        "dosha_aggravating": ["pitta"], 
        "contraindications": ["back_injury", "pregnancy", "headache"],
        "instructions": "Lie on your belly. Place your hands under your shoulders and lift chest.",
        "pose_type": "backbend"
    },
    {
        "id": "y004",
        "name_english": "Tree Pose",
        "name_sanskrit": "Vrksasana",
        "difficulty": "beginner",
        "benefits": ["improves balance", "strengthens thighs, calves, and ankles"],
        "target_muscles": ["legs", "core"],
        "dosha_pacifying": ["kapha", "pitta"],
        "dosha_aggravating": ["vata"],
        "contraindications": ["headache", "insomnia", "low_bp"],
        "instructions": "Stand tall. Shift weight to left foot, place right foot on inner left thigh.",
        "pose_type": "standing_balance"
    },
    {
        "id": "y005",
        "name_english": "Corpse Pose",
        "name_sanskrit": "Savasana",
        "difficulty": "beginner",
        "benefits": ["calms the brain", "relaxes the body", "reduces headache"],
        "target_muscles": ["full_body"],
        "dosha_pacifying": ["vata", "pitta"],
        "dosha_aggravating": ["kapha"], 
        "contraindications": ["back_injury"], 
        "instructions": "Lie flat on your back. Keep arms at sides, palms facing up.",
        "pose_type": "resting"
    },
    {
        "id": "y006",
        "name_english": "Triangle Pose",
        "name_sanskrit": "Trikonasana",
        "difficulty": "intermediate",
        "benefits": ["stretches legs", "opens chest", "relieves backache"],
        "target_muscles": ["hamstrings", "groin", "hips"],
        "dosha_pacifying": ["kapha"],
        "dosha_aggravating": ["vata"],
        "contraindications": ["low_bp", "headache", "diarrhea"],
        "instructions": "Stand with feet wide apart. Turn right foot out, extend arms, bend down to right.",
        "pose_type": "standing"
    },
    {
        "id": "y007",
        "name_english": "Warrior I",
        "name_sanskrit": "Virabhadrasana I",
        "difficulty": "intermediate",
        "benefits": ["strengthens shoulders, arms, legs", "opens chest and lungs"],
        "target_muscles": ["shoulders", "arms", "legs"],
        "dosha_pacifying": ["kapha", "vata"],
        "dosha_aggravating": ["pitta"],
        "contraindications": ["high_bp", "heart_problems"],
        "instructions": "Step one foot back, bend front knee, raise arms overhead.",
        "pose_type": "standing"
    },
    {
        "id": "y008",
        "name_english": "Seated Forward Bend",
        "name_sanskrit": "Paschimottanasana",
        "difficulty": "intermediate",
        "benefits": ["calms brain", "stretches spine and hamstrings", "improves digestion"],
        "target_muscles": ["spine", "hamstrings"],
        "dosha_pacifying": ["pitta", "vata"],
        "dosha_aggravating": ["kapha"],
        "contraindications": ["asthma", "diarrhea", "back_injury"],
        "instructions": "Sit with legs straight in front. Inhale arms up, exhale fold forward.",
        "pose_type": "seated_forward_bend"
    },
    {
        "id": "y009",
        "name_english": "Bow Pose",
        "name_sanskrit": "Dhanurasana",
        "difficulty": "intermediate",
        "benefits": ["stretches entire front of body", "strengthens back", "improves posture"],
        "target_muscles": ["chest", "abdomen", "quadriceps"],
        "dosha_pacifying": ["kapha", "vata"],
        "dosha_aggravating": ["pitta"],
        "contraindications": ["high_bp", "low_bp", "hernia", "neck_injury"],
        "instructions": "Lie on belly. Bend knees, grab ankles, lift chest and thighs.",
        "pose_type": "backbend"
    },
    {
        "id": "y010",
        "name_english": "Bridge Pose",
        "name_sanskrit": "Setu Bandhasana",
        "difficulty": "beginner",
        "benefits": ["stretches chest, neck, spine", "calms brain", "stimulates abdominal organs"],
        "target_muscles": ["chest", "neck", "spine"],
        "dosha_pacifying": ["vata", "pitta"],
        "dosha_aggravating": ["kapha"],
        "contraindications": ["neck_injury"],
        "instructions": "Lie on back, bend knees. Lift hips towards ceiling.",
        "pose_type": "backbend"
    }
]

# 2. PRANAYAMA (Breathing exercises)
PRANAYAMA = [
    {
        "id": "p001",
        "name_english": "Alternate Nostril Breathing",
        "name_sanskrit": "Nadi Shodhana",
        "benefits": ["balances left and right brain", "calms nervous system", "reduces anxiety"],
        "dosha_pacifying": ["vata", "pitta", "kapha"], 
        "dosha_aggravating": [],
        "contraindications": ["severe_cold", "blocked_sinuses"],
        "instructions": "Close right nostril, inhale left. Close left, exhale right."
    },
    {
        "id": "p002",
        "name_english": "Skull Shining Breath",
        "name_sanskrit": "Kapalabhati",
        "benefits": ["clears respiratory tract", "energizes nervous system", "improves digestion"],
        "dosha_pacifying": ["kapha"],
        "dosha_aggravating": ["vata", "pitta"], 
        "contraindications": ["high_bp", "heart_disease", "hernia", "pregnancy"],
        "instructions": "Forceful exhalations through nose, passive inhalations."
    },
    {
        "id": "p003",
        "name_english": "Cooling Breath",
        "name_sanskrit": "Sheetali",
        "benefits": ["cools the body", "quenches thirst", "reduces acidity"],
        "dosha_pacifying": ["pitta"],
        "dosha_aggravating": ["vata", "kapha"], 
        "contraindications": ["asthma", "cold", "low_bp"],
        "instructions": "Roll tongue into a tube, inhale through it, exhale nose."
    },
    {
        "id": "p004",
        "name_english": "Bellows Breath",
        "name_sanskrit": "Bhastrika",
        "benefits": ["increases heat in body", "improves metabolism", "clears sinuses"],
        "dosha_pacifying": ["kapha"],
        "dosha_aggravating": ["pitta", "vata"],
        "contraindications": ["high_bp", "heart_disease", "pregnancy", "epilepsy"],
        "instructions": "Forceful inhalation and exhalation, like a blacksmith's bellows."
    },
    {
        "id": "p005",
        "name_english": "Humming Bee Breath",
        "name_sanskrit": "Bhramari",
        "benefits": ["relieves tension", "calms mind", "improves concentration"],
        "dosha_pacifying": ["vata", "pitta"],
        "dosha_aggravating": ["kapha"],
        "contraindications": ["ear_infection"],
        "instructions": "Close ears with thumbs, fingers over eyes. Inhale, exhale making a humming sound."
    }
]

# 3. GYM ROUTINES
GYM_EXERCISES = [
    {
        "id": "g001",
        "name": "Barbell Squat",
        "equipment": "barbell",
        "mechanics": "compound",
        "target_muscle": "lower",
        "secondary_muscles": ["core", "glutes", "hamstrings"],
        "dosha_suitability": {
            "vata": "low_reps_heavy_weight", 
            "pitta": "moderate_reps",
            "kapha": "high_reps_fast_pace" 
        },
        "contraindications": ["knee_injury", "lower_back_pain"],
        "instructions": "Place barbell on upper back, descend until thighs are parallel to floor."
    },
    {
        "id": "g002",
        "name": "Push-up",
        "equipment": "bodyweight",
        "mechanics": "compound",
        "target_muscle": "upper",
        "secondary_muscles": ["core", "triceps", "shoulders"],
        "dosha_suitability": {
            "vata": "moderate_pace", 
            "pitta": "steady_controlled",
            "kapha": "fast_explosive" 
        },
        "contraindications": ["wrist_injury", "shoulder_injury"],
        "instructions": "Start in plank position. Lower body until chest touches floor. Push up."
    },
    {
        "id": "g003",
        "name": "Deadlift",
        "equipment": "barbell",
        "mechanics": "compound",
        "target_muscle": "full_body",
        "secondary_muscles": ["lower_back", "hamstrings", "glutes", "core", "forearms"],
        "dosha_suitability": {
            "vata": "low_reps_heavy_weight",
            "pitta": "moderate_reps",
            "kapha": "high_reps"
        },
        "contraindications": ["lower_back_pain", "hernia"],
        "instructions": "Stand with feet shoulder-width apart. Hinge at hips to grip bar. Lift bar."
    },
    {
        "id": "g004",
        "name": "Dumbbell Lunges",
        "equipment": "dumbbells",
        "mechanics": "compound",
        "target_muscle": "lower",
        "secondary_muscles": ["glutes", "hamstrings", "core"],
        "dosha_suitability": {
            "vata": "slow_controlled",
            "pitta": "moderate",
            "kapha": "walking_lunges_fast"
        },
        "contraindications": ["knee_injury"],
        "instructions": "Hold dumbbells. Step forward with one leg, lower hips until knees are 90 deg."
    },
    {
        "id": "g005",
        "name": "Plank",
        "equipment": "bodyweight",
        "mechanics": "isolation", 
        "target_muscle": "core",
        "secondary_muscles": ["shoulders", "glutes"],
        "dosha_suitability": {
            "vata": "short_holds",
            "pitta": "moderate_holds",
            "kapha": "long_holds"
        },
        "contraindications": ["shoulder_injury", "lower_back_pain"],
        "instructions": "Rest on forearms and toes, keeping body straight."
    },
    {
        "id": "g006",
        "name": "Kettlebell Swing",
        "equipment": "kettlebell",
        "mechanics": "compound",
        "target_muscle": "full_body",
        "secondary_muscles": ["glutes", "hamstrings", "core", "shoulders"],
        "dosha_suitability": {
            "vata": "avoid_if_exhausted",
            "pitta": "moderate_intensity",
            "kapha": "excellent_high_intensity"
        },
        "contraindications": ["lower_back_pain", "shoulder_injury"],
        "instructions": "Hinge at hips, swing kettlebell back, then thrust hips forward to swing it up."
    },
    {
        "id": "g007",
        "name": "Pull-up",
        "equipment": "full_gym", 
        "mechanics": "compound",
        "target_muscle": "upper",
        "secondary_muscles": ["biceps", "core"],
        "dosha_suitability": {
            "vata": "assisted_if_needed",
            "pitta": "bodyweight_or_weighted",
            "kapha": "high_volume"
        },
        "contraindications": ["shoulder_injury", "elbow_injury"],
        "instructions": "Grip bar overhead. Pull body up until chin is over bar. Lower with control."
    },
    {
        "id": "g008",
        "name": "Cable Row",
        "equipment": "cables",
        "mechanics": "compound",
        "target_muscle": "back",
        "secondary_muscles": ["biceps", "core"],
        "dosha_suitability": {
            "vata": "moderate_weight_slow",
            "pitta": "moderate",
            "kapha": "high_volume_fast"
        },
        "contraindications": ["lower_back_pain"],
        "instructions": "Sit at cable machine. Pull handle towards chest while squeezing shoulder blades."
    },
    {
        "id": "g009",
        "name": "Resistance Band Bicep Curls",
        "equipment": "resistance_bands",
        "mechanics": "isolation",
        "target_muscle": "upper",
        "secondary_muscles": [],
        "dosha_suitability": {
            "vata": "slow_reps",
            "pitta": "moderate_reps",
            "kapha": "fast_reps"
        },
        "contraindications": ["elbow_injury", "wrist_injury"],
        "instructions": "Stand on band, hold handles. Curl hands towards shoulders."
    },
    {
        "id": "g010",
        "name": "High Knees",
        "equipment": "bodyweight",
        "mechanics": "compound",
        "target_muscle": "full_body",
        "secondary_muscles": ["core", "calves"],
        "dosha_suitability": {
            "vata": "avoid", 
            "pitta": "moderate",
            "kapha": "excellent" 
        },
        "contraindications": ["knee_injury", "ankle_injury", "high_bp"],
        "instructions": "Run in place, bringing knees as high as possible."
    }
]

# 4. DIET PLANS
DIET_ITEMS = [
    {
        "id": "d001",
        "name": "Kitchari",
        "type": "Lunch/Dinner",
        "dietary_types": ["vegetarian", "vegan", "eggetarian", "non_vegetarian", "pescatarian"],
        "macros": {"protein": "moderate", "carbs": "high", "fats": "moderate"},
        "dosha_effect": "Tridoshic (Balances Vata, Pitta, Kapha)",
        "gunas": ["light", "soft"],
        "allergens": [],
        "ingredients": ["basmati rice", "mung dal", "ghee/coconut oil", "cumin", "coriander", "turmeric", "ginger"],
        "benefits": ["easy to digest", "detoxifying", "nourishing"],
        "contraindications": [] 
    },
    {
        "id": "d002",
        "name": "Oatmeal with Almonds and Cinnamon",
        "type": "Breakfast",
        "dietary_types": ["vegetarian", "vegan", "eggetarian", "non_vegetarian", "pescatarian"],
        "macros": {"protein": "low", "carbs": "high", "fats": "moderate"},
        "dosha_effect": "Balances Vata and Pitta. May increase Kapha if too heavy.",
        "gunas": ["heavy", "soft", "sweet"],
        "allergens": ["nuts_tree"],
        "ingredients": ["rolled oats", "almond milk", "almonds", "cinnamon", "maple syrup"],
        "benefits": ["sustained energy", "heart healthy", "grounding for vata"],
        "contraindications": ["gluten_intolerance_if_not_gf_oats"]
    },
    {
        "id": "d003",
        "name": "Spicy Lentil Soup (Dal)",
        "type": "Lunch/Dinner",
        "dietary_types": ["vegetarian", "vegan", "eggetarian", "non_vegetarian", "pescatarian"],
        "macros": {"protein": "high", "carbs": "moderate", "fats": "low"},
        "dosha_effect": "Balances Kapha and Vata (with oil). May aggravate Pitta if too spicy.",
        "gunas": ["hot", "light"],
        "allergens": [],
        "ingredients": ["red lentils", "garlic", "chili", "mustard seeds", "tomato", "cilantro"],
        "benefits": ["high protein", "stimulates digestion (agni)"],
        "contraindications": ["acidity", "ulcers"]
    },
    {
        "id": "d004",
        "name": "Grilled Salmon with Asparagus",
        "type": "Dinner",
        "dietary_types": ["pescatarian", "non_vegetarian"],
        "macros": {"protein": "high", "carbs": "low", "fats": "high"},
        "dosha_effect": "Balances Vata. May aggravate Pitta (fish is heating) and Kapha (heavy).",
        "gunas": ["heavy", "hot"],
        "allergens": ["fish"],
        "ingredients": ["salmon fillet", "asparagus", "olive oil", "lemon", "black pepper"],
        "benefits": ["omega-3 rich", "joint health", "muscle support"],
        "contraindications": ["high_cholesterol"]
    },
    {
        "id": "d005",
        "name": "Cooling Cucumber and Mint Salad",
        "type": "Snack",
        "dietary_types": ["vegetarian", "vegan", "eggetarian", "non_vegetarian", "pescatarian"],
        "macros": {"protein": "low", "carbs": "low", "fats": "low"},
        "dosha_effect": "Pacifies Pitta. Aggravates Vata and Kapha (cold and raw).",
        "gunas": ["cold", "light", "dry"],
        "allergens": [],
        "ingredients": ["cucumber", "fresh mint", "lime juice", "rock salt"],
        "benefits": ["hydrating", "reduces body heat", "clears skin"],
        "contraindications": ["cold", "cough", "weak_digestion"]
    },
    {
        "id": "d006",
        "name": "Warm Spiced Milk (Golden Milk)",
        "type": "Snack",
        "dietary_types": ["vegetarian", "eggetarian", "non_vegetarian", "pescatarian"],
        "macros": {"protein": "moderate", "carbs": "low", "fats": "moderate"},
        "dosha_effect": "Pacifies Vata and Pitta. May increase Kapha if too sweet/heavy.",
        "gunas": ["heavy", "warm", "liquid"],
        "allergens": ["dairy"],
        "ingredients": ["cow's milk", "turmeric", "black pepper", "cardamom", "ashwagandha"],
        "benefits": ["promotes sleep", "reduces inflammation", "immunity boost"],
        "contraindications": ["lactose_intolerance", "excess_mucus"]
    },
    {
        "id": "d007",
        "name": "Scrambled Eggs with Spinach",
        "type": "Breakfast",
        "dietary_types": ["eggetarian", "non_vegetarian", "pescatarian"],
        "macros": {"protein": "high", "carbs": "low", "fats": "high"},
        "dosha_effect": "Balances Vata. Aggravates Pitta (heating). Moderate for Kapha.",
        "gunas": ["heavy", "hot"],
        "allergens": ["eggs"],
        "ingredients": ["eggs", "spinach", "ghee", "black pepper"],
        "benefits": ["muscle building", "iron rich"],
        "contraindications": []
    },
    {
        "id": "d008",
        "name": "Quinoa Salad with Roasted Root Vegetables",
        "type": "Lunch",
        "dietary_types": ["vegetarian", "vegan", "eggetarian", "non_vegetarian", "pescatarian"],
        "macros": {"protein": "moderate", "carbs": "high", "fats": "low"},
        "dosha_effect": "Balances Pitta and Kapha. Vata should add more dressing/oil.",
        "gunas": ["light", "dry", "warm"],
        "allergens": [],
        "ingredients": ["quinoa", "sweet potato", "carrots", "beets", "olive oil", "lemon"],
        "benefits": ["high fiber", "sustained energy", "blood building"],
        "contraindications": []
    },
    {
        "id": "d009",
        "name": "Chicken Tikka Masala (Lighter Version)",
        "type": "Dinner",
        "dietary_types": ["non_vegetarian"],
        "macros": {"protein": "high", "carbs": "low", "fats": "moderate"},
        "dosha_effect": "Balances Vata and Kapha (if not too oily). Aggravates Pitta (spicy/heating).",
        "gunas": ["hot", "heavy"],
        "allergens": ["dairy"],
        "ingredients": ["chicken breast", "yogurt", "tomato paste", "garam masala", "ginger", "garlic"],
        "benefits": ["high protein", "warming"],
        "contraindications": ["acidity", "ulcers"]
    },
    {
        "id": "d010",
        "name": "Fresh Fruit Bowl (Papaya, Apple, Berries)",
        "type": "Snack",
        "dietary_types": ["vegetarian", "vegan", "eggetarian", "non_vegetarian", "pescatarian"],
        "macros": {"protein": "low", "carbs": "high", "fats": "low"},
        "dosha_effect": "Balances Pitta. Apples balance Kapha. Papaya balances Vata.",
        "gunas": ["light", "cold", "liquid"],
        "allergens": [],
        "ingredients": ["papaya", "apple", "blueberries"],
        "benefits": ["vitamins", "antioxidants", "hydrating"],
        "contraindications": ["diabetes_monitor_portions"]
    }
]

# 5. PANCHAKARMA THERAPIES
PANCHAKARMA_THERAPIES = [
    {
        "id": "pk001",
        "name": "Abhyanga (Warm Oil Massage)",
        "setting": ["home", "clinic", "both"],
        "duration_minutes": 45,
        "target_dosha": "vata",
        "benefits": ["calms nervous system", "lubricates joints", "improves circulation"],
        "recommended_season": ["Hemanta (Winter)", "Shishira (Late Winter)"],
        "contraindications": ["fever", "indigestion", "pregnancy", "kapha_imbalance"],
        "herbs_oils_used": ["Sesame oil", "Mahanarayan oil", "Brahmi oil"],
        "instructions": "Warm the oil. Massage forcefully on limbs, circularly on joints."
    },
    {
        "id": "pk002",
        "name": "Shirodhara (Oil pouring on forehead)",
        "setting": ["clinic"],
        "duration_minutes": 60,
        "target_dosha": "vata_and_pitta",
        "benefits": ["deep relaxation", "relieves insomnia", "reduces stress and anxiety"],
        "recommended_season": ["All seasons"],
        "contraindications": ["brain_tumor", "fever", "acute_illness"],
        "herbs_oils_used": ["Ksheerabala oil", "Brahmi oil", "Buttermilk"],
        "instructions": "Continuous pouring of warm medicated liquid over the forehead."
    },
    {
        "id": "pk003",
        "name": "Swedana (Herbal Steam Therapy)",
        "setting": ["clinic"],
        "duration_minutes": 20,
        "target_dosha": "vata_and_kapha",
        "benefits": ["opens pores", "removes toxins", "reduces stiffness"],
        "recommended_season": ["Hemanta (Winter)", "Vasanta (Spring)"],
        "contraindications": ["pregnancy", "bleeding_disorders", "pitta_imbalance"],
        "herbs_oils_used": ["Dashamoola", "Nirgundi", "Tulsi"],
        "instructions": "Client sits in a steam box, head outside. Herbal steam is applied."
    },
    {
        "id": "pk004",
        "name": "Nasya (Nasal Administration)",
        "setting": ["home", "clinic", "both"],
        "duration_minutes": 15,
        "target_dosha": "kapha_and_vata",
        "benefits": ["clears sinuses", "relieves headaches", "improves mental clarity"],
        "recommended_season": ["Vasanta (Spring)", "Sharad (Autumn)"],
        "contraindications": ["immediately_after_food", "pregnancy", "acute_fever"],
        "herbs_oils_used": ["Anu Tailam", "Shadbindu Tailam"],
        "instructions": "Tilt head back, instill 2-5 drops of medicated oil in each nostril."
    },
    {
        "id": "pk005",
        "name": "Basti (Herbal Enema)",
        "setting": ["clinic"],
        "duration_minutes": 30,
        "target_dosha": "vata",
        "benefits": ["cleanses colon", "nourishes tissues", "treats chronic constipation"],
        "recommended_season": ["Varsha (Monsoon)"],
        "contraindications": ["diarrhea", "bleeding_piles", "indigestion"],
        "herbs_oils_used": ["Dashamoola decoction", "Sesame oil", "Ghee"],
        "instructions": "Administration of herbal decoctions and oils through the rectum."
    },
    {
        "id": "pk006",
        "name": "Vamana (Therapeutic Vomiting)",
        "setting": ["clinic"],
        "duration_minutes": 120,
        "target_dosha": "kapha",
        "benefits": ["removes excess mucus", "treats asthma and bronchitis"],
        "recommended_season": ["Vasanta (Spring)"],
        "contraindications": ["children", "elderly", "pregnancy", "hypertension"],
        "herbs_oils_used": ["Madanaphala", "Licorice", "Salt water"],
        "instructions": "Emetics are given to induce vomiting to expel Kapha from stomach."
    },
    {
        "id": "pk007",
        "name": "Virechana (Purgation Therapy)",
        "setting": ["clinic"],
        "duration_minutes": 120,
        "target_dosha": "pitta",
        "benefits": ["cleanses liver and gallbladder", "treats skin diseases"],
        "recommended_season": ["Sharad (Autumn)"],
        "contraindications": ["weakness", "pregnancy", "diarrhea"],
        "herbs_oils_used": ["Trivrit", "Senna", "Castor oil", "Triphala"],
        "instructions": "Administration of purgative substances to eliminate Pitta toxins."
    },
    {
        "id": "pk008",
        "name": "Udvartana (Herbal Powder Massage)",
        "setting": ["clinic", "both"],
        "duration_minutes": 45,
        "target_dosha": "kapha",
        "benefits": ["reduces fat", "improves skin complexion", "stimulates circulation"],
        "recommended_season": ["Vasanta (Spring)"],
        "contraindications": ["vata_imbalance", "dry_skin", "eczema"],
        "herbs_oils_used": ["Triphala powder", "Chickpea flour", "Turmeric"],
        "instructions": "Deep massage using dry herbal powders against hair direction."
    },
    {
        "id": "pk009",
        "name": "Kati Basti (Lower Back Oil Pool)",
        "setting": ["clinic"],
        "duration_minutes": 30,
        "target_dosha": "vata",
        "benefits": ["relieves lower back pain", "treats sciatica", "lubricates joints"],
        "recommended_season": ["All seasons"],
        "contraindications": ["acute_inflammation", "open_wounds"],
        "herbs_oils_used": ["Mahanarayan oil", "Sahacharadi oil", "Black gram dough"],
        "instructions": "A dough ring is placed on lower back and filled with warm oil."
    },
    {
        "id": "pk010",
        "name": "Netra Tarpana (Eye Bath)",
        "setting": ["clinic", "both"],
        "duration_minutes": 20,
        "target_dosha": "pitta_and_vata",
        "benefits": ["relieves eye strain", "treats dry eyes", "improves vision"],
        "recommended_season": ["Grishma (Summer)", "Sharad (Autumn)"],
        "contraindications": ["eye_infection", "conjunctivitis"],
        "herbs_oils_used": ["Triphala Ghee", "Plain Ghee", "Rose water"],
        "instructions": "Dough rings around eyes filled with warm medicated ghee."
    }
]

def generate_all():
    print("Generating Knowledge Base...")
    
    with open(KNOWLEDGE_DIR / "yoga_plans.json", "w") as f:
        json.dump(YOGA_POSES, f, indent=2)
    print(f"Generated yoga_plans.json ({len(YOGA_POSES)} items)")
    
    with open(KNOWLEDGE_DIR / "pranayama.json", "w") as f:
        json.dump(PRANAYAMA, f, indent=2)
    print(f"Generated pranayama.json ({len(PRANAYAMA)} items)")
    
    with open(KNOWLEDGE_DIR / "gym_routines.json", "w") as f:
        json.dump(GYM_EXERCISES, f, indent=2)
    print(f"Generated gym_routines.json ({len(GYM_EXERCISES)} items)")
    
    with open(KNOWLEDGE_DIR / "diet_plans.json", "w") as f:
        json.dump(DIET_ITEMS, f, indent=2)
    print(f"Generated diet_plans.json ({len(DIET_ITEMS)} items)")
    
    with open(KNOWLEDGE_DIR / "panchakarma_plans.json", "w") as f:
        json.dump(PANCHAKARMA_THERAPIES, f, indent=2)
    print(f"Generated panchakarma_plans.json ({len(PANCHAKARMA_THERAPIES)} items)")
    
    print("\nKnowledge Base Generation Complete!")

if __name__ == "__main__":
    generate_all()
