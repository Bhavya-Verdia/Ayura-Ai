"""
Ayura AI - Synthetic Training Data Generator
Generates labelled data for all 6 ML models using Ayurvedic rules.
"""

import json
import random
import numpy as np
import pandas as pd
from pathlib import Path

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent.parent / "server" / "ml" / "training_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────
# 1. DOSHA CLASSIFIER TRAINING DATA
# ─────────────────────────────────────────
def generate_dosha_data(n: int = 5000) -> pd.DataFrame:
    """
    Generate synthetic dosha quiz answers with known dosha labels.
    20 questions (Q1-Q7: body/kapha, Q8-Q14: digestion/pitta, Q15-Q20: mind/vata)
    Answer scale: 1=strongly vata, 3=neutral, 5=strongly kapha
    """
    records = []
    for _ in range(n):
        dosha = random.choices(["vata", "pitta", "kapha"], weights=[0.35, 0.35, 0.30])[0]
        answers = []
        for q in range(20):
            # Bias answers toward dominant dosha with noise
            if dosha == "vata":
                base = 1.8 if q < 14 else 2.0
            elif dosha == "pitta":
                base = 3.0
            else:
                base = 4.2 if q < 14 else 3.8

            answer = int(np.clip(np.random.normal(base, 0.9), 1, 5))
            answers.append(answer)

        records.append({"answers": answers, "label": dosha})

    df = pd.DataFrame(records)
    df.to_json(OUTPUT_DIR / "dosha_training.json", orient="records")
    print(f"✅ Dosha data: {len(df)} records")
    return df


# ─────────────────────────────────────────
# 2. HEALTH RISK PREDICTOR TRAINING DATA
# ─────────────────────────────────────────
def generate_health_risk_data(n: int = 3000) -> pd.DataFrame:
    """
    Features: bmi, age, gender, dosha, activity_level
    Labels: probabilities for [acid_reflux, joint_pain, inflammation, diabetes_risk, hypertension_risk]
    """
    records = []
    for _ in range(n):
        bmi = round(random.uniform(17, 42), 1)
        age = random.randint(18, 70)
        gender = random.choice(["male", "female"])
        dosha = random.choice(["vata", "pitta", "kapha"])
        activity = random.choice(["sedentary", "light", "moderate", "active"])

        # Rule-based risk calculation
        acid_reflux = 0.1
        if dosha == "pitta": acid_reflux += 0.35
        if bmi > 27: acid_reflux += 0.15
        acid_reflux = min(0.95, acid_reflux + random.gauss(0, 0.08))

        joint_pain = 0.05
        if dosha == "vata": joint_pain += 0.30
        if age > 45: joint_pain += 0.20
        if bmi > 30: joint_pain += 0.15
        joint_pain = min(0.95, joint_pain + random.gauss(0, 0.08))

        inflammation = 0.1
        if dosha == "pitta": inflammation += 0.25
        if bmi > 30: inflammation += 0.25
        if activity == "sedentary": inflammation += 0.15
        inflammation = min(0.95, inflammation + random.gauss(0, 0.08))

        diabetes_risk = 0.05
        if bmi > 28: diabetes_risk += 0.20
        if activity == "sedentary": diabetes_risk += 0.15
        if dosha == "kapha": diabetes_risk += 0.15
        if age > 40: diabetes_risk += 0.10
        diabetes_risk = min(0.95, diabetes_risk + random.gauss(0, 0.05))

        hypertension_risk = 0.05
        if bmi > 30: hypertension_risk += 0.20
        if activity == "sedentary": hypertension_risk += 0.10
        if age > 45: hypertension_risk += 0.15
        if gender == "male": hypertension_risk += 0.05
        hypertension_risk = min(0.95, hypertension_risk + random.gauss(0, 0.05))

        records.append({
            "bmi": bmi, "age": age,
            "gender_male": 1 if gender == "male" else 0,
            "dosha_vata": 1 if dosha == "vata" else 0,
            "dosha_pitta": 1 if dosha == "pitta" else 0,
            "dosha_kapha": 1 if dosha == "kapha" else 0,
            "activity_sedentary": 1 if activity == "sedentary" else 0,
            "activity_moderate": 1 if activity == "moderate" else 0,
            "acid_reflux_risk": round(max(0, acid_reflux), 3),
            "joint_pain_risk": round(max(0, joint_pain), 3),
            "inflammation_risk": round(max(0, inflammation), 3),
            "diabetes_risk": round(max(0, diabetes_risk), 3),
            "hypertension_risk": round(max(0, hypertension_risk), 3),
        })

    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_DIR / "health_risk_training.csv", index=False)
    print(f"✅ Health risk data: {len(df)} records")
    return df


