"""
Ayura AI — Lab results: the catalogue, and how a value is read against it.

A user records a result the way it is printed on their report (one test, one value,
the date the sample was taken). This module is the only place that knows what a test
is: its unit, the values that cannot be a real reading (a typo, not a result), the
published reference bands, and the values where waiting for the next appointment is
the wrong advice.

What it does NOT do is diagnose. A band is reported in the guideline's own terms —
"in the range used to diagnose diabetes", never "you have diabetes" — because a
single reading is not a diagnosis and the doctor confirms with a repeat test. And no
plan engine reads these values yet: deciding, say, that a potassium of 5.6 should
change a kidney patient's diet is a clinical rule, and it belongs in the Vaidya packet
before it belongs in code.

Sex-specific ranges: `other` or unanswered takes the stricter limit of the two (the
one that flags sooner). Over-flagging costs a conversation with a doctor; a falsely
reassuring "normal" costs more. Pregnancy changes several ranges; where it does and
the trimester-specific range is not authored here, the reading is left unclassified
and says so, rather than being judged against the non-pregnant range.
"""
from __future__ import annotations

from typing import Optional

# status values a reading can take
LOW, NORMAL, BORDERLINE, HIGH, UNCLASSIFIED = "low", "normal", "borderline", "high", "unclassified"


def _sex_key(sex: Optional[str]) -> str:
    s = (sex or "").lower()
    return s if s in ("male", "female") else "unknown"


# Each test: label, unit, plausible bounds (outside them is refused as a typo), bands,
# urgent thresholds, and the source of the bands. `bands(sex, pregnant)` returns an
# ordered list of (upper_bound_exclusive, status, label); the last upper bound is None.
def _hba1c(sex, pregnant):
    return [(5.7, NORMAL, "Normal"),
            (6.5, BORDERLINE, "In the prediabetes range"),
            (None, HIGH, "In the range used to diagnose diabetes")]


def _fasting_glucose(sex, pregnant):
    return [(70, LOW, "Low"),
            (100, NORMAL, "Normal"),
            (126, BORDERLINE, "In the prediabetes range (impaired fasting glucose)"),
            (None, HIGH, "In the range used to diagnose diabetes")]


def _tsh(sex, pregnant):
    if pregnant:
        return None  # trimester-specific; not authored
    return [(0.4, LOW, "Below the usual range"),
            (4.0 + 1e-9, NORMAL, "Normal"),
            (None, HIGH, "Above the usual range")]


def _hemoglobin(sex, pregnant):
    if pregnant:
        low = 11.0
        high = 15.0
    else:
        low = {"male": 13.0, "female": 12.0, "unknown": 13.0}[_sex_key(sex)]
        high = {"male": 17.5, "female": 15.5, "unknown": 15.5}[_sex_key(sex)]
    return [(low, LOW, "Below the WHO threshold for anaemia"),
            (high + 1e-9, NORMAL, "Normal"),
            (None, HIGH, "Above the usual range")]


def _ferritin(sex, pregnant):
    high = {"male": 200, "female": 150, "unknown": 150}[_sex_key(sex)]
    return [(15, LOW, "Low — iron stores depleted"),
            (high + 1e-9, NORMAL, "Normal"),
            (None, HIGH, "Above the usual range")]


def _vitamin_d(sex, pregnant):
    return [(20, LOW, "Deficient"),
            (30, BORDERLINE, "Insufficient"),
            (100 + 1e-9, NORMAL, "Sufficient"),
            (None, HIGH, "Above the usual range")]


def _b12(sex, pregnant):
    return [(200, LOW, "Low"),
            (300, BORDERLINE, "Borderline"),
            (None, NORMAL, "Normal")]


def _total_cholesterol(sex, pregnant):
    return [(200, NORMAL, "Desirable"),
            (240, BORDERLINE, "Borderline high"),
            (None, HIGH, "High")]


def _ldl(sex, pregnant):
    return [(100, NORMAL, "Optimal"),
            (160, BORDERLINE, "Near optimal to borderline high"),
            (190, HIGH, "High"),
            (None, HIGH, "Very high")]


def _hdl(sex, pregnant):
    low = {"male": 40, "female": 50, "unknown": 50}[_sex_key(sex)]
    return [(low, LOW, "Low"), (None, NORMAL, "Normal")]


