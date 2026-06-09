import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "knowledge_base"
OUTPUT_FILE = OUTPUT_DIR / "ayurvedic_remedies.json"

REMEDIES = [
    # HOME REMEDIES (KITCHEN SPICES)
    {
        "id": "ginger_honey_tea",
        "name": "Ginger & Honey Tea",
        "type": "home_remedy",
        "dosha_effect": {"vata": -1, "pitta": 1, "kapha": -1},
        "indications": ["cold", "cough", "congestion", "indigestion", "nausea"],
        "contraindications": ["acidity", "ulcers"],
        "pregnancy_safe": True,
        "ingredient_access_required": "kitchen_only",
        "taste_profile": ["pungent", "sweet"],
        "preparation_method": "Grate 1 inch ginger, boil in 1 cup water for 5 mins. Strain, let cool slightly, and add 1 tsp raw honey."
    },
    {
        "id": "ccf_tea",
        "name": "CCF Tea (Cumin, Coriander, Fennel)",
        "type": "home_remedy",
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1}, # Tridoshic
        "indications": ["indigestion", "bloating", "gas", "detox", "water_retention"],
        "contraindications": [],
        "pregnancy_safe": True,
        "ingredient_access_required": "kitchen_only",
        "taste_profile": ["sweet", "bitter", "pungent"],
        "preparation_method": "Boil 1/2 tsp each of cumin, coriander, and fennel seeds in 2 cups of water. Simmer for 10 mins. Strain and drink warm."
    },
    {
        "id": "turmeric_milk",
        "name": "Golden Milk (Haldi Doodh)",
        "type": "home_remedy",
        "dosha_effect": {"vata": -1, "pitta": 0, "kapha": -1},
        "indications": ["joint_pain", "inflammation", "insomnia", "immunity", "cough"],
        "contraindications": ["severe_pitta_imbalance"],
        "pregnancy_safe": True,
        "ingredient_access_required": "kitchen_only",
        "taste_profile": ["bitter", "astringent", "sweet"],
        "preparation_method": "Heat 1 cup milk (or plant milk) with 1/2 tsp turmeric powder, a pinch of black pepper, and a pinch of cardamom. Do not boil vigorously."
    },
    {
        "id": "ajwain_water",
        "name": "Ajwain (Carom) Water",
        "type": "home_remedy",
        "dosha_effect": {"vata": -1, "pitta": 1, "kapha": -1},
        "indications": ["severe_bloating", "gas", "stomach_ache", "cramps"],
        "contraindications": ["acidity", "hyperacidity"],
        "pregnancy_safe": False, # Often avoided in high amounts during early pregnancy due to heating nature
        "ingredient_access_required": "kitchen_only",
        "taste_profile": ["pungent", "bitter"],
        "preparation_method": "Boil 1 tsp of ajwain seeds in 1 cup of water until it reduces by half. Drink warm."
    },
    {
        "id": "ghee_warm_water",
        "name": "Warm Water with Ghee",
        "type": "home_remedy",
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": 1},
        "indications": ["constipation", "dry_skin", "dry_joints", "vata_imbalance"],
        "contraindications": ["high_cholesterol", "severe_kapha", "obesity"],
        "pregnancy_safe": True,
        "ingredient_access_required": "kitchen_only",
        "taste_profile": ["sweet"],
        "preparation_method": "Melt 1 tsp of pure cow ghee in a cup of warm water. Drink first thing in the morning on an empty stomach."
    },
    {
        "id": "fennel_chew",
        "name": "Roasted Fennel Seeds",
        "type": "home_remedy",
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "indications": ["acidity", "indigestion", "bad_breath"],
        "contraindications": [],
        "pregnancy_safe": True,
        "ingredient_access_required": "kitchen_only",
        "taste_profile": ["sweet"],
        "preparation_method": "Dry roast fennel seeds. Chew 1 tsp thoroughly after meals."
    },
    {
        "id": "clove_oil_cotton",
        "name": "Clove on Cotton",
        "type": "home_remedy",
        "dosha_effect": {"vata": -1, "pitta": 1, "kapha": -1},
        "indications": ["toothache", "gum_pain"],
        "contraindications": [],
        "pregnancy_safe": True,
        "ingredient_access_required": "kitchen_only",
        "taste_profile": ["pungent"],
        "preparation_method": "Bite down gently on a whole clove near the affected tooth, or apply 1 drop of clove oil to a cotton swab and place on the tooth."
    },

    # CLINICAL MEDICINES (CLASSIC AYURVEDIC FORMULATIONS)
    {
        "id": "ashwagandha_churna",
        "name": "Ashwagandha Churna",
        "type": "clinical_medicine",
        "dosha_effect": {"vata": -1, "pitta": 1, "kapha": -1},
        "indications": ["stress", "anxiety", "insomnia", "fatigue", "weakness", "muscle_building"],
        "contraindications": ["excess_pitta", "ama_toxicity"],
        "pregnancy_safe": False,
        "ingredient_access_required": "can_buy_herbs",
        "taste_profile": ["bitter", "astringent", "sweet"],
        "preparation_method": "Take 1/2 tsp powder mixed with warm milk and a pinch of cardamom before bed."
    },
    {
        "id": "triphala_churna",
        "name": "Triphala Churna",
        "type": "clinical_medicine",
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "indications": ["constipation", "indigestion", "eye_health", "detox", "bloating"],
        "contraindications": ["diarrhea", "dysentery"],
        "pregnancy_safe": False,
        "ingredient_access_required": "can_buy_herbs",
        "taste_profile": ["bitter", "astringent", "sweet", "sour", "pungent"],
        "preparation_method": "Take 1 tsp with warm water at bedtime for bowel regulation, or with honey/ghee for rejuvenation."
    },
    {
        "id": "shatavari_churna",
        "name": "Shatavari Churna",
        "type": "clinical_medicine",
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": 1},
        "indications": ["hormonal_imbalance", "pms", "menopause", "acidity", "ulcers", "fatigue"],
        "contraindications": ["high_kapha", "congestion"],
        "pregnancy_safe": True, # One of the few safe clinical herbs
        "ingredient_access_required": "can_buy_herbs",
        "taste_profile": ["sweet", "bitter"],
        "preparation_method": "Take 1 tsp mixed with warm milk or ghee, twice a day."
    },
    {
        "id": "brahmi_vati",
        "name": "Brahmi Vati / Powder",
        "type": "clinical_medicine",
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "indications": ["memory", "focus", "anxiety", "adhd", "stress", "hair_fall"],
        "contraindications": ["severe_bradycardia"],
        "pregnancy_safe": False,
        "ingredient_access_required": "can_buy_herbs",
        "taste_profile": ["bitter", "astringent"],
        "preparation_method": "Take 1/2 tsp powder with warm water or ghee, or 1 tablet twice a day."
    },
    {
        "id": "guggulu_kanchanar",
        "name": "Kanchanar Guggulu",
        "type": "clinical_medicine",
        "dosha_effect": {"vata": 0, "pitta": 0, "kapha": -1},
        "indications": ["thyroid", "lymphatic_swelling", "pcos", "cysts"],
        "contraindications": ["pregnancy", "thinning_blood"],
        "pregnancy_safe": False,
        "ingredient_access_required": "can_buy_herbs",
        "taste_profile": ["bitter", "pungent", "astringent"],
        "preparation_method": "Take 2 tablets twice a day after meals with warm water."
    },
    {
        "id": "sitopaladi_churna",
        "name": "Sitopaladi Churna",
        "type": "clinical_medicine",
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "indications": ["cough", "cold", "bronchitis", "asthma", "fever"],
        "contraindications": ["diabetes"], # Contains rock sugar
        "pregnancy_safe": True,
        "ingredient_access_required": "can_buy_herbs",
        "taste_profile": ["sweet", "pungent"],
        "preparation_method": "Mix 1 tsp powder with 1 tsp honey to make a paste. Lick slowly 3-4 times a day."
    },
    {
        "id": "haridrakhand",
        "name": "Haridrakhandam",
        "type": "clinical_medicine",
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "indications": ["allergies", "hives", "skin_rash", "chronic_cold", "immunity"],
        "contraindications": ["diabetes"], # Contains sugar
        "pregnancy_safe": False,
        "ingredient_access_required": "can_buy_herbs",
        "taste_profile": ["sweet", "bitter", "pungent"],
        "preparation_method": "Take 1 tsp with warm water or milk twice a day."
    },
    {
        "id": "amla_juice",
        "name": "Amla Juice / Churna",
        "type": "clinical_medicine",
        "dosha_effect": {"vata": -1, "pitta": -1, "kapha": -1},
        "indications": ["hair_fall", "acidity", "immunity", "eye_health", "skin_aging", "diabetes"],
        "contraindications": ["severe_cold"],
        "pregnancy_safe": True,
        "ingredient_access_required": "can_buy_herbs",
        "taste_profile": ["sour", "astringent"],
        "preparation_method": "Take 20ml fresh juice with water on an empty stomach, or 1 tsp powder with warm water."
    }
]

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(REMEDIES, f, indent=2, ensure_ascii=False)
        
    print(f"Total remedies seeded: {len(REMEDIES)}")
    for t in ["home_remedy", "clinical_medicine"]:
        count = len([x for x in REMEDIES if x["type"] == t])
        print(f"  {t}: {count}")

if __name__ == "__main__":
    main()
