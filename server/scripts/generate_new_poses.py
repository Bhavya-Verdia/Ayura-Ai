"""
One-time script: generates full Ayurvedic metadata for 50 new yoga poses
and merges them into yoga_poses.json.

Run from the server/ directory:
    python scripts/generate_new_poses.py
"""

import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSES_FILE = ROOT / "data" / "knowledge_base" / "yoga_poses.json"
PROTOCOLS_FILE = ROOT / "data" / "knowledge_base" / "condition_protocols.json"

# ── New poses to generate ─────────────────────────────────────────────────────

NEW_POSES = [
    {"name": "Big Toe Pose",             "sanskrit": "Padangusthasana",               "types": ["Standing","Forward Bend"],  "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/ForwardBendBigToe.png"},
    {"name": "Gorilla Pose",             "sanskrit": "Padahastasana",                 "types": ["Standing","Forward Bend"],  "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/Gorilla.png"},
    {"name": "Bird of Paradise Pose",    "sanskrit": "Svarga Dvijasana",              "types": ["Standing","Balancing"],     "level": "advanced",     "img": "https://pocketyoga.com/assets/images/full/ChairTwistBindUp_L.png"},
    {"name": "Goddess Pose",             "sanskrit": "Utkata Konasana",               "types": ["Standing"],                 "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/Goddess_L.png"},
    {"name": "Revolved Half Moon Pose",  "sanskrit": "Parivritta Ardha Chandrasana",  "types": ["Standing","Balancing"],     "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/HalfMoonRevolved_L.png"},
    {"name": "Pyramid Pose",             "sanskrit": "Parshvottanasana",              "types": ["Standing","Forward Bend"],  "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/PyramidPrayer_L.png"},
    {"name": "Tree Pose",                "sanskrit": "Vrikshasana",                   "types": ["Standing","Balancing"],     "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/TreePrayer_R.png"},
    {"name": "Revolved Triangle Pose",   "sanskrit": "Parivritta Trikonasana",        "types": ["Standing","Twist"],         "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/TriangleRevolved_L.png"},
    {"name": "Revolved Wide Legged Forward Bend", "sanskrit": "Parivritta Prasarita Padottanasana", "types": ["Standing","Forward Bend","Twist"], "level": "intermediate", "img": ""},
    {"name": "Bound Revolved Chair Pose","sanskrit": "Parivritta Utkatasana",         "types": ["Standing","Twist"],         "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/ChairTwistBind_L.png"},
    {"name": "Archer's Pose",            "sanskrit": "Akarna Dhanurasana",            "types": ["Seated"],                   "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/Archer_R.png"},
    {"name": "Seated Gate Pose",         "sanskrit": "Parighasana",                   "types": ["Seated","Lateral Bend"],    "level": "beginner",     "img": ""},
    {"name": "Heron Pose",               "sanskrit": "Kraunchasana",                  "types": ["Seated","Forward Bend"],    "level": "intermediate", "img": ""},
    {"name": "Noose Pose",               "sanskrit": "Pashasana",                     "types": ["Seated","Twist"],           "level": "intermediate", "img": ""},
    {"name": "Side Lunge Pose",          "sanskrit": "Skandasana",                    "types": ["Seated","Balancing"],       "level": "intermediate", "img": ""},
    {"name": "Thunderbolt Pose",         "sanskrit": "Vajrasana",                     "types": ["Seated"],                   "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/Thunderbolt.png"},
    {"name": "Gate Pose",                "sanskrit": "Parighasana",                   "types": ["Kneeling","Lateral Bend"],  "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/Gate_R.png"},
    {"name": "Wind Removing Pose",       "sanskrit": "Pavanamuktasana",               "types": ["Supine"],                   "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/Turtle.png"},
    {"name": "Banana Pose",              "sanskrit": "Supta Nitambasana",             "types": ["Supine"],                   "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/Banana_R.png"},
    {"name": "Happy Baby Pose",          "sanskrit": "Ananda Balasana",               "types": ["Supine"],                   "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/BlissfulBaby.png"},
    {"name": "Reverse Corpse Pose",      "sanskrit": "Advasana",                      "types": ["Prone"],                    "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/CorpseFrontArmsForward.png"},
    {"name": "Puppy Pose",               "sanskrit": "Uttana Shishosana",             "types": ["Prone","Back Bend"],        "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/PuppyExtended.png"},
    {"name": "Frog Pose",                "sanskrit": "Bhekasana",                     "types": ["Prone","Back Bend"],        "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/FrogTraditional.png"},
    {"name": "Snake Pose",               "sanskrit": "Sarpasana",                     "types": ["Prone","Back Bend"],        "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/Snake.png"},
    {"name": "Tiger Pose",               "sanskrit": "Vyaghrasana",                   "types": ["Prone","Back Bend"],        "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/Tiger_L.png"},
    {"name": "Table Pose",               "sanskrit": "Bharmanasana",                  "types": ["Kneeling"],                 "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/BoxNeutral.png"},
    {"name": "Four Limbed Staff Pose",   "sanskrit": "Chaturanga Dandasana",          "types": ["Arm Leg Support"],          "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/FourLimbedStaff.png"},
    {"name": "Upward-Facing Dog Pose",   "sanskrit": "Urdhva Mukha Shvanasana",       "types": ["Prone","Back Bend"],        "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/UpwardDog.png"},
    {"name": "Wild Thing Pose",          "sanskrit": "Chamatkarasana",                "types": ["Backbend","Balancing"],     "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/WildThing_R.png"},
    {"name": "Wheel Pose",               "sanskrit": "Urdhva Dhanurasana",            "types": ["Back Bend"],                "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/Wheel.png"},
    {"name": "Camel Pose",               "sanskrit": "Ushtrasana",                    "types": ["Back Bend"],                "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/Camel.png"},
    {"name": "Upward Plank Pose",        "sanskrit": "Purvottanasana",                "types": ["Back Bend","Arm Support"],  "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/PlankUpward.png"},
    {"name": "Fish Pose",                "sanskrit": "Matsyasana",                    "types": ["Supine","Back Bend"],       "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/FishPreparation.png"},
    {"name": "Plow Pose",                "sanskrit": "Halasana",                      "types": ["Inversion","Forward Bend"], "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/Plow.png"},
    {"name": "Supported Headstand Pose", "sanskrit": "Salamba Shirshasana",           "types": ["Inversion"],                "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/HeadstandSupported.png"},
    {"name": "Supported Shoulder Stand Pose","sanskrit":"Salamba Sarvangasana",       "types": ["Inversion"],                "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/ShoulderstandSupported.png"},
    {"name": "Dolphin Pose",             "sanskrit": "Ardha Pincha Mayurasana",       "types": ["Inversion","Arm Support"],  "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/Dolphin.png"},
    {"name": "Crow Pose",                "sanskrit": "Kakasana",                      "types": ["Arm Balance"],              "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/Crow.png"},
    {"name": "Side Plank Pose",          "sanskrit": "Vasishthasana",                 "types": ["Arm Balance","Balancing"],  "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/PlankSide_R.png"},
    {"name": "Handstand Pose",           "sanskrit": "Adho Mukha Vrikshasana",        "types": ["Inversion","Arm Balance"],  "level": "advanced",     "img": "https://pocketyoga.com/assets/images/full/Handstand.png"},
    {"name": "Half Pigeon Pose",         "sanskrit": "Ardha Kapotasana",              "types": ["Seated","Hip Opener"],      "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/PigeonHalf_L.png"},
    {"name": "Lizard Pose",              "sanskrit": "Uttana Pristhasana",            "types": ["Hip Opener"],               "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/Lizard_L.png"},
    {"name": "Low Lunge Pose",           "sanskrit": "Anjaneyasana",                  "types": ["Standing","Hip Opener"],    "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/WarriorIKneeling_L.png"},
    {"name": "High Lunge Pose",          "sanskrit": "Ashta Chandrasana",             "types": ["Standing","Balancing"],     "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/LungeCrescent_L.png"},
    {"name": "Dancer Pose",              "sanskrit": "Natarajasana",                  "types": ["Standing","Balancing","Back Bend"],"level": "intermediate","img": "https://pocketyoga.com/assets/images/full/LordOfTheDance_L.png"},
    {"name": "Eagle Pose",               "sanskrit": "Garudasana",                    "types": ["Standing","Balancing"],     "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/Eagle_R.png"},
    {"name": "Standing Forward Bend Pose","sanskrit":"Uttanasana",                    "types": ["Standing","Forward Bend"],  "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/ForwardBend.png"},
    {"name": "Warrior III Pose",         "sanskrit": "Virabhadrasana C",              "types": ["Standing","Balancing"],     "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/WarriorIII_L.png"},
    {"name": "Lotus Pose",               "sanskrit": "Padmasana",                     "types": ["Seated","Meditation"],      "level": "intermediate", "img": "https://pocketyoga.com/assets/images/full/LotusFull.png"},
    {"name": "Garland Pose",             "sanskrit": "Malasana",                      "types": ["Seated","Hip Opener"],      "level": "beginner",     "img": "https://pocketyoga.com/assets/images/full/GarlandSideways_L.png"},
]

