"""
Tests for the Vaidya-handoff PDF export (routes/export._build_pdf).

Guards the clinical-profile code path (Prakriti/Vikriti/Agni/Ama/Ojas/Manasa +
recent Vikriti trend) against exceptions and confirms a real PDF is produced.
"""

import pytest
from datetime import datetime, timezone
from types import SimpleNamespace

from routes.export import _build_pdf

reportlab = pytest.importorskip("reportlab")  # prod dependency; skip if absent


def _clinical_user():
    return SimpleNamespace(
        name="Maya", dominant_dosha="pitta", goal="general_wellness",
        bmi=22.5, bmi_category="normal",
        dosha_scores={"vata": 20, "pitta": 55, "kapha": 25},
        dosha_confidence=72,
        dosha_constitution_type="pitta_vata",
        prakriti_classical_name="Pitta-Vata Prakriti (Dvidoshaja)",
        vikriti_scores={"vata": 25, "pitta": 50, "kapha": 25},
        vikriti_dominant="pitta", vikriti_secondary="vata",
        agni_type="tikshna", ama_indicator="mild",
        ojas_level="medium", ojas_score=62,
        manasa_prakriti={"label": "Rajasika", "satva": 30, "rajas": 50,
                         "tamas": 20, "dominant_guna": "rajas"},
        primary_gunas=["Ushna (hot)", "Tikshna (sharp)"],
        medical_history=["hypertension", "acid_reflux"],
        current_medications=["metformin"],
        allergies=["peanuts"],
        vikriti_history=[{
            "ts": datetime(2026, 6, 20, tzinfo=timezone.utc), "dominant": "pitta",
            "scores": {"vata": 25, "pitta": 50, "kapha": 25},
            "symptoms": ["heartburn_acidity"],
        }],
    )


def test_pdf_builds_with_clinical_profile():
    pdf = _build_pdf(_clinical_user(), {"diet_plan": {"summary": "Sample"}},
                     "20 June 2026 at 09:00 UTC")
    assert isinstance(pdf, bytes)
    assert len(pdf) > 1000
    assert pdf[:4] == b"%PDF"


def test_pdf_builds_when_unassessed_user_has_no_clinical_data():
    """No Prakriti/Vikriti yet → clinical section is skipped, PDF still builds."""
    user = SimpleNamespace(
        name="New User", dominant_dosha=None, goal=None, bmi=None, bmi_category=None,
        dosha_scores=None, vikriti_scores=None, vikriti_history=None,
    )
    pdf = _build_pdf(user, {}, "20 June 2026")
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"
