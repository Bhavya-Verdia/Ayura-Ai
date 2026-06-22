import json
import urllib.request
import urllib.error
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "knowledge_base"
POSES_FILE = OUTPUT_DIR / "yoga_poses.json"
PRANAYAMA_FILE = OUTPUT_DIR / "pranayama.json"

URL_CATEGORIES = "https://yoga-api-nzy4.onrender.com/v1/categories"

def to_snake_case(name):
    if not name: return "unknown_pose"
    return name.lower().replace(" ", "_").replace("-", "_").replace("'", "").replace("/", "_")

def map_category(cat_name):
    name = cat_name.lower()
    if "stand" in name: return "standing"
    if "seat" in name: return "seated"
    if "supine" in name: return "supine"
    if "prone" in name: return "prone"
    if "invert" in name or "inversion" in name: return "inversion"
    if "backbend" in name or "chest opening" in name: return "backbend"
    if "forward bend" in name or "forward_fold" in name or "forward fold" in name: return "forward_fold"
    if "twist" in name: return "twist"
    if "balanc" in name: return "balancing"
    if "restor" in name: return "restorative"
    return "standing"

def get_dosha_balance(category):
    rules = {
        "standing": {"vata": "balances", "pitta": "balances", "kapha": "balances"},
        "seated": {"vata": "balances", "pitta": "balances", "kapha": "neutral"},
        "supine": {"vata": "balances", "pitta": "balances", "kapha": "aggravates"},
        "prone": {"vata": "neutral", "pitta": "balances", "kapha": "balances"},
        "inversion": {"vata": "aggravates", "pitta": "neutral", "kapha": "balances"},
        "backbend": {"vata": "neutral", "pitta": "aggravates", "kapha": "balances"},
        "forward_fold": {"vata": "balances", "pitta": "balances", "kapha": "neutral"},
        "twist": {"vata": "neutral", "pitta": "balances", "kapha": "balances"},
        "balancing": {"vata": "aggravates", "pitta": "balances", "kapha": "balances"},
        "restorative": {"vata": "balances", "pitta": "balances", "kapha": "aggravates"},
    }
    return rules.get(category, {"vata": "neutral", "pitta": "neutral", "kapha": "neutral"})

def get_contraindications(category, pose_name=""):
    c = []
    if category == "inversion": c.extend(["high_blood_pressure", "glaucoma", "neck_injury", "pregnancy"])
    elif category == "backbend": c.extend(["lower_back_pain", "herniated_disc", "pregnancy_third_trimester"])
    elif category == "twist": c.extend(["pregnancy", "spinal_injury"])
    elif category == "balancing": c.extend(["ankle_injury", "knee_injury"])
    elif category == "supine": c.extend(["pregnancy_third_trimester"])
    
    name_lower = pose_name.lower()
    if "headstand" in name_lower or "shoulderstand" in name_lower:
        c.extend(["neck_injury", "glaucoma", "high_blood_pressure"])
    return list(set(c))

def get_pregnancy_safe(category, level, custom_false=False):
    if custom_false: return False
    if category in ["inversion", "twist", "backbend"]:
        return False
    if category in ["restorative", "standing", "seated"]:
        return True
    return True

def get_sequence_role(category):
    rules = {
        "standing": "main",
        "inversion": "main",
        "backbend": "main",
        "forward_fold": "cooldown",
        "restorative": "cooldown",
        "supine": "cooldown",
        "twist": "main",
        "balancing": "main",
        "seated": "warmup",
        "prone": "main"
    }
    return rules.get(category, "any")

def get_goals(category, benefits):
    goals = set()
    b = benefits.lower()
    
    if category in ["forward_fold", "supine", "seated"] or "flexibility" in b or "stretch" in b:
        goals.add("flexibility")
    if category in ["restorative", "supine", "forward_fold"] or "stress" in b or "relax" in b or "calm" in b:
        goals.add("stress_relief")
    if category in ["standing", "balancing", "inversion", "prone"] or "strength" in b or "core" in b:
        goals.add("strength")
    if category in ["balancing", "standing"] or "balance" in b:
        goals.add("balance")
    if category in ["restorative"] or "heal" in b:
        goals.add("healing")
    if category in ["seated", "supine"] or "mind" in b or "focus" in b:
        goals.add("spiritual")
        
    return list(goals)

