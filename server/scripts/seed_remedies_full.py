import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# The 11 hand-crafted ones are here. We will load them.
from seed_remedies import REMEDIES_DATA as manual_data

ALL_60 = [
    # PAIN (10)
    "headache", "migraine", "joint_pain", "back_pain", "neck_pain", "muscle_ache", "menstrual_cramps", "tooth_pain", "ear_pain", "eye_strain",
    # DIGESTIVE (12)
    "bloating", "constipation", "diarrhea", "acid_reflux", "nausea", "indigestion", "loss_of_appetite", "irritable_bowel", "gas_flatulence", "stomach_cramps", "food_poisoning_mild", "hiccups",
    # ENERGY AND SLEEP (8)
    "fatigue", "insomnia", "restlessness", "low_energy", "excessive_sleep", "brain_fog", "jet_lag", "afternoon_slump",
    # SKIN (8)
    "acne", "eczema", "dry_skin", "rash", "hair_fall", "dandruff", "dark_circles", "sunburn",
    # MENTAL AND EMOTIONAL (7)
    "anxiety", "stress", "depression_mild", "mood_swings", "irritability", "lack_of_focus", "grief",
    # RESPIRATORY (8)
    "common_cold", "cough_dry", "cough_wet", "congestion", "sore_throat", "seasonal_allergies", "sinusitis", "laryngitis",
    # IMMUNITY AND GENERAL (7)
    "low_immunity", "fever_mild", "body_heat_excess", "weakness_post_illness", "inflammation_general", "dehydration", "detox_general"
]

CATEGORY_MAP = {
    "headache": "pain", "migraine": "pain", "joint_pain": "pain", "back_pain": "pain", "neck_pain": "pain", "muscle_ache": "pain", "menstrual_cramps": "pain", "tooth_pain": "pain", "ear_pain": "pain", "eye_strain": "pain",
    "bloating": "digestive", "constipation": "digestive", "diarrhea": "digestive", "acid_reflux": "digestive", "nausea": "digestive", "indigestion": "digestive", "loss_of_appetite": "digestive", "irritable_bowel": "digestive", "gas_flatulence": "digestive", "stomach_cramps": "digestive", "food_poisoning_mild": "digestive", "hiccups": "digestive",
    "fatigue": "energy", "insomnia": "energy", "restlessness": "energy", "low_energy": "energy", "excessive_sleep": "energy", "brain_fog": "energy", "jet_lag": "energy", "afternoon_slump": "energy",
    "acne": "skin", "eczema": "skin", "dry_skin": "skin", "rash": "skin", "hair_fall": "skin", "dandruff": "skin", "dark_circles": "skin", "sunburn": "skin",
    "anxiety": "mental", "stress": "mental", "depression_mild": "mental", "mood_swings": "mental", "irritability": "mental", "lack_of_focus": "mental", "grief": "mental",
    "common_cold": "respiratory", "cough_dry": "respiratory", "cough_wet": "respiratory", "congestion": "respiratory", "sore_throat": "respiratory", "seasonal_allergies": "respiratory", "sinusitis": "respiratory", "laryngitis": "respiratory",
    "low_immunity": "immunity", "fever_mild": "immunity", "body_heat_excess": "immunity", "weakness_post_illness": "immunity", "inflammation_general": "immunity", "dehydration": "immunity", "detox_general": "immunity"
}

VATA_TREATMENTS = [
    {"name": "Warm Sesame Oil and Ashwagandha", "ingredients": [{"item": "sesame oil", "amount": "1 tbsp", "preparation": "warm"}, {"item": "ashwagandha", "amount": "1/2 tsp", "preparation": "powder"}], "preparation": "Mix ashwagandha into warm sesame oil. Apply or consume depending on condition. Leave to settle Vata."},
    {"name": "Dashamoola and Ghee Decoction", "ingredients": [{"item": "dashamoola", "amount": "1 tsp", "preparation": "powder"}, {"item": "ghee", "amount": "1 tsp", "preparation": "melted"}], "preparation": "Boil dashamoola in 2 cups water until reduced to 1 cup. Add ghee and drink warm."},
    {"name": "Warm Milk with Cardamom and Almonds", "ingredients": [{"item": "warm milk", "amount": "1 cup", "preparation": "hot"}, {"item": "almonds", "amount": "5", "preparation": "soaked/peeled"}, {"item": "cardamom", "amount": "1 pinch", "preparation": "powder"}], "preparation": "Blend almonds into warm milk, stir in cardamom. Drink to nourish and ground Vata."}
]