def _triglycerides(sex, pregnant):
    return [(150, NORMAL, "Normal"),
            (200, BORDERLINE, "Borderline high"),
            (500, HIGH, "High"),
            (None, HIGH, "Very high")]


def _creatinine(sex, pregnant):
    low, high = {"male": (0.7, 1.3), "female": (0.6, 1.1), "unknown": (0.6, 1.1)}[_sex_key(sex)]
    return [(low, LOW, "Below the usual range"),
            (high + 1e-9, NORMAL, "Normal"),
            (None, HIGH, "Above the usual range")]


def _egfr(sex, pregnant):
    # KDIGO G-stages. Low is the concerning direction here.
    return [(15, LOW, "Kidney function in the kidney-failure range (G5)"),
            (30, LOW, "Severely decreased (G4)"),
            (60, LOW, "Moderately decreased (G3)"),
            (90, BORDERLINE, "Mildly decreased (G2) — only significant with other kidney findings"),
            (None, NORMAL, "Normal (G1)")]


def _potassium(sex, pregnant):
    return [(3.5, LOW, "Low"),
            (5.0 + 1e-9, NORMAL, "Normal"),
            (None, HIGH, "High")]


def _uric_acid(sex, pregnant):
    high = {"male": 7.0, "female": 6.0, "unknown": 6.0}[_sex_key(sex)]
    return [(high + 1e-9, NORMAL, "Normal"), (None, HIGH, "Above the usual range")]


def _systolic(sex, pregnant):
    # ISH 2020: normal < 130/85, high-normal 130-139/85-89, hypertension >= 140/90.
    return [(90, LOW, "Low"),
            (130, NORMAL, "Normal"),
            (140, BORDERLINE, "High-normal"),
            (None, HIGH, "In the hypertension range")]


def _diastolic(sex, pregnant):
    return [(60, LOW, "Low"),
            (85, NORMAL, "Normal"),
            (90, BORDERLINE, "High-normal"),
            (None, HIGH, "In the hypertension range")]


# urgent: (below, at_or_above) — either may be None. A reading past one of these says
# "contact a doctor today" instead of "discuss at your next appointment".
LAB_TESTS: dict[str, dict] = {
    "hba1c": {"label": "HbA1c", "unit": "%", "min": 3, "max": 20, "group": "Blood sugar",
              "bands": _hba1c, "urgent": (None, None),
              "source": "American Diabetes Association, Standards of Care 2024"},
    "fasting_glucose": {"label": "Fasting blood glucose", "unit": "mg/dL", "min": 20, "max": 700,
                        "group": "Blood sugar", "bands": _fasting_glucose, "urgent": (54, 250),
                        "source": "American Diabetes Association, Standards of Care 2024"},
    "tsh": {"label": "TSH (thyroid)", "unit": "mIU/L", "min": 0.005, "max": 150, "group": "Thyroid",
            "bands": _tsh, "urgent": (None, None),
            "source": "Typical adult reference interval (American Thyroid Association); labs vary"},
    "hemoglobin": {"label": "Haemoglobin", "unit": "g/dL", "min": 3, "max": 25, "group": "Blood count",
                   "bands": _hemoglobin, "urgent": (8, None),
                   "source": "WHO haemoglobin thresholds for anaemia (2011)"},
    "ferritin": {"label": "Ferritin", "unit": "ng/mL", "min": 1, "max": 5000, "group": "Iron and vitamins",
                 "bands": _ferritin, "urgent": (None, None),
                 "source": "WHO guideline on ferritin thresholds (2020)"},
    "vitamin_d": {"label": "Vitamin D (25-OH)", "unit": "ng/mL", "min": 1, "max": 200,
                  "group": "Iron and vitamins", "bands": _vitamin_d, "urgent": (None, None),
                  "source": "Endocrine Society clinical practice guideline (2011)"},
    "b12": {"label": "Vitamin B12", "unit": "pg/mL", "min": 50, "max": 3000, "group": "Iron and vitamins",
            "bands": _b12, "urgent": (None, None),
            "source": "Common laboratory cut-offs (Hunt et al., BMJ 2014)"},
    "total_cholesterol": {"label": "Total cholesterol", "unit": "mg/dL", "min": 50, "max": 600,
                          "group": "Lipids", "bands": _total_cholesterol, "urgent": (None, None),
                          "source": "NCEP Adult Treatment Panel III"},
    "ldl": {"label": "LDL cholesterol", "unit": "mg/dL", "min": 10, "max": 500, "group": "Lipids",
            "bands": _ldl, "urgent": (None, None), "source": "NCEP Adult Treatment Panel III"},
    "hdl": {"label": "HDL cholesterol", "unit": "mg/dL", "min": 5, "max": 200, "group": "Lipids",
            "bands": _hdl, "urgent": (None, None), "source": "NCEP Adult Treatment Panel III"},
    "triglycerides": {"label": "Triglycerides", "unit": "mg/dL", "min": 10, "max": 5000, "group": "Lipids",
                      "bands": _triglycerides, "urgent": (None, 1000),
                      "source": "NCEP Adult Treatment Panel III"},
    "creatinine": {"label": "Creatinine", "unit": "mg/dL", "min": 0.1, "max": 20, "group": "Kidney",
                   "bands": _creatinine, "urgent": (None, None),
                   "source": "Typical adult reference interval; labs vary"},
    "egfr": {"label": "eGFR", "unit": "mL/min/1.73m²", "min": 1, "max": 200, "group": "Kidney",
             "bands": _egfr, "urgent": (15, None), "source": "KDIGO CKD guideline (2012)"},
    "potassium": {"label": "Potassium", "unit": "mmol/L", "min": 1.5, "max": 9, "group": "Kidney",
                  "bands": _potassium, "urgent": (3.0, 6.0),
                  "source": "Typical adult reference interval"},
    "uric_acid": {"label": "Uric acid", "unit": "mg/dL", "min": 0.5, "max": 20, "group": "Kidney",
                  "bands": _uric_acid, "urgent": (None, None),
                  "source": "Typical adult reference interval"},
    "systolic_bp": {"label": "Blood pressure — systolic (upper)", "unit": "mmHg", "min": 60, "max": 260,
                    "group": "Blood pressure", "bands": _systolic, "urgent": (None, 180),
                    "source": "International Society of Hypertension guideline (2020)"},
    "diastolic_bp": {"label": "Blood pressure — diastolic (lower)", "unit": "mmHg", "min": 30, "max": 160,
                     "group": "Blood pressure", "bands": _diastolic, "urgent": (None, 110),
                     "source": "International Society of Hypertension guideline (2020)"},
}

