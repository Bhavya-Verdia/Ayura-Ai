"""
Tests for the unified weekly Vikriti check-in (services/vikriti_service.py).

Both /profile/vikriti-checkin and /checkin/weekly now run this single refinement,
so the user's imbalance is updated the same way regardless of entry point, and
plan adaptation is grounded in an actual Vikriti shift.
"""
from types import SimpleNamespace

from services.vikriti_service import compute_vikriti_update, vikriti_shifted


def _user(**kw):
    base = dict(
        vikriti_scores={"vata": 40, "pitta": 35, "kapha": 25},
        dosha_scores={"vata": 50, "pitta": 30, "kapha": 20},
        vikriti_history=[], medical_history=[], gender="male",
        disease_stages={}, checkin_count=0, dosha_confidence=35,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_update_normalises_and_tracks_state():
    upd, old = compute_vikriti_update(
        _user(checkin_count=2, dosha_confidence=45),
        symptoms=["anxiety_worry"], sleep=2, digestion=2,
    )
    assert sum(upd["vikriti_scores"].values()) == 100
    assert upd["vikriti_dominant"] in ("vata", "pitta", "kapha")
    assert upd["checkin_count"] == 3                 # incremented
    assert upd["dosha_confidence"] > 45              # grows with check-ins
    assert len(upd["vikriti_history"]) == 1
    assert upd["vikriti_history"][-1]["pulse"]["digestion"] == 2


def test_ama_refreshes_from_digestion_trend():
    poor = compute_vikriti_update(_user(), symptoms=[], digestion=1)[0]
    good = compute_vikriti_update(_user(), symptoms=[], digestion=5)[0]
    assert poor["ama_indicator"] == "high"
    assert good["ama_indicator"] == "none"


def test_rolling_history_capped_at_12():
    hist = [{"scores": {"vata": 33, "pitta": 33, "kapha": 34}, "dominant": "kapha",
             "pulse": {"digestion": 3}, "ts": "t"} for _ in range(12)]
    upd, _ = compute_vikriti_update(_user(vikriti_history=hist), symptoms=[], digestion=3)
    assert len(upd["vikriti_history"]) == 12         # oldest dropped


def test_menstrual_phase_elevates_pitta_for_female():
    base = compute_vikriti_update(_user(gender="female"), symptoms=[])[0]["vikriti_scores"]
    mens = compute_vikriti_update(_user(gender="female"), symptoms=[], menstrual_phase=True)[0]["vikriti_scores"]
    assert mens["pitta"] >= base["pitta"]


def test_vikriti_shifted_detects_real_change_not_noise():
    assert vikriti_shifted({"vata": 40, "pitta": 35, "kapha": 25}, {"vata": 30, "pitta": 45, "kapha": 25})  # dominant flip
    assert vikriti_shifted({"vata": 40, "pitta": 35, "kapha": 25}, {"vata": 48, "pitta": 30, "kapha": 22})  # >=6 move
    assert not vikriti_shifted({"vata": 40, "pitta": 35, "kapha": 25}, {"vata": 41, "pitta": 34, "kapha": 25})  # noise