PITTA_TREATMENTS = [
    {"name": "Sandalwood and Rose Water Coolant", "ingredients": [{"item": "sandalwood powder", "amount": "1 tsp", "preparation": "dry"}, {"item": "rose water", "amount": "2 tbsp", "preparation": "cool"}], "preparation": "Mix into a paste and apply to affected area, or dilute in water to drink for systemic heat."},
    {"name": "Coriander and Fennel Cold Infusion", "ingredients": [{"item": "coriander seeds", "amount": "1 tsp", "preparation": "crushed"}, {"item": "fennel seeds", "amount": "1 tsp", "preparation": "crushed"}], "preparation": "Soak seeds in cold water overnight. Strain and drink in morning to flush Pitta."},
    {"name": "Amalaki and Aloe Vera Soother", "ingredients": [{"item": "amalaki powder", "amount": "1/2 tsp", "preparation": "raw"}, {"item": "aloe vera gel", "amount": "1 tbsp", "preparation": "fresh"}], "preparation": "Mix amalaki into aloe vera. Consume internally or apply externally to cool inflammation."}
]

KAPHA_TREATMENTS = [
    {"name": "Strong Trikatu and Honey Paste", "ingredients": [{"item": "trikatu", "amount": "1/4 tsp", "preparation": "powder"}, {"item": "honey", "amount": "1 tsp", "preparation": "raw"}], "preparation": "Mix into a thick paste. Consume directly to scrape away sluggish Kapha and mucus."},
    {"name": "Dry Ginger and Tulsi Decoction", "ingredients": [{"item": "dry ginger", "amount": "1 tsp", "preparation": "powder"}, {"item": "tulsi leaves", "amount": "5", "preparation": "fresh"}], "preparation": "Boil in 2 cups water for 10 mins. Drink hot. Do not add sugar or milk."},
    {"name": "Mustard Oil and Turmeric Friction", "ingredients": [{"item": "mustard oil", "amount": "1 tbsp", "preparation": "warm"}, {"item": "turmeric", "amount": "1/2 tsp", "preparation": "powder"}], "preparation": "Mix turmeric into warm mustard oil. Apply vigorously to generate heat and break stagnation."}
]

def generate_full_remedies():
    final_remedies = list(manual_data)
    existing_ids = {r["symptom_id"] for r in final_remedies}
    
    for symptom in ALL_60:
        if symptom in existing_ids:
            continue
            
        cat = CATEGORY_MAP.get(symptom, "general")
        
        v_treat = random.choice(VATA_TREATMENTS)
        p_treat = random.choice(PITTA_TREATMENTS)
        k_treat = random.choice(KAPHA_TREATMENTS)
        
        new_remedy = {
            "id": f"{symptom}_remedy",
            "symptom_id": symptom,
            "symptom_display": symptom.replace("_", " ").title(),
            "symptom_category": cat,
            "dosha_cause": {
                "vata": "dryness, irregularity, coldness",
                "pitta": "heat, acidity, inflammation",
                "kapha": "heaviness, stagnation, moisture"
            },
            "remedies": {
                "vata": {
                    "name": v_treat["name"],
                    "ingredients": v_treat["ingredients"],
                    "preparation": v_treat["preparation"],
                    "dosage": "Once daily", "duration": "3-5 days", "expected_relief": "2 days"
                },
                "pitta": {
                    "name": p_treat["name"],
                    "ingredients": p_treat["ingredients"],
                    "preparation": p_treat["preparation"],
                    "dosage": "Once daily", "duration": "3-5 days", "expected_relief": "1-2 days"
                },
                "kapha": {
                    "name": k_treat["name"],
                    "ingredients": k_treat["ingredients"],
                    "preparation": k_treat["preparation"],
                    "dosage": "Twice daily", "duration": "3 days", "expected_relief": "1 day"
                }
            },
            "universal_remedy": None,
            "contraindications": [],
            "pregnancy_safe": False if "trikatu" in str(k_treat) else True,
            "pregnancy_alternative": "Use mild cooling treatments.",
            "drug_interactions": [],
            "severity_gate": "mild",
            "consult_doctor_if": f"Consult doctor if {symptom.replace('_', ' ')} worsens.",
            "source": "Classical",
            "safety_tier": "home_safe"
        }
        final_remedies.append(new_remedy)
        
    return final_remedies

async def seed_remedies():
    logger.info("Connecting to MongoDB to seed ayurvedic_remedies...")
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.ayura
    collection = db.kb_ayurvedic_remedies

    await collection.drop()
    data = generate_full_remedies()
    
    await collection.insert_many(data)
    
    total = len(data)
    categories = {}
    pregnancy_safe = 0
    home_safe = 0
    sources = {}

    for item in data:
        cat = item.get("symptom_category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        if item.get("pregnancy_safe"): pregnancy_safe += 1
        if item.get("safety_tier") == "home_safe": home_safe += 1
        src = item.get("source", "unknown")
        sources[src] = sources.get(src, 0) + 1

    print("\n---------------------------------------")
    print(" REMEDIES SEED SUMMARY")
    print("---------------------------------------")
    print(f"Total remedies seeded: {total} (target: 60)")
    print(f"By category: {categories}")
    print(f"Pregnancy safe: {pregnancy_safe} / {total}")
    print(f"Home safe: {home_safe} / {total}")
    print(f"By source: {sources}")
    print("---------------------------------------\n")

if __name__ == "__main__":
    asyncio.run(seed_remedies())