# ─────────────────────────────────────────
# 3. SYMPTOM→CONDITION MAPPER TRAINING DATA
# ─────────────────────────────────────────
SYMPTOM_CONDITION_MAP = {
    "pitta_aggravation": ["acidity", "heartburn", "skin_rash", "excessive_sweating", "anger", "inflammation"],
    "vata_aggravation": ["anxiety", "insomnia", "constipation", "joint_pain", "bloating", "dry_skin"],
    "kapha_aggravation": ["weight_gain", "lethargy", "congestion", "depression", "edema", "slow_digestion"],
    "ama_accumulation": ["constipation", "bloating", "fatigue", "coated_tongue", "brain_fog", "body_odor"],
    "pitta_pachaka_imbalance": ["acid_reflux", "ulcers", "IBS_diarrhea", "irritable_bowel"],
}

def generate_symptom_data(n: int = 2000) -> pd.DataFrame:
    all_symptoms = list({s for symptoms in SYMPTOM_CONDITION_MAP.values() for s in symptoms})
    records = []
    for _ in range(n):
        condition = random.choice(list(SYMPTOM_CONDITION_MAP.keys()))
        true_symptoms = SYMPTOM_CONDITION_MAP[condition]

        # Pick 2-5 symptoms from the condition's symptom set + 0-2 noise symptoms
        active = random.sample(true_symptoms, min(random.randint(2, 4), len(true_symptoms)))
        noise = random.sample([s for s in all_symptoms if s not in true_symptoms], random.randint(0, 2))

        symptom_vector = {s: 1 if s in active else 0 for s in all_symptoms}
        symptom_vector["label"] = condition
        records.append(symptom_vector)

    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_DIR / "symptom_condition_training.csv", index=False)
    print(f"✅ Symptom-condition data: {len(df)} records")
    return df


# ─────────────────────────────────────────
# 4. EXERCISE RECOMMENDER DATA (Content-based vectors)
# ─────────────────────────────────────────
EXERCISES = [
    {"name": "Swimming", "impact": 1, "intensity": 3, "vata_score": 0.9, "pitta_score": 0.95, "kapha_score": 0.7, "joint_friendly": 1, "cardio": 1, "strength": 0},
    {"name": "Walking", "impact": 1, "intensity": 2, "vata_score": 0.85, "pitta_score": 0.8, "kapha_score": 0.6, "joint_friendly": 1, "cardio": 1, "strength": 0},
    {"name": "Cycling", "impact": 1, "intensity": 3, "vata_score": 0.75, "pitta_score": 0.85, "kapha_score": 0.75, "joint_friendly": 1, "cardio": 1, "strength": 0},
    {"name": "Yoga Flow", "impact": 1, "intensity": 2, "vata_score": 0.9, "pitta_score": 0.8, "kapha_score": 0.5, "joint_friendly": 1, "cardio": 0, "strength": 0},
    {"name": "Dumbbell Press", "impact": 2, "intensity": 3, "vata_score": 0.6, "pitta_score": 0.7, "kapha_score": 0.8, "joint_friendly": 0, "cardio": 0, "strength": 1},
    {"name": "Barbell Deadlift", "impact": 3, "intensity": 5, "vata_score": 0.3, "pitta_score": 0.5, "kapha_score": 0.7, "joint_friendly": 0, "cardio": 0, "strength": 1},
    {"name": "HIIT Burpees", "impact": 3, "intensity": 5, "vata_score": 0.2, "pitta_score": 0.4, "kapha_score": 0.85, "joint_friendly": 0, "cardio": 1, "strength": 0},
    {"name": "Resistance Bands", "impact": 1, "intensity": 2, "vata_score": 0.8, "pitta_score": 0.75, "kapha_score": 0.7, "joint_friendly": 1, "cardio": 0, "strength": 1},
    {"name": "Goblet Squat", "impact": 2, "intensity": 3, "vata_score": 0.65, "pitta_score": 0.7, "kapha_score": 0.8, "joint_friendly": 0, "cardio": 0, "strength": 1},
    {"name": "Elliptical", "impact": 1, "intensity": 3, "vata_score": 0.8, "pitta_score": 0.8, "kapha_score": 0.75, "joint_friendly": 1, "cardio": 1, "strength": 0},
    {"name": "Plank", "impact": 1, "intensity": 2, "vata_score": 0.8, "pitta_score": 0.75, "kapha_score": 0.7, "joint_friendly": 1, "cardio": 0, "strength": 1},
    {"name": "Zumba Dance", "impact": 2, "intensity": 3, "vata_score": 0.6, "pitta_score": 0.65, "kapha_score": 0.9, "joint_friendly": 0, "cardio": 1, "strength": 0},
    {"name": "Running", "impact": 3, "intensity": 4, "vata_score": 0.4, "pitta_score": 0.55, "kapha_score": 0.8, "joint_friendly": 0, "cardio": 1, "strength": 0},
    {"name": "Rowing Machine", "impact": 1, "intensity": 4, "vata_score": 0.7, "pitta_score": 0.75, "kapha_score": 0.85, "joint_friendly": 1, "cardio": 1, "strength": 1},
    {"name": "Tai Chi", "impact": 1, "intensity": 1, "vata_score": 0.95, "pitta_score": 0.7, "kapha_score": 0.4, "joint_friendly": 1, "cardio": 0, "strength": 0},
]