def get_duration(level):
    if level == "beginner":
        return {"beginner": 20, "intermediate": 30, "advanced": 45}
    elif level == "advanced":
        return {"beginner": 45, "intermediate": 60, "advanced": 90}
    else: # intermediate
        return {"beginner": 30, "intermediate": 45, "advanced": 60}

def get_pranayama_sync(category):
    if category == "backbend": return "Inhale as you open the chest, exhale to deepen"
    if category == "forward_fold": return "Exhale as you fold, breathe naturally in pose"
    if category == "twist": return "Inhale to lengthen spine, exhale to deepen twist"
    if category == "inversion": return "Breathe slowly and evenly throughout"
    if category == "standing": return "Inhale to ground, exhale to stabilize"
    if category == "seated": return "Breathe naturally, focus on lengthening spine"
    if category == "supine": return "Allow breath to expand belly naturally"
    if category == "restorative": return "Slow deep belly breathing throughout"
    if category == "balancing": return "Steady rhythmic breathing, gaze fixed"
    return "Breathe naturally"

def fix_api_level(name, category):
    n = name.lower()
    beginner_words = ["mountain", "child", "corpse", "savasana", "cat", "cow", "staff", "easy", "seated forward", "butterfly", "bridge", "warrior i", "warrior ii", "triangle", "tree", "downward", "cobra", "sphinx"]
    advanced_words = ["headstand", "shoulderstand", "handstand", "forearm stand", "crow", "eight angle", "flying pigeon", "advanced"]
    
    if category == "restorative": return "beginner"
    if any(w in n for w in advanced_words): return "advanced"
    if any(w in n for w in beginner_words): return "beginner"
    if category == "forward_fold": return "beginner"
    
    if category in ["standing", "twist", "balancing", "backbend", "seated", "prone", "supine", "inversion"]:
        return "intermediate"
        
    return "intermediate"

