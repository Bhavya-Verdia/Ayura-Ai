"""Deepana-Pachana herbs pass the formulary, and Pitta gets Tikta Deepana.

The Ama-correction list is classical Katu Deepana (Trikatu, Chitraka, Hingu,
Panchakola), all Ushna and Tikshna. A live plan gave it to a Pitta patient with
acidity, which the medicines formulary bars for exactly that patient. Each herb now
goes through `screen_formulation`. Musta and Guduchi (Tikta, kindling Agni without
heat) are offered where a Katu herb is withheld.
"""
import json
from pathlib import Path

from services.panchakarma_engine import (
    _AMA_HERB_FORMULARY,
    _ama_correction_herbs,
    generate_panchakarma_plan,
)
from services.remedy_engine import _KB_BY_NAME

_ROOT = Path(__file__).resolve().parent.parent
_PROTOCOLS = json.loads((_ROOT / "data/knowledge_base/panchakarma_protocols.json").read_text())
_AMA = _PROTOCOLS["shodhana_eligibility"]["ama_correction_first"]
_PREFS = {"panchakarma_goal": "detox", "experience": "none", "duration_days": 14}


def _profile(dosha, history=(), agni="sama"):
    return {"age": 35, "gender": "female", "dominant_dosha": dosha, "vikriti_dominant": dosha,
            "medical_history": list(history), "ama_indicator": "high", "agni_type": agni}


def test_every_herb_is_screenable():
    for name in _AMA["herbs"] + _AMA["herbs_pitta"]:
        assert _AMA_HERB_FORMULARY.get(name, name) in _KB_BY_NAME, name


def test_a_pitta_patient_with_acidity_gets_no_katu_deepana():
    plan = generate_panchakarma_plan(_profile("pitta", ["acid_reflux"], "tikshna"), _PREFS, None)
    schedule = json.dumps(plan["daily_schedule"])
    for katu in _AMA["herbs"]:
        assert katu not in schedule, katu
    assert "Musta Churna" in schedule


def test_kapha_keeps_the_classical_list():
    herbs, withheld = _ama_correction_herbs(_AMA, _profile("kapha", agni="manda"))
    assert herbs == _AMA["herbs"] and withheld == []


def test_withheld_herbs_carry_a_reason():
    herbs, withheld = _ama_correction_herbs(_AMA, _profile("pitta", ["acid_reflux"]))
    assert herbs[:2] == _AMA["herbs_pitta"]
    assert withheld and all(w["reason"] for w in withheld)


def test_no_window_confirm_in_the_client():
    # Native dialogs block the page and cannot be styled or translated;
    # `components/InlineConfirm.jsx` asks in the page instead.
    src = _ROOT.parent / "client" / "src"
    hits = [p.name for p in src.rglob("*.jsx") if "window.confirm(" in p.read_text()]
    assert hits == []