ADVICE_FLAG = "Worth discussing with your doctor."
ADVICE_URGENT = "Contact a doctor today about this result."
ADVICE_PREGNANT = "Ranges for this test are different in pregnancy — ask your doctor how to read it."


def classify(test: str, value: float, sex: Optional[str] = None, pregnant: bool = False) -> dict:
    """Read one value against its test's bands. Raises KeyError for an unknown test."""
    spec = LAB_TESTS[test]
    bands = spec["bands"](sex, pregnant)
    if bands is None:
        return {"status": UNCLASSIFIED, "reading": "Not classified in pregnancy",
                "urgent": False, "advice": ADVICE_PREGNANT}
    status, label = bands[-1][1], bands[-1][2]
    for upper, st, lb in bands:
        if upper is None or value < upper:
            status, label = st, lb
            break
    below, at_or_above = spec["urgent"]
    urgent = (below is not None and value < below) or (at_or_above is not None and value >= at_or_above)
    advice = ADVICE_URGENT if urgent else (ADVICE_FLAG if status != NORMAL else None)
    return {"status": status, "reading": label, "urgent": urgent, "advice": advice}


def catalogue() -> list[dict]:
    """The tests in display order, without the band functions."""
    return [{"key": k, "label": v["label"], "unit": v["unit"], "min": v["min"], "max": v["max"],
             "group": v["group"], "source": v["source"]} for k, v in LAB_TESTS.items()]


def plausible(test: str, value: float) -> bool:
    spec = LAB_TESTS[test]
    return spec["min"] <= value <= spec["max"]


def latest_by_test(results: list[dict]) -> list[dict]:
    """Newest result per test. Urgent ones first, then the rest in catalogue order:
    a potassium of 6.2 must not sit below a normal vitamin D. `results` must carry
    `test` and `taken_on` (ISO date string or date)."""
    newest: dict[str, dict] = {}
    for r in results:
        cur = newest.get(r["test"])
        if cur is None or str(r["taken_on"]) > str(cur["taken_on"]):
            newest[r["test"]] = r
    ordered = [newest[k] for k in LAB_TESTS if k in newest]
    return sorted(ordered, key=lambda r: not r.get("urgent", False))
