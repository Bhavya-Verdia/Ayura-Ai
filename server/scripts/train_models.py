"""
Ayura AI - ML Model Trainer
Trains all 6 ML models and saves them to server/ml/models/
Run: python scripts/train_models.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path

from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.neural_network import MLPClassifier
from sklearn.multioutput import MultiOutputRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_squared_error
from xgboost import XGBClassifier
from lightgbm import LGBMRegressor

DATA_DIR = Path(__file__).parent.parent / "server" / "ml" / "training_data"
MODELS_DIR = Path(__file__).parent.parent / "server" / "ml" / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────
# 1. DOSHA CLASSIFIER (XGBoost)
# ─────────────────────────────────────────
def train_dosha_classifier():
    print("\n📊 Training Dosha Classifier (XGBoost)...")
    data = pd.read_json(DATA_DIR / "dosha_training.json")

    X = np.array(data["answers"].tolist())
    le = LabelEncoder()
    y = le.fit_transform(data["label"])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False, eval_metric="mlogloss", random_state=42
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"  ✅ Accuracy: {acc:.3f}")

    joblib.dump(model, MODELS_DIR / "dosha_classifier.pkl")
    joblib.dump(le, MODELS_DIR / "dosha_label_encoder.pkl")
    print(f"  💾 Saved: dosha_classifier.pkl")
    return model, le


# ─────────────────────────────────────────
# 2. HEALTH RISK PREDICTOR (Gradient Boosting Multi-output)
# ─────────────────────────────────────────
def train_health_risk_predictor():
    print("\n📊 Training Health Risk Predictor (GradientBoosting)...")
    df = pd.read_csv(DATA_DIR / "health_risk_training.csv")

    feature_cols = ["bmi", "age", "gender_male", "dosha_vata", "dosha_pitta",
                    "dosha_kapha", "activity_sedentary", "activity_moderate"]
    target_cols = ["acid_reflux_risk", "joint_pain_risk", "inflammation_risk",
                   "diabetes_risk", "hypertension_risk"]

    X = df[feature_cols].values
    y = df[target_cols].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    base = GradientBoostingRegressor(n_estimators=150, max_depth=4, learning_rate=0.1)
    model = MultiOutputRegressor(base, n_jobs=-1)
    model.fit(X_train, y_train)

    mse = mean_squared_error(y_test, model.predict(X_test))
    print(f"  ✅ MSE: {mse:.4f}")

    joblib.dump(model, MODELS_DIR / "health_risk_predictor.pkl")
    joblib.dump(feature_cols, MODELS_DIR / "health_risk_features.pkl")
    joblib.dump(target_cols, MODELS_DIR / "health_risk_targets.pkl")
    print("  💾 Saved: health_risk_predictor.pkl")
    return model


# ─────────────────────────────────────────
# 3. SYMPTOM→CONDITION MAPPER (MLP Neural Network)
# ─────────────────────────────────────────
def train_symptom_mapper():
    print("\n📊 Training Symptom-Condition Mapper (MLP)...")
    df = pd.read_csv(DATA_DIR / "symptom_condition_training.csv")

    label_col = "label"
    feature_cols = [c for c in df.columns if c != label_col]

    X = df[feature_cols].values
    le = LabelEncoder()
    y = le.fit_transform(df[label_col])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = MLPClassifier(
        hidden_layer_sizes=(128, 64, 32),
        activation="relu",
        max_iter=300,
        random_state=42,
        early_stopping=True,
    )
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"  ✅ Accuracy: {acc:.3f}")

    joblib.dump(model, MODELS_DIR / "symptom_mapper.pkl")
    joblib.dump(le, MODELS_DIR / "symptom_label_encoder.pkl")
    joblib.dump(feature_cols, MODELS_DIR / "symptom_feature_cols.pkl")
    print("  💾 Saved: symptom_mapper.pkl")
    return model


# ─────────────────────────────────────────
# 4. DIET SUITABILITY SCORER (LightGBM)
# ─────────────────────────────────────────
def train_diet_scorer():
    print("\n📊 Training Diet Suitability Scorer (LightGBM)...")
    df = pd.read_csv(DATA_DIR / "diet_scorer_training.csv")

    feature_cols = ["dosha_vata", "dosha_pitta", "dosha_kapha",
                    "bmi_overweight", "goal_weight_loss", "gi_index", "inflammation_score"]
    X = df[feature_cols].values
    y = df["suitability_score"].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LGBMRegressor(n_estimators=200, max_depth=6, learning_rate=0.05, verbose=-1)
    model.fit(X_train, y_train)

    mse = mean_squared_error(y_test, model.predict(X_test))
    print(f"  ✅ RMSE: {mse**0.5:.3f}")

    joblib.dump(model, MODELS_DIR / "diet_scorer.pkl")
    joblib.dump(feature_cols, MODELS_DIR / "diet_scorer_features.pkl")
    print("  💾 Saved: diet_scorer.pkl")
    return model


# ─────────────────────────────────────────
# 5. EXERCISE RECOMMENDER (Cosine Similarity — no training, precomputed)
# ─────────────────────────────────────────
def build_exercise_recommender():
    print("\n📊 Building Exercise Recommender (Content-based)...")
    df = pd.read_csv(DATA_DIR / "exercise_vectors.csv")
    joblib.dump(df, MODELS_DIR / "exercise_vectors.pkl")
    print(f"  ✅ {len(df)} exercises indexed")
    print("  💾 Saved: exercise_vectors.pkl")
    return df


if __name__ == "__main__":
    print("🚀 Ayura AI ML Training Pipeline")
    print("=" * 50)
    from generate_training_data import (
        generate_dosha_data, generate_health_risk_data,
        generate_symptom_data, save_exercise_data, generate_diet_scorer_data
    )
    generate_dosha_data()
    generate_health_risk_data()
    generate_symptom_data()
    save_exercise_data()
    generate_diet_scorer_data()

    train_dosha_classifier()
    train_health_risk_predictor()
    train_symptom_mapper()
    train_diet_scorer()
    build_exercise_recommender()

    print("\n🎉 All models trained and saved to server/ml/models/")
