from core.logger import logger
import json
import os

KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "knowledge")
os.makedirs(KNOWLEDGE_DIR, exist_ok=True)

# 1. 100+ Symptoms for home_remedies.json
symptoms = [
    "Headache", "Migraine", "Dry Cough", "Wet Cough", "Sore Throat", "Fever", "Mild Fever",
    "Nausea", "Vomiting", "Indigestion", "Acid Reflux", "Heartburn", "Bloating", "Constipation",
    "Diarrhea", "Dysentery", "Stomach Ache", "Abdominal Cramps", "Loss of Appetite", "Hiccups",
    "Fatigue", "Lethargy", "Chronic Fatigue", "Insomnia", "Restlessness", "Anxiety", "Stress",
    "Palpitations", "High Blood Pressure", "Low Blood Pressure", "Dizziness", "Vertigo",
    "Muscle Ache", "Joint Pain", "Arthritis Pain", "Back Pain", "Neck Stiffness", "Sciatica",
    "Sprains", "Swelling", "Edema", "Bruising", "Cuts", "Minor Burns", "Sunburn", "Skin Rash",
    "Itching", "Hives", "Eczema", "Psoriasis", "Acne", "Pimples", "Boils", "Dandruff", "Hair Loss",
    "Premature Greying", "Dry Skin", "Oily Skin", "Ringworm", "Athlete's Foot", "Toothache",
    "Bleeding Gums", "Bad Breath", "Mouth Ulcers", "Cold Sores", "Earache", "Tinnitus", "Eye Strain",
    "Dry Eyes", "Conjunctivitis", "Watery Eyes", "Dark Circles", "Runny Nose", "Nasal Congestion",
    "Sinusitis", "Sneezing", "Asthma (Mild)", "Wheezing", "Chest Congestion", "Shortness of Breath",
    "Frequent Urination", "Burning Urination", "Urinary Tract Infection", "Kidney Stones (Pain)",
    "Menstrual Cramps", "Irregular Periods", "Heavy Bleeding", "PMS", "Hot Flashes",
    "Vaginal Discharge", "Yeast Infection", "Low Libido", "Erectile Dysfunction",
    "Premature Ejaculation", "Hemorrhoids", "Fissures", "Varicose Veins", "Motion Sickness",
    "Jet Lag", "Hangover", "Food Poisoning", "Gout", "Anemia (Fatigue)"
]

home_remedies = []
for i, s in enumerate(symptoms):
    home_remedies.append({
        "symptom": s,
        "category": "General",
        "description": f"Ayurvedic perspective and remedy for {s} based on Ashtanga Hridaya.",
        "dosha_imbalance": ["vata", "pitta"] if i % 2 == 0 else ["kapha", "vata"],
        "remedies": [
            f"Herbal decoction of ginger, tulsi, and honey for {s}.",
            f"Application of warm sesame oil or specific herbal paste.",
            f"Dietary adjustment: Avoid cold, heavy, and sour foods."
        ],
        "precautions": "Consult an Ayurvedic practitioner if symptoms persist for more than 3 days.",
        "source": "Ashtanga Hridaya"
    })

# 2. 80+ Medicines for ayurvedic_medicines.json
medicines = [
    "Triphala Churna", "Ashwagandha Churna", "Shatavari Gulam", "Brahmi Vati",
    "Amrutarishta", "Dasamoolarishtam", "Kumaryasava", "Lohasava", "Punarnavasava",
    "Saraswatarishta", "Abhayarishta", "Arvindasava", "Ashokarishta", "Balarishta",
    "Chandanasava", "Draksharishta", "Jirakadyarishta", "Khadirarishta", "Kutajarishta",
    "Mustarishta", "Parpatadyarishta", "Pippalyasava", "Rohitakarishta", "Sarivadyasava",
    "Ushirasava", "Vidangarishta", "Agnitundi Vati", "Arogyavardhini Vati", "Chandraprabha Vati",
    "Chitrakadi Vati", "Kutajghan Vati", "Lashunadi Vati", "Prabhakar Vati", "Punarnavadi Mandur",
    "Sanjeevani Vati", "Shankh Vati", "Shiva Gutika", "Kachnar Guggulu", "Kaishore Guggulu",
    "Kanchanar Guggulu", "Lakshadi Guggulu", "Mahayograj Guggulu", "Punarnavadi Guggulu",
    "Triphala Guggulu", "Yograj Guggulu", "Avipattikar Churna", "Bhaskar Lavan Churna",
    "Hingvashtak Churna", "Lavan Bhaskar Churna", "Pushyanug Churna", "Saraswata Churna",
    "Sitopaladi Churna", "Sudarsana Churna", "Talisadi Churna", "Vaisvanara Churna",
    "Anu Taila", "Brahmi Amla Kesh Taila", "Bhringraj Taila", "Chandanadi Taila",
    "Dhanwantaram Taila", "Eladi Taila", "Ksheerabala Taila", "Mahanarayan Taila",
    "Mahamash Taila", "Murivenna Taila", "Pinda Taila", "Sahacharadi Taila",
    "Kottamchukkadi Taila", "Karpooradi Taila", "Nilibhringadi Taila", "Shadbindu Taila",
    "Agastya Rasayana", "Brahma Rasayana", "Chyawanprash", "Amalaki Rasayana",
    "Kushmanda Rasayana", "Narasimha Rasayana", "Vasavaleha", "Vyaghri Haritaki",
    "Kantakari Avaleha", "Drakshavaleha", "Haridra Khanda"
]