# ── Category mapper ───────────────────────────────────────────────────────────

CATEGORY_MAP = {
    "Forward Bend": "forward_fold",
    "Back Bend": "backbend",
    "Balancing": "balancing",
    "Twist": "twist",
    "Inversion": "inversion",
    "Seated": "seated",
    "Supine": "supine",
    "Prone": "prone",
    "Arm Balance": "balancing",
    "Hip Opener": "seated",
    "Meditation": "seated",
    "Kneeling": "seated",
    "Arm Leg Support": "prone",
    "Arm Support": "prone",
    "Standing": "standing",
    "Lateral Bend": "standing",
    "Backbend": "backbend",
}

def infer_category(types: list[str]) -> str:
    for t in types:
        c = CATEGORY_MAP.get(t)
        if c:
            return c
    return "standing"

def to_snake(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')

# ── LLM prompt ────────────────────────────────────────────────────────────────

SYSTEM = """You are an expert yoga teacher and Ayurvedic practitioner. Generate accurate, clinically-informed metadata for yoga poses in JSON format. Be precise about contraindications — use only tags from the allowed list."""

ALLOWED_CONTRA = [
    "high_blood_pressure","hypertension","heart_disease","glaucoma",
    "neck_injury","serious_neck_injury","cervical_spondylosis",
    "serious_back_injury","herniated_disc","serious_spinal_injury",
    "spinal_injury","lower_back_pain","knee_injury","knee_replacement",
    "ankle_injury","shoulder_injury","rotator_cuff","groin_injury",
    "pregnancy","pregnancy_third_trimester","wrist_injury"
]

USER_TEMPLATE = """Generate complete metadata for these {n} yoga poses.
Return a JSON object with key "poses" whose value is an array. Each element has EXACTLY these fields:

{{
  "id": "snake_case_english_name",
  "english_name": "...",
  "sanskrit_name": "...",
  "category": one of: standing|balancing|seated|forward_fold|twist|inversion|backbend|restorative|supine|prone,
  "level": one of: beginner|intermediate|advanced,
  "duration_seconds": {{"beginner": 20, "intermediate": 30, "advanced": 45}},
  "primary_benefits": ["3-4 specific benefits"],
  "body_parts": ["list of body parts targeted"],
  "instructions": ["5-7 clear step-by-step instructions"],
  "dosha_balance": {{"vata": "balances|neutral|aggravates", "pitta": "balances|neutral|aggravates", "kapha": "balances|neutral|aggravates"}},
  "contraindications": ["only use tags from this list: {allowed}"],
  "pregnancy_safe": true or false,
  "goals": ["subset of: flexibility|strength|stress_relief|balance|healing|spiritual|energy"],
  "sequence_role": "warmup|main|cooldown",
  "pranayama_sync": "1 sentence on breath coordination for this pose",
  "ayurvedic_rationale": "1-2 sentence Ayurvedic explanation of why this pose is used"
}}

Poses to generate:
{poses_json}

Return ONLY: {{"poses": [...]}}"""

# ── Main ─────────────────────────────────────────────────────────────────────

async def generate_batch(poses_batch: list[dict], llm) -> list[dict]:
    poses_json = json.dumps([
        {"english_name": p["name"], "sanskrit_name": p["sanskrit"],
         "known_types": p["types"], "expertise_level": p["level"]}
        for p in poses_batch
    ], indent=2)

    prompt = USER_TEMPLATE.format(
        n=len(poses_batch),
        allowed=", ".join(ALLOWED_CONTRA),
        poses_json=poses_json,
    )

    response = await llm.generate(prompt=prompt, system_prompt=SYSTEM, json_mode=True)
    result = json.loads(response)
    # Unwrap {"poses": [...]} envelope
    if isinstance(result, dict):
        # Find the first list value
        for v in result.values():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        return []
    if isinstance(result, list):
        return [r for r in result if isinstance(r, dict)]
    return []


async def main():
    sys.path.insert(0, str(ROOT))
    from ai.llm_client import llm_client

    # Load existing poses
    existing = json.loads(POSES_FILE.read_text())
    existing_ids = {p["id"] for p in existing}

    # Load condition protocols for back-fill
    protocols = json.loads(PROTOCOLS_FILE.read_text())
    pose_to_conditions: dict[str, list[str]] = {}
    for proto in protocols:
        cond = proto["condition"]
        for pid in proto.get("priority_pose_ids", []):
            pose_to_conditions.setdefault(pid, []).append(cond)

    tag_to_conditions = {
        "high_blood_pressure": ["hypertension"], "hypertension": ["hypertension"],
        "heart_disease": ["heart_disease"], "glaucoma": ["glaucoma"],
        "neck_injury": ["cervical_spondylosis"], "serious_neck_injury": ["cervical_spondylosis"],
        "cervical_spondylosis": ["cervical_spondylosis"],
        "serious_back_injury": ["sciatica","back_pain"], "herniated_disc": ["back_pain"],
        "serious_spinal_injury": ["back_pain"], "spinal_injury": ["back_pain"],
        "lower_back_pain": ["back_pain"],
        "knee_injury": ["arthritis"], "knee_replacement": ["arthritis"],
        "ankle_injury": ["arthritis"], "shoulder_injury": ["arthritis"], "rotator_cuff": ["arthritis"],
    }

    # Filter out any already in existing poses
    new = [p for p in NEW_POSES if to_snake(p["name"]) not in existing_ids]
    print(f"Generating {len(new)} new poses in batches of 5 …")

    generated = []
    BATCH = 5
    for i in range(0, len(new), BATCH):
        batch = new[i:i+BATCH]
        names = [p["name"] for p in batch]
        print(f"  Batch {i//BATCH + 1}: {names}")
        try:
            results = await generate_batch(batch, llm_client)
            for r, src in zip(results, batch):
                # Ensure required fields
                r.setdefault("id", to_snake(src["name"]))
                r.setdefault("english_name", src["name"])
                r.setdefault("sanskrit_name", src["sanskrit"])
                r.setdefault("category", infer_category(src["types"]))
                r.setdefault("level", src["level"])
                r.setdefault("image_url", src.get("img", ""))
                r["image_url"] = src.get("img", "") or r.get("image_url", "")

                # Add medical_conditions_beneficial from protocols
                pid = r["id"]
                r["medical_conditions_beneficial"] = sorted(set(pose_to_conditions.get(pid, [])))

                # Add medical_conditions_contraindicated from contra tags
                contra_conds: list[str] = []
                for tag in r.get("contraindications", []):
                    contra_conds.extend(tag_to_conditions.get(tag, []))
                r["medical_conditions_contraindicated"] = sorted(set(contra_conds))

                generated.append(r)
            print(f"    ✓ {len(results)} poses generated")
        except Exception as e:
            print(f"    ✗ Batch failed: {e}")
            # Add stub entries so we don't lose them silently
            for src in batch:
                stub = {
                    "id": to_snake(src["name"]),
                    "english_name": src["name"],
                    "sanskrit_name": src["sanskrit"],
                    "category": infer_category(src["types"]),
                    "level": src["level"],
                    "duration_seconds": {"beginner": 30, "intermediate": 45, "advanced": 60},
                    "primary_benefits": [],
                    "body_parts": [],
                    "instructions": [],
                    "dosha_balance": {"vata": "neutral", "pitta": "neutral", "kapha": "neutral"},
                    "contraindications": [],
                    "pregnancy_safe": True,
                    "goals": ["flexibility"],
                    "sequence_role": "main",
                    "pranayama_sync": "Breathe steadily.",
                    "ayurvedic_rationale": "",
                    "image_url": src.get("img", ""),
                    "medical_conditions_beneficial": [],
                    "medical_conditions_contraindicated": [],
                }
                generated.append(stub)

    # Merge into existing (skip duplicates)
    new_ids = {p["id"] for p in generated}
    merged = [p for p in existing if p["id"] not in new_ids] + generated
    merged.sort(key=lambda p: (p.get("category",""), p.get("english_name","")))

    POSES_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    print(f"\nDone. Total poses: {len(merged)} (was {len(existing)}, added {len(generated)})")


if __name__ == "__main__":
    asyncio.run(main())