MANUAL_POSES = [
    # BEGINNER POSES (20)
    {"name": "Mountain Pose", "sanskrit": "Tadasana", "cat": "standing", "lvl": "beginner"},
    {"name": "Child's Pose", "sanskrit": "Balasana", "cat": "restorative", "lvl": "beginner"},
    {"name": "Corpse Pose", "sanskrit": "Savasana", "cat": "supine", "lvl": "beginner"},
    {"name": "Easy Pose", "sanskrit": "Sukhasana", "cat": "seated", "lvl": "beginner"},
    {"name": "Cat Pose", "sanskrit": "Marjaryasana", "cat": "prone", "lvl": "beginner"},
    {"name": "Cow Pose", "sanskrit": "Bitilasana", "cat": "prone", "lvl": "beginner"},
    {"name": "Bridge Pose", "sanskrit": "Setu Bandha Sarvangasana", "cat": "supine", "lvl": "beginner"},
    {"name": "Staff Pose", "sanskrit": "Dandasana", "cat": "seated", "lvl": "beginner"},
    {"name": "Butterfly", "sanskrit": "Baddha Konasana", "cat": "seated", "lvl": "beginner"},
    {"name": "Seated Forward Bend", "sanskrit": "Paschimottanasana", "cat": "forward_fold", "lvl": "beginner"},
    {"name": "Standing Forward Fold", "sanskrit": "Uttanasana", "cat": "forward_fold", "lvl": "beginner"},
    {"name": "Low Lunge", "sanskrit": "Anjaneyasana", "cat": "standing", "lvl": "beginner"},
    {"name": "Legs Up The Wall", "sanskrit": "Viparita Karani", "cat": "inversion", "lvl": "beginner", "preg_safe": False},
    {"name": "Reclining Butterfly", "sanskrit": "Supta Baddha Konasana", "cat": "supine", "lvl": "beginner"},
    {"name": "Cat-Cow Flow", "sanskrit": "Bidalasana", "cat": "prone", "lvl": "beginner"},
    {"name": "Half Standing Forward Fold", "sanskrit": "Ardha Uttanasana", "cat": "forward_fold", "lvl": "beginner"},
    {"name": "Upward Salute", "sanskrit": "Urdhva Hastasana", "cat": "standing", "lvl": "beginner"},
    {"name": "Equestrian Pose", "sanskrit": "Ashwa Sanchalanasana", "cat": "standing", "lvl": "beginner"},
    {"name": "Knees to Chest", "sanskrit": "Apanasana", "cat": "supine", "lvl": "beginner"},
    {"name": "Supine Twist", "sanskrit": "Supta Matsyendrasana", "cat": "twist", "lvl": "beginner", "preg_safe": False},
    
    # INTERMEDIATE POSES (25)
    {"name": "Revolved Triangle", "sanskrit": "Parivrtta Trikonasana", "cat": "twist", "lvl": "intermediate"},
    {"name": "Half Moon Pose", "sanskrit": "Ardha Chandrasana", "cat": "balancing", "lvl": "intermediate"},
    {"name": "Side Plank", "sanskrit": "Vasisthasana", "cat": "balancing", "lvl": "intermediate"},
    {"name": "Camel Pose", "sanskrit": "Ustrasana", "cat": "backbend", "lvl": "intermediate"},
    {"name": "Cobra Pose", "sanskrit": "Bhujangasana", "cat": "backbend", "lvl": "intermediate"},
    {"name": "Locust Pose", "sanskrit": "Salabhasana", "cat": "prone", "lvl": "intermediate"},
    {"name": "Bow Pose", "sanskrit": "Dhanurasana", "cat": "backbend", "lvl": "intermediate"},
    {"name": "Cow Face Pose", "sanskrit": "Gomukhasana", "cat": "seated", "lvl": "intermediate"},
    {"name": "Hero Pose", "sanskrit": "Virasana", "cat": "seated", "lvl": "intermediate"},
    {"name": "Wide Angle Seated Forward Fold", "sanskrit": "Upavistha Konasana", "cat": "forward_fold", "lvl": "intermediate"},
    {"name": "Head to Knee Forward Bend", "sanskrit": "Janu Sirsasana", "cat": "forward_fold", "lvl": "intermediate"},
    {"name": "Revolved Head to Knee", "sanskrit": "Parivrtta Janu Sirsasana", "cat": "twist", "lvl": "intermediate"},
    {"name": "Dancer Pose", "sanskrit": "Natarajasana", "cat": "balancing", "lvl": "intermediate"},
    {"name": "Eagle Pose", "sanskrit": "Garudasana", "cat": "balancing", "lvl": "intermediate"},
    {"name": "Lizard Pose", "sanskrit": "Utthan Pristhasana", "cat": "standing", "lvl": "intermediate"},
    {"name": "Sleeping Vishnu", "sanskrit": "Anantasana", "cat": "supine", "lvl": "intermediate"},
    {"name": "Half Lord of the Fishes", "sanskrit": "Ardha Matsyendrasana", "cat": "twist", "lvl": "intermediate", "preg_safe": False},
    {"name": "Upward Plank", "sanskrit": "Purvottanasana", "cat": "backbend", "lvl": "intermediate"},
    {"name": "Garland/Squat Pose", "sanskrit": "Malasana", "cat": "standing", "lvl": "intermediate"},
    {"name": "Fire Log Pose", "sanskrit": "Agnistambhasana", "cat": "seated", "lvl": "intermediate"},
    {"name": "Reclining Hero", "sanskrit": "Supta Virasana", "cat": "supine", "lvl": "intermediate"},
    {"name": "Mountain in Seated", "sanskrit": "Parvatasana", "cat": "seated", "lvl": "intermediate"},
    {"name": "Side Crow", "sanskrit": "Parsva Bakasana", "cat": "balancing", "lvl": "intermediate"},
    {"name": "Sage Pose", "sanskrit": "Marichyasana", "cat": "twist", "lvl": "intermediate", "preg_safe": False},
    {"name": "Wide Leg Forward Fold", "sanskrit": "Prasarita Padottanasana", "cat": "forward_fold", "lvl": "intermediate"},
    
    # ADVANCED POSES (15)
    {"name": "Headstand", "sanskrit": "Sirsasana", "cat": "inversion", "lvl": "advanced", "preg_safe": False},
    {"name": "Shoulderstand", "sanskrit": "Sarvangasana", "cat": "inversion", "lvl": "advanced", "preg_safe": False},
    {"name": "Plow Pose", "sanskrit": "Halasana", "cat": "inversion", "lvl": "advanced", "preg_safe": False},
    {"name": "Crow Pose", "sanskrit": "Bakasana", "cat": "balancing", "lvl": "advanced"},
    {"name": "Eight Angle Pose", "sanskrit": "Astavakrasana", "cat": "balancing", "lvl": "advanced"},
    {"name": "Flying Splits", "sanskrit": "Eka Pada Koundinyasana", "cat": "balancing", "lvl": "advanced"},
    {"name": "Full Pigeon", "sanskrit": "Kapotasana", "cat": "backbend", "lvl": "advanced"},
    {"name": "Splits", "sanskrit": "Hanumanasana", "cat": "forward_fold", "lvl": "advanced"},
    {"name": "Scorpion Pose", "sanskrit": "Vrschikasana", "cat": "inversion", "lvl": "advanced", "preg_safe": False},
    {"name": "Wheel/Full Backbend", "sanskrit": "Urdhva Dhanurasana", "cat": "backbend", "lvl": "advanced"},
    {"name": "Forearm Stand", "sanskrit": "Pincha Mayurasana", "cat": "inversion", "lvl": "advanced", "preg_safe": False},
    {"name": "Handstand", "sanskrit": "Adho Mukha Vrksasana", "cat": "inversion", "lvl": "advanced", "preg_safe": False},
    {"name": "Firefly Pose", "sanskrit": "Tittibhasana", "cat": "balancing", "lvl": "advanced"},
    {"name": "Tortoise Pose", "sanskrit": "Kurmasana", "cat": "forward_fold", "lvl": "advanced"},
    {"name": "Yoga Sleep Pose", "sanskrit": "Yoganidrasana", "cat": "supine", "lvl": "advanced"}
]