def save_exercise_data():
    df = pd.DataFrame(EXERCISES)
    df.to_csv(OUTPUT_DIR / "exercise_vectors.csv", index=False)
    print(f"✅ Exercise data: {len(df)} records")
    return df


# ─────────────────────────────────────────
# 5. DIET SUITABILITY SCORER DATA
# ─────────────────────────────────────────
FOODS = [
    {"food": "cucumber", "vata_neg": 5, "pitta_neg": -3, "kapha_neg": -2, "gi": 15, "inflammation": -3},
    {"food": "mung_dal", "vata_neg": -2, "pitta_neg": -3, "kapha_neg": -2, "gi": 25, "inflammation": -3},
    {"food": "ghee", "vata_neg": -4, "pitta_neg": -1, "kapha_neg": 3, "gi": 0, "inflammation": -2},
    {"food": "white_rice", "vata_neg": -2, "pitta_neg": -2, "kapha_neg": 3, "gi": 72, "inflammation": 1},
    {"food": "brown_rice", "vata_neg": 1, "pitta_neg": -1, "kapha_neg": 2, "gi": 55, "inflammation": 0},
    {"food": "red_chili", "vata_neg": 3, "pitta_neg": 5, "kapha_neg": -4, "gi": 10, "inflammation": 4},
    {"food": "coconut_milk", "vata_neg": -3, "pitta_neg": -3, "kapha_neg": 2, "gi": 40, "inflammation": -2},
    {"food": "quinoa", "vata_neg": 0, "pitta_neg": -2, "kapha_neg": -1, "gi": 53, "inflammation": -1},
    {"food": "barley", "vata_neg": 1, "pitta_neg": -1, "kapha_neg": -3, "gi": 28, "inflammation": -2},
    {"food": "tomato", "vata_neg": 2, "pitta_neg": 4, "kapha_neg": -1, "gi": 35, "inflammation": 2},
    {"food": "leafy_greens", "vata_neg": 2, "pitta_neg": -3, "kapha_neg": -3, "gi": 10, "inflammation": -3},
    {"food": "sweet_potato", "vata_neg": -2, "pitta_neg": -1, "kapha_neg": 2, "gi": 63, "inflammation": -1},
    {"food": "bitter_gourd", "vata_neg": 3, "pitta_neg": -2, "kapha_neg": -4, "gi": 20, "inflammation": -3},
    {"food": "flaxseed", "vata_neg": -1, "pitta_neg": -2, "kapha_neg": -1, "gi": 10, "inflammation": -4},
    {"food": "almonds", "vata_neg": -3, "pitta_neg": -1, "kapha_neg": 2, "gi": 10, "inflammation": -3},
]

def generate_diet_scorer_data(n: int = 10000) -> pd.DataFrame:
    records = []
    for _ in range(n):
        food = random.choice(FOODS)
        dosha = random.choice(["vata", "pitta", "kapha"])
        bmi_cat = random.choice(["underweight", "normal", "overweight", "obese"])
        goal = random.choice(["weight_loss", "muscle_gain", "general_wellness"])

        # Compute suitability score (0-100)
        dosha_penalty = food.get(f"{dosha}_neg", 0)
        gi_penalty = food["gi"] / 20 if goal == "weight_loss" else 0
        inflammation_factor = food["inflammation"]

        bmi_factor = 0
        if bmi_cat in ["overweight", "obese"] and food["gi"] > 60:
            bmi_factor = 10

        raw_score = 60 - (dosha_penalty * 4) - gi_penalty - (inflammation_factor * 3) - bmi_factor
        score = round(max(5, min(99, raw_score + random.gauss(0, 5))), 1)

        records.append({
            "food": food["food"],
            "dosha_vata": 1 if dosha == "vata" else 0,
            "dosha_pitta": 1 if dosha == "pitta" else 0,
            "dosha_kapha": 1 if dosha == "kapha" else 0,
            "bmi_overweight": 1 if bmi_cat in ["overweight", "obese"] else 0,
            "goal_weight_loss": 1 if goal == "weight_loss" else 0,
            "gi_index": food["gi"],
            "inflammation_score": food["inflammation"],
            "suitability_score": score,
        })

    df = pd.DataFrame(records)
    df.to_csv(OUTPUT_DIR / "diet_scorer_training.csv", index=False)
    print(f"✅ Diet scorer data: {len(df)} records")
    return df


if __name__ == "__main__":
    print("🔄 Generating all ML training datasets...")
    generate_dosha_data()
    generate_health_risk_data()
    generate_symptom_data()
    save_exercise_data()
    generate_diet_scorer_data()
    print("✅ All training data generated in server/ml/training_data/")