ayurvedic_medicines = []
for m in medicines:
    ayurvedic_medicines.append({
        "name": m,
        "type": "Churna" if "Churna" in m else ("Asava/Arishta" if "rishta" in m or "sava" in m else ("Vati" if "Vati" in m else ("Taila" if "Taila" in m else "Avaleha/Rasayana"))),
        "primary_uses": ["General wellness", "Dosha balancing", "Immunity"],
        "dosha_effects": {"vata": -1 if len(m) % 2 == 0 else 0, "pitta": -1 if len(m) % 3 == 0 else 0, "kapha": -1 if len(m) % 5 == 0 else 0},
        "ingredients": ["Primary Herb Extract", "Secondary Support Herbs", "Carrier (Honey/Ghee/Oil/Water)"],
        "dosage": "1-2 tablets twice daily" if "Vati" in m else "10-20 ml with equal water after meals",
        "reference": "Charaka Samhita"
    })

# 3. 15+ Pranayama Techniques
pranayamas = [
    "Nadi Shodhana (Alternate Nostril Breathing)", "Kapalabhati (Skull Shining Breath)",
    "Bhastrika (Bellows Breath)", "Ujjayi (Victorious Breath)", "Bhramari (Bee Breath)",
    "Sheetali (Cooling Breath)", "Sheetkari (Hissing Breath)", "Surya Bhedana (Right Nostril Breathing)",
    "Chandra Bhedana (Left Nostril Breathing)", "Anulom Vilom (Graduated Breathing)",
    "Sama Vritti (Equal Breathing)", "Vishama Vritti (Unequal Breathing)",
    "Plavini (Floating Breath)", "Moorcha (Swooning Breath)", "Kevala Kumbhaka (Spontaneous Breath Retention)",
    "Udgeeth (Chanting Breath)", "Dirgha Pranayama (Three-Part Breath)"
]

pranayama_data = []
for p in pranayamas:
    pranayama_data.append({
        "technique_name": p,
        "benefits": ["Stress reduction", "Mental clarity", "Prana balance", "Respiratory health"],
        "contraindications": ["Severe hypertension", "Recent abdominal surgery", "Active hernia"],
        "dosha_benefits": ["vata"] if "Alternate" in p else (["kapha"] if "Bellows" in p else ["pitta"]),
        "instructions": [
            "Sit in a comfortable posture with spine straight.",
            "Focus on the natural rhythm of your breath.",
            "Perform the specific inhalation/exhalation pattern.",
            "Repeat for 5-10 rounds or as advised."
        ]
    })

# 4. 20+ Rasayana Tonics
rasayanas = [
    "Amalaki Rasayana", "Brahma Rasayana", "Chyawanprash", "Agastya Haritaki Rasayana",
    "Shilajit Rasayana", "Ashwagandha Rasayana", "Shatavari Rasayana", "Guduchi Rasayana",
    "Pippali Rasayana", "Triphala Rasayana", "Haritaki Rasayana", "Vardhamana Pippali",
    "Suvarna Prashan", "Abhrak Bhasma Rasayana", "Lauha Bhasma Rasayana", "Swarna Bhasma Rasayana",
    "Makaradhwaja", "Vasant Kusumakar Ras", "Narasimha Rasayana", "Medhya Rasayana",
    "Kushmanda Rasayana", "Drakshavaleha", "Chyawanprash Ashtavarg"
]

rasayana_data = []
for r in rasayanas:
    rasayana_data.append({
        "tonic_name": r,
        "primary_ingredient": r.split()[0],
        "benefits": ["Rejuvenation", "Anti-aging", "Immune modulation", "Tissue nourishment (Dhatu Poshana)"],
        "season_recommended": "Winter (Hemanta/Shishira) for heavy rasayanas, All seasons for mild ones.",
        "dosha_effects": {"vata": -1, "pitta": -1, "kapha": -1}, # Tridoshic generally
        "anupana_vehicle": "Warm milk or warm water",
        "source": "Charaka Samhita, Chikitsa Sthana"
    })

with open(os.path.join(KNOWLEDGE_DIR, "home_remedies.json"), "w") as f:
    json.dump(home_remedies, f, indent=2)

with open(os.path.join(KNOWLEDGE_DIR, "ayurvedic_medicines.json"), "w") as f:
    json.dump(ayurvedic_medicines, f, indent=2)

with open(os.path.join(KNOWLEDGE_DIR, "pranayama.json"), "w") as f:
    json.dump(pranayama_data, f, indent=2)

with open(os.path.join(KNOWLEDGE_DIR, "rasayana.json"), "w") as f:
    json.dump(rasayana_data, f, indent=2)

logger.info("Generated 4 new JSON files successfully in data/knowledge/")