PRANAYAMA = [
    {"name": "Alternate Nostril", "sanskrit": "Nadi Shodhana", "type": "balancing", "lvl": "beginner", "vata": "balances", "pitta": "balances", "kapha": "balances", "preg_safe": True},
    {"name": "Ocean Breath", "sanskrit": "Ujjayi", "type": "grounding", "lvl": "beginner", "vata": "balances", "pitta": "neutral", "kapha": "balances", "preg_safe": True},
    {"name": "Skull Shining", "sanskrit": "Kapalabhati", "type": "cleansing", "lvl": "intermediate", "vata": "aggravates", "pitta": "neutral", "kapha": "balances", "preg_safe": False},
    {"name": "Bellows Breath", "sanskrit": "Bhastrika", "type": "energizing", "lvl": "intermediate", "vata": "aggravates", "pitta": "neutral", "kapha": "balances", "preg_safe": False},
    {"name": "Cooling Breath", "sanskrit": "Sitali", "type": "cooling", "lvl": "beginner", "vata": "neutral", "pitta": "balances", "kapha": "neutral", "preg_safe": True},
    {"name": "Hissing Breath", "sanskrit": "Sitkari", "type": "cooling", "lvl": "beginner", "vata": "neutral", "pitta": "balances", "kapha": "neutral", "preg_safe": True},
    {"name": "Humming Bee", "sanskrit": "Bhramari", "type": "balancing", "lvl": "beginner", "vata": "balances", "pitta": "balances", "kapha": "balances", "preg_safe": True},
    {"name": "Box/Equal Breathing", "sanskrit": "Sama Vritti", "type": "balancing", "lvl": "beginner", "vata": "balances", "pitta": "balances", "kapha": "neutral", "preg_safe": True},
    {"name": "Unequal Breathing", "sanskrit": "Vishama Vritti", "type": "energizing", "lvl": "intermediate", "vata": "neutral", "pitta": "neutral", "kapha": "balances", "preg_safe": True},
    {"name": "Right Nostril", "sanskrit": "Surya Bhedana", "type": "energizing", "lvl": "intermediate", "vata": "balances", "pitta": "aggravates", "kapha": "balances", "preg_safe": False},
    {"name": "Left Nostril", "sanskrit": "Chandra Bhedana", "type": "cooling", "lvl": "intermediate", "vata": "balances", "pitta": "balances", "kapha": "aggravates", "preg_safe": True},
    {"name": "With the Grain", "sanskrit": "Anuloma", "type": "balancing", "lvl": "beginner", "vata": "balances", "pitta": "neutral", "kapha": "neutral", "preg_safe": True},
    {"name": "Against the Grain", "sanskrit": "Viloma", "type": "balancing", "lvl": "beginner", "vata": "neutral", "pitta": "balances", "kapha": "neutral", "preg_safe": True},
    {"name": "Three Part Breath", "sanskrit": "Dirgha", "type": "grounding", "lvl": "beginner", "vata": "balances", "pitta": "balances", "kapha": "neutral", "preg_safe": True},
    {"name": "Swooning Breath", "sanskrit": "Murcha", "type": "grounding", "lvl": "advanced", "vata": "balances", "pitta": "balances", "kapha": "neutral", "preg_safe": False},
    {"name": "Floating Breath", "sanskrit": "Plavini", "type": "grounding", "lvl": "advanced", "vata": "balances", "pitta": "neutral", "kapha": "neutral", "preg_safe": True},
    {"name": "Breath Retention", "sanskrit": "Kumbhaka", "type": "balancing", "lvl": "advanced", "vata": "neutral", "pitta": "neutral", "kapha": "balances", "preg_safe": False},
    {"name": "Extended Cooling", "sanskrit": "Sheetali extended", "type": "cooling", "lvl": "advanced", "vata": "neutral", "pitta": "balances", "kapha": "neutral", "preg_safe": True},
    {"name": "Fire Essence", "sanskrit": "Agni Sara", "type": "cleansing", "lvl": "intermediate", "vata": "neutral", "pitta": "aggravates", "kapha": "balances", "preg_safe": False},
    {"name": "Root Lock Breath", "sanskrit": "Mula Bandha breathing", "type": "grounding", "lvl": "intermediate", "vata": "balances", "pitta": "neutral", "kapha": "neutral", "preg_safe": True}
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    transformed = []
    stats_category = defaultdict(int)
    stats_level = defaultdict(int)
    stats_dosha = {"vata": 0, "pitta": 0, "kapha": 0}
    stats_pregnancy_safe = 0
    
    # 1. FETCH API
    print(f"Fetching from {URL_CATEGORIES}...")
    req = urllib.request.Request(URL_CATEGORIES, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            categories_data = json.loads(response.read().decode('utf-8'))
            
        for cat in categories_data:
            cat_name = cat.get("category_name", "")
            mapped_cat = map_category(cat_name)
            
            poses = cat.get("poses", [])
            for pose in poses:
                english_name = pose.get("english_name", "")
                sanskrit_name = pose.get("sanskrit_name_adapted", pose.get("sanskrit_name", ""))
                pose_id = to_snake_case(english_name)
                
                # PART 1: Use the new level tagging
                level = fix_api_level(english_name, mapped_cat)
                
                dosha_balance = get_dosha_balance(mapped_cat)
                benefits = pose.get("pose_benefits", "Improves flexibility and strength.")
                goals = get_goals(mapped_cat, benefits)
                contraindications = get_contraindications(mapped_cat, english_name)
                
                if "heart_disease" not in contraindications and level == "advanced" and mapped_cat in ["standing", "inversion", "backbend"]:
                    contraindications.extend(["heart_disease", "hypertension"])
                    
                preg_safe = get_pregnancy_safe(mapped_cat, level)
                
                item = {
                    "id": pose_id,
                    "english_name": english_name,
                    "sanskrit_name": sanskrit_name,
                    "category": mapped_cat,
                    "level": level,
                    "duration_seconds": get_duration(level),
                    "primary_benefits": [b.strip() for b in benefits.split(".") if b.strip()],
                    "body_parts": [],
                    "instructions": [step.strip() for step in (pose.get("pose_description") or "").split(".") if step.strip()],
                    "dosha_balance": dosha_balance,
                    "contraindications": list(set(contraindications)),
                    "pregnancy_safe": preg_safe,
                    "goals": goals,
                    "sequence_role": get_sequence_role(mapped_cat),
                    "pranayama_sync": get_pranayama_sync(mapped_cat),
                    "ayurvedic_rationale": "Balancing through mindful breath and structural alignment.",
                    "image_url": pose.get("url_png", pose.get("url_svg", ""))
                }
                transformed.append(item)
    except Exception as e:
        print(f"Failed to fetch API: {e}")

    # 2. ADD MANUAL POSES
    for mp in MANUAL_POSES:
        pose_id = to_snake_case(mp["name"])
        cat = mp["cat"]
        lvl = mp["lvl"]
        preg_safe_override = False if mp.get("preg_safe") is False else None
        
        dosha_balance = get_dosha_balance(cat)
        benefits = f"Improves {cat} strength and flexibility."
        goals = get_goals(cat, benefits)
        
        contra = get_contraindications(cat, mp["name"])
        if "heart_disease" not in contra and lvl == "advanced" and cat in ["standing", "inversion", "backbend"]:
            contra.extend(["heart_disease", "hypertension"])
            
        preg_safe = get_pregnancy_safe(cat, lvl, custom_false=(preg_safe_override is False))
        
        item = {
            "id": pose_id,
            "english_name": mp["name"],
            "sanskrit_name": mp["sanskrit"],
            "category": cat,
            "level": lvl,
            "duration_seconds": get_duration(lvl),
            "primary_benefits": [benefits],
            "body_parts": [],
            "instructions": ["Follow classical alignment.", "Breathe steadily."],
            "dosha_balance": dosha_balance,
            "contraindications": list(set(contra)),
            "pregnancy_safe": preg_safe,
            "goals": goals,
            "sequence_role": get_sequence_role(cat),
            "pranayama_sync": get_pranayama_sync(cat),
            "ayurvedic_rationale": "Classical asana for balancing mind and body.",
            "image_url": ""
        }
        transformed.append(item)
        
    # Deduplicate poses by ID
    unique_poses = {p["id"]: p for p in transformed}.values()
    final_poses = list(unique_poses)
    
    # Calc stats
    for p in final_poses:
        stats_category[p["category"]] += 1
        stats_level[p["level"]] += 1
        if p["dosha_balance"]["vata"] == "balances": stats_dosha["vata"] += 1
        if p["dosha_balance"]["pitta"] == "balances": stats_dosha["pitta"] += 1
        if p["dosha_balance"]["kapha"] == "balances": stats_dosha["kapha"] += 1
        if p["pregnancy_safe"]: stats_pregnancy_safe += 1
        
    with open(POSES_FILE, "w", encoding="utf-8") as f:
        json.dump(final_poses, f, indent=2, ensure_ascii=False)
        
    # 3. PRANAYAMA — skip overwriting if the curated file already has real instructions
    pranayama_count = 0
    skip_pranayama = False
    if PRANAYAMA_FILE.exists():
        existing = json.loads(PRANAYAMA_FILE.read_text(encoding="utf-8"))
        if any(len(p.get("instructions", [])) > 2 for p in existing):
            skip_pranayama = True
            pranayama_count = len(existing)

    if not skip_pranayama:
        pranayama_items = []
        for pr in PRANAYAMA:
            pranayama_items.append({
                "id": to_snake_case(pr["name"]),
                "english_name": pr["name"],
                "sanskrit_name": pr["sanskrit"],
                "type": pr["type"],
                "level": pr["lvl"],
                "duration_minutes": {"beginner": 3, "intermediate": 5, "advanced": 10},
                "dosha_effect": {
                    "vata": pr["vata"],
                    "pitta": pr["pitta"],
                    "kapha": pr["kapha"]
                },
                "best_time": "morning" if pr["type"] in ["energizing", "cleansing"] else "anytime",
                "instructions": ["Find a comfortable seat.", "Follow the breath technique."],
                "benefits": [f"Provides {pr['type']} effects."],
                "contraindications": ["heart_disease", "hypertension"] if pr["type"] == "energizing" else [],
                "pregnancy_safe": pr["preg_safe"]
            })
        with open(PRANAYAMA_FILE, "w", encoding="utf-8") as f:
            json.dump(pranayama_items, f, indent=2, ensure_ascii=False)
        pranayama_count = len(pranayama_items)

    print(f"Total asanas: {len(final_poses)} (target: 100+)")
    print(f"By level: {dict(stats_level)}")
    print(f"By category: {dict(stats_category)}")
    print(f"Pregnancy safe asanas: {stats_pregnancy_safe}")
    print(f"Pranayama techniques: {pranayama_count} ({'preserved' if skip_pranayama else 'generated'})")

if __name__ == "__main__":
    main()
