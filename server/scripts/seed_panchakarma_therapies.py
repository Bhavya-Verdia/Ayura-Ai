import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "knowledge_base"
OUTPUT_FILE = OUTPUT_DIR / "panchakarma_therapies.json"

THERAPIES = [
    # PURVAKARMA (PREP)
    {
        "id": "abhyanga_self",
        "name": "Self-Abhyanga (Warm Oil Massage)",
        "phase": "purvakarma",
        "setting_required": ["home", "clinic", "both"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": 1},
        "duration_minutes": 15,
        "experience_required": "none",
        "diet_strictness": "lifestyle_only",
        "herb_requirement": "readily_available",
        "benefits": ["Relieves fatigue", "Pacifies Vata", "Improves sleep"]
    },
    {
        "id": "abhyanga_clinic",
        "name": "Clinical Abhyanga (2-Therapist Sync)",
        "phase": "purvakarma",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": -1, "pitta": 0, "kapha": 1},
        "duration_minutes": 60,
        "experience_required": "none",
        "diet_strictness": "partial",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Deep tissue release", "Mobilizes toxins"]
    },
    {
        "id": "swedana_home",
        "name": "Home Steam Therapy (Swedana)",
        "phase": "purvakarma",
        "setting_required": ["home", "clinic", "both"],
        "dosha_effect": {"vata": -1, "pitta": 1, "kapha": -1},
        "duration_minutes": 15,
        "experience_required": "none",
        "diet_strictness": "lifestyle_only",
        "herb_requirement": "readily_available",
        "benefits": ["Opens pores", "Liquefies toxins"]
    },
    {
        "id": "bashpa_sweda_clinic",
        "name": "Clinical Herbal Steam (Bashpa Sweda)",
        "phase": "purvakarma",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": -1, "pitta": 1, "kapha": -1},
        "duration_minutes": 30,
        "experience_required": "none",
        "diet_strictness": "partial",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Deep vasodilation", "Cellular toxin release"]
    },
    {
        "id": "snehapana_home",
        "name": "Mild Internal Oleation (Ghee Intake)",
        "phase": "purvakarma",
        "setting_required": ["home", "both"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": 1},
        "duration_minutes": 5,
        "experience_required": "some",
        "diet_strictness": "strict",
        "herb_requirement": "readily_available",
        "benefits": ["Lubricates GI tract", "Binds fat-soluble toxins"]
    },
    {
        "id": "snehapana_clinic",
        "name": "Intensive Internal Oleation",
        "phase": "purvakarma",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": 1},
        "duration_minutes": 5,
        "experience_required": "experienced",
        "diet_strictness": "strict",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Deep cellular binding of ama"]
    },
    {
        "id": "shirodhara",
        "name": "Shirodhara (Warm Oil on Forehead)",
        "phase": "purvakarma",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": 1},
        "duration_minutes": 45,
        "experience_required": "none",
        "diet_strictness": "partial",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Profound stress relief", "Balances nervous system"]
    },
    {
        "id": "udvartana",
        "name": "Udvartana (Dry Herbal Powder Massage)",
        "phase": "purvakarma",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": 1, "pitta": 0, "kapha": -1},
        "duration_minutes": 45,
        "experience_required": "none",
        "diet_strictness": "partial",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Reduces cellulite", "Stimulates lymphatic system", "Pacifies Kapha"]
    },
    {
        "id": "udvartana_home",
        "name": "Dry Brushing (Garshana)",
        "phase": "purvakarma",
        "setting_required": ["home", "both"],
        "dosha_effect": {"vata": 1, "pitta": 0, "kapha": -1},
        "duration_minutes": 10,
        "experience_required": "none",
        "diet_strictness": "lifestyle_only",
        "herb_requirement": "readily_available",
        "benefits": ["Lymphatic drainage", "Invigorating"]
    },
    
    # PRADHANA KARMA (MAIN CLEANSING)
    {
        "id": "vamana",
        "name": "Vamana (Therapeutic Emesis)",
        "phase": "pradhana",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": 0, "pitta": 0, "kapha": -1},
        "duration_minutes": 120,
        "experience_required": "experienced",
        "diet_strictness": "strict",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Expels deep-rooted Kapha toxins from stomach"]
    },
    {
        "id": "virechana_clinic",
        "name": "Virechana (Clinical Purgation)",
        "phase": "pradhana",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": 0, "pitta": -1, "kapha": 0},
        "duration_minutes": 180,
        "experience_required": "some",
        "diet_strictness": "strict",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Clears Pitta toxins from liver and small intestine"]
    },
    {
        "id": "virechana_home",
        "name": "Mild Mild Laxative Therapy (Triphala/Castor)",
        "phase": "pradhana",
        "setting_required": ["home", "both"],
        "dosha_effect": {"vata": 0, "pitta": -1, "kapha": 0},
        "duration_minutes": 5,
        "experience_required": "some",
        "diet_strictness": "strict",
        "herb_requirement": "readily_available",
        "benefits": ["Gentle bowel cleanse", "Safe for home use"]
    },
    {
        "id": "basti_niruha",
        "name": "Niruha Basti (Decoction Enema)",
        "phase": "pradhana",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": -1, "pitta": 0, "kapha": 0},
        "duration_minutes": 45,
        "experience_required": "some",
        "diet_strictness": "strict",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Clears Vata from colon", "Systemic detox"]
    },
    {
        "id": "basti_anuvasana",
        "name": "Anuvasana Basti (Oil Enema)",
        "phase": "pradhana",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": -1, "pitta": 0, "kapha": 0},
        "duration_minutes": 30,
        "experience_required": "some",
        "diet_strictness": "strict",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Nourishes colon", "Pacifies severe Vata"]
    },
    {
        "id": "basti_home",
        "name": "Mild Oil Matra Basti (Home Enema)",
        "phase": "pradhana",
        "setting_required": ["home", "both"],
        "dosha_effect": {"vata": -1, "pitta": 0, "kapha": 0},
        "duration_minutes": 30,
        "experience_required": "experienced",
        "diet_strictness": "strict",
        "herb_requirement": "readily_available",
        "benefits": ["Vata management at home"]
    },
    {
        "id": "nasya_clinic",
        "name": "Clinical Nasya (Nasal Administration)",
        "phase": "pradhana",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "duration_minutes": 30,
        "experience_required": "some",
        "diet_strictness": "partial",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Clears head and neck toxins", "Improves mental clarity"]
    },
    {
        "id": "nasya_home",
        "name": "Pratimarsha Nasya (Daily Nasal Drops)",
        "phase": "pradhana",
        "setting_required": ["home", "both"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "duration_minutes": 5,
        "experience_required": "none",
        "diet_strictness": "lifestyle_only",
        "herb_requirement": "readily_available",
        "benefits": ["Protects nasal passages", "Mild clearance"]
    },
    {
        "id": "raktamokshana",
        "name": "Raktamokshana (Bloodletting/Leech)",
        "phase": "pradhana",
        "setting_required": ["clinic"],
        "dosha_effect": {"vata": 0, "pitta": -1, "kapha": 0},
        "duration_minutes": 60,
        "experience_required": "experienced",
        "diet_strictness": "strict",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Extracts deep Pitta toxins from blood"]
    },
    
    # PASCHAT KARMA (POST/REJUVENATION)
    {
        "id": "samsarjana_krama_strict",
        "name": "Strict Samsarjana Krama (Dietary Re-entry)",
        "phase": "paschat",
        "setting_required": ["clinic", "both"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "duration_minutes": 0,
        "experience_required": "some",
        "diet_strictness": "strict",
        "herb_requirement": "readily_available",
        "benefits": ["Reignites Agni safely after deep cleanse"]
    },
    {
        "id": "samsarjana_krama_mild",
        "name": "Mild Kitchari Mono-diet",
        "phase": "paschat",
        "setting_required": ["home", "both", "clinic"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "duration_minutes": 0,
        "experience_required": "none",
        "diet_strictness": "partial",
        "herb_requirement": "readily_available",
        "benefits": ["Gives digestion a rest", "Nourishing"]
    },
    {
        "id": "rasayana_herbs",
        "name": "Rasayana Herb Integration",
        "phase": "paschat",
        "setting_required": ["home", "clinic", "both"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "duration_minutes": 5,
        "experience_required": "none",
        "diet_strictness": "lifestyle_only",
        "herb_requirement": "specific_ayurvedic",
        "benefits": ["Tissue rejuvenation", "Immunity building"]
    },
    {
        "id": "yoga_nidra",
        "name": "Yoga Nidra (Deep Relaxation)",
        "phase": "paschat",
        "setting_required": ["home", "clinic", "both"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": 0},
        "duration_minutes": 30,
        "experience_required": "none",
        "diet_strictness": "lifestyle_only",
        "herb_requirement": "readily_available",
        "benefits": ["Nervous system reset", "Integration of detox"]
    },
    {
        "id": "gentle_pranayama",
        "name": "Rejuvenative Pranayama (Anulom Vilom)",
        "phase": "paschat",
        "setting_required": ["home", "clinic", "both"],
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "duration_minutes": 15,
        "experience_required": "none",
        "diet_strictness": "lifestyle_only",
        "herb_requirement": "readily_available",
        "benefits": ["Restores Prana", "Balances nadis"]
    }
]

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(THERAPIES, f, indent=2, ensure_ascii=False)
        
    print(f"Total therapies seeded: {len(THERAPIES)}")
    for t in ["purvakarma", "pradhana", "paschat"]:
        count = len([x for x in THERAPIES if x["phase"] == t])
        print(f"  {t}: {count}")

if __name__ == "__main__":
    main()
