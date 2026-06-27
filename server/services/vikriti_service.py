"""
Shared Vikriti-refinement logic for the weekly check-in.

Both check-in entry points use this single function so the user's current
imbalance (Vikriti) is refined the same way no matter which UI they came from:
  - /profile/vikriti-checkin  (VikritiCheckIn dashboard modal)
  - /checkin/weekly           (Check-In page)

It blends the prior Vikriti with this week's symptom + lifestyle signal, anchors
to Prakriti, applies seasonal/medical/menstrual corrections, updates the Kriya
Kala disease stage, grows confidence with each check-in, refreshes Ama from the
digestion trend, and keeps a rolling 12-week history.
"""
from __future__ import annotations

from datetime import datetime, timezone


# (duration, trajectory) → classical Shatkriyakala stage (Sushruta)
_KRIYA_KALA_MAP = {
    ("months", "worsening"): "prakopa", ("months", "stable"): "sanchaya", ("months", "improving"): "sanchaya",
    ("1-3y", "worsening"): "prasara", ("1-3y", "stable"): "sthana", ("1-3y", "improving"): "prakopa",
    ("3-5y", "worsening"): "vyakti", ("3-5y", "stable"): "sthana", ("3-5y", "improving"): "prasara",
    ("5y+", "worsening"): "bheda", ("5y+", "stable"): "vyakti", ("5y+", "improving"): "sthana",
}


def _ama_from_digestion_trend(history: list[dict]) -> str | None:
    """Ama (toxin load) is a function of Agni quality over time — estimate it from
    the recent digestion pulse (1-5). Returns None if there's no signal."""
    digs = [
        h["pulse"]["digestion"] for h in history
        if isinstance(h.get("pulse"), dict) and isinstance(h["pulse"].get("digestion"), (int, float))
    ]
    if not digs:
        return None
    avg = sum(digs[-4:]) / len(digs[-4:])
    if avg <= 2:
        return "high"
    if avg <= 2.8:
        return "moderate"
    if avg <= 3.6:
        return "mild"
    return "none"


def compute_vikriti_update(
    user,
    *,
    symptoms: list[str] | None = None,
    sleep: int | None = None,
    stress: int | None = None,
    digestion: int | None = None,
    menstrual_phase: bool | None = None,
    disease_stage_updates: dict | None = None,
) -> tuple[dict, dict]:
    """Compute the weekly Vikriti update. sleep/stress/digestion are 1-5 (1=poor).
    Returns (update_dict, old_vikriti) — the caller persists update_dict."""
    from engine.dosha_analyzer import (
        _apply_seasonal_correction,
        _blend_vikriti,
        _compute_symptom_signal,
        _confidence_from_checkins,
        _lifestyle_pulse_signal,
        _medical_history_vikriti_signal,
        _symptom_persistence_weights,
        _vikriti_secondary,
    )

    old_vikriti = dict(user.vikriti_scores or {"vata": 33, "pitta": 33, "kapha": 34})
    prakriti = user.dosha_scores
    existing_history: list = list(user.vikriti_history or [])

    meaningful = [s for s in (symptoms or []) if s != "feeling_balanced"]
    persistence_weights = _symptom_persistence_weights(meaningful, existing_history) if meaningful else None
    symptom_signal = _compute_symptom_signal(meaningful, persistence_weights) if meaningful else {}
    lifestyle_signal = _lifestyle_pulse_signal(sleep, stress, digestion)

    blended = _blend_vikriti(old_vikriti, symptom_signal, len(meaningful), prakriti, lifestyle_signal or None)
    blended = _apply_seasonal_correction(blended)

    # Medical history — persistent disease channel involvement biases Vikriti (15% slot)
    if user.medical_history:
        _med_sig, _ = _medical_history_vikriti_signal(user.medical_history)
        if _med_sig:
            MEDICAL_SLOT = 0.15
            blended = {d: round((1 - MEDICAL_SLOT) * blended.get(d, 33) + MEDICAL_SLOT * _med_sig.get(d, 33))
                       for d in ["vata", "pitta", "kapha"]}
            _t = sum(blended.values()) or 1
            blended = {d: round(v / _t * 100) for d, v in blended.items()}
            _d = 100 - sum(blended.values())
            if _d != 0:
                blended[max(blended, key=blended.get)] += _d

    # Menstrual phase: Pitta naturally elevates during menstruation (classical Artava teaching)
    if menstrual_phase and getattr(user, "gender", None) == "female":
        blended["pitta"] = min(68, round(blended.get("pitta", 33) * 1.12))
        _t = sum(blended.values()) or 1
        blended = {d: round(v / _t * 100) for d, v in blended.items()}
        _d = 100 - sum(blended.values())
        if _d != 0:
            blended[max(blended, key=blended.get)] += _d

    # Kriya Kala stage update
    existing_stages = dict(user.disease_stages or {})
    for cid, stage_data in (disease_stage_updates or {}).items():
        duration = stage_data.get("duration", "months")
        trajectory = stage_data.get("trajectory", "stable")
        existing_stages[cid] = {
            "duration": duration, "trajectory": trajectory,
            "kriya_kala": _KRIYA_KALA_MAP.get((duration, trajectory), "vyakti"),
        }

    new_checkin_count = (user.checkin_count or 0) + 1
    new_confidence = _confidence_from_checkins(user.dosha_confidence or 35, new_checkin_count)

    now = datetime.now(timezone.utc)
    vikriti_dominant = max(blended, key=blended.get)

    history_entry = {
        "scores": blended, "dominant": vikriti_dominant,
        "symptom_count": len(meaningful), "symptoms": meaningful,
        "pulse": {"sleep": sleep, "stress": stress, "digestion": digestion},
        "ts": now.isoformat(),
    }
    updated_history = (existing_history + [history_entry])[-12:]

    update = {
        "vikriti_scores": blended,
        "vikriti_dominant": vikriti_dominant,
        "vikriti_secondary": _vikriti_secondary(blended),
        "dosha_confidence": new_confidence,
        "checkin_count": new_checkin_count,
        "vikriti_history": updated_history,
        "last_vikriti_checkin": now,
        "disease_stages": existing_stages,
        "updated_at": now,
    }

    # Ama (toxin load) refresh from the digestion trend — Ama IS dynamic, unlike the
    # constitutional Agni type, so it's correct to update it weekly.
    ama = _ama_from_digestion_trend(updated_history)
    if ama is not None:
        update["ama_indicator"] = ama

    return update, old_vikriti


def vikriti_shifted(old: dict, new: dict, threshold: int = 6) -> bool:
    """True if the imbalance meaningfully changed — dominant flipped or any dosha
    moved by `threshold`+ points. Used to ground plan adaptation in a real shift."""
    if not old or not new:
        return True
    if max(old, key=old.get) != max(new, key=new.get):
        return True
    return any(abs(new.get(d, 33) - old.get(d, 33)) >= threshold for d in ("vata", "pitta", "kapha"))
