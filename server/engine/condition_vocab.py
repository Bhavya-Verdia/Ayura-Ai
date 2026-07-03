"""
Condition vocabulary + precise matching.

Replaces fragile naive-substring condition matching (`key in condition`) which
both over-matches ("heart" matched "heartburn" → cardiac herbs for reflux) and is
case-sensitive in places (a capitalised "Anemia" bypassed a contraindication set).

Two tools:
  - normalize_condition / normalize_conditions: map free-text or aliased condition
    names onto canonical keys (a real normalized vocabulary).
  - term_in_condition(condition, term): precise, case-insensitive containment.
    Matches `term` as a whole word/phrase, NOT as a raw substring. A term ending
    in '*' is a prefix stem ('epilep*' matches 'epilepsy', 'epileptic').

Used by the safety-critical gates (medicine contraindications, Panchakarma karma
contraindications, Shodhana eligibility). Designed to be safe-biased: when in
doubt it is better to flag a contraindication than to miss one.
"""
from __future__ import annotations

import re

# ── Canonical condition vocabulary ────────────────────────────────────────────
# canonical_key -> set of alias strings users / other modules may supply.
# Keep aliases lowercase, underscore-or-space agnostic (normalization handles both).
CONDITION_ALIASES: dict[str, set[str]] = {
    "diabetes_type2": {"diabetes", "type2 diabetes", "type 2 diabetes", "t2dm",
                       "diabetes mellitus", "madhumeha", "prediabetes", "insulin resistance"},
    "hypertension": {"high blood pressure", "high bp", "bp", "htn", "uchcha raktachapa"},
    "hypotension": {"low blood pressure", "low bp"},
    "heart_disease": {"cardiac", "cardiac disease", "cardiovascular disease",
                      "coronary artery disease", "ischemic heart disease", "hridroga"},
    "anemia": {"iron deficiency", "iron deficiency anemia", "pandu", "anaemia"},
    "hypothyroidism": {"hypothyroid", "low thyroid", "underactive thyroid"},
    "hyperthyroidism": {"hyperthyroid", "overactive thyroid"},
    "acid_reflux": {"acidity", "gerd", "heartburn", "amlapitta", "acid peptic disease"},
    "ibs": {"irritable bowel syndrome", "grahani"},
    "fatty_liver": {"nafld", "liver disease", "hepatic steatosis"},
    "kidney_disease": {"ckd", "renal disease", "chronic kidney disease", "vrikka roga"},
    "rheumatoid_arthritis": {"rheumatoid", "ra", "amavata"},
    "osteoarthritis": {"oa", "sandhivata", "degenerative joint disease"},
    "ankylosing_spondylitis": {"as", "spondylitis"},
    "sciatica": {"gridhrasi"},
    "psoriasis": {"kitibha", "skin psoriasis"},
    "pcos": {"polycystic ovary syndrome", "polycystic ovarian syndrome", "pcod"},
    "epilepsy": {"seizure disorder", "apasmara"},
    "glaucoma": set(),
    "asthma": {"bronchial asthma", "tamaka shwasa"},
    "migraine": {"ardhavabhedaka"},
    "obesity": {"overweight", "sthoulya"},
    "anxiety": {"anxiety disorder", "chittodvega"},
    "depression": {"vishada", "major depressive disorder"},
}

# Extra synonyms / classical names that appear across the KBs — each canonical key
# below is a REAL entry in engine.dosha_analyzer._DISEASE_DOSHA_SIGNAL, so these
# aliases make the central disease lookup resolve them (no new classical claims).
_EXTRA_ALIASES: dict[str, set[str]] = {
    "acid_reflux": {"hyperacidity", "amlapitta", "acid peptic disease"},
    "ibs": {"ibs c", "ibs d", "irritable bowel", "spastic colon"},
    "gout": {"vatarakta", "uric acid", "hyperuricemia"},
    "anemia": {"pandu", "pandu roga"},
    "migraine": {"ardhavabhedaka", "chronic migraine", "cluster headache"},
    "hemorrhoids": {"piles", "arsha", "bawaseer", "haemorrhoids"},
    "heart_disease": {"cardiovascular disease", "cardiac rehabilitation",
                      "heart surgery recovery", "coronary artery disease"},
    "diabetes_type2": {"prameha", "madhumeha", "prediabetes", "insulin resistance"},
    "fibromyalgia": {"fms", "fibromyalgia syndrome"},
    "rheumatoid_arthritis": {"inflammatory arthritis", "autoimmune arthritis"},
    "cervical_spondylosis": {"cervical disc", "cervical radiculopathy", "cervical spondylitis", "neck arthritis"},
    "vertigo": {"bppv", "labyrinthitis", "dizziness", "bhrama"},
    "constipation_chronic": {"constipation", "chronic constipation", "vibandha"},
    "recurrent_uti": {"uti", "urinary tract infection", "mutrakrichra"},
    "long_covid": {"long covid fatigue", "post covid", "post covid fatigue"},
    "hyperthyroidism": {"hyperthyroid", "thyrotoxicosis"},
    "hypothyroidism": {"hypothyroid", "hashimotos thyroiditis"},
    "gallstones": {"cholelithiasis", "gallbladder stones"},
    "kidney_stones": {"renal calculi", "nephrolithiasis", "mutrashmari"},
    "eczema": {"atopic dermatitis", "vicharchika"},
    "sinusitis": {"sinus", "pinasa", "chronic sinusitis"},
    "chronic_kidney_disease": {"ckd", "kidney disease", "kidney failure", "renal failure", "dialysis"},
    "psoriasis": {"kitibha", "mandal kushtha"},
    "osteoarthritis": {"sandhivata", "degenerative joint disease"},
    "asthma": {"tamaka shwasa", "bronchial asthma"},
    # Common lay / colloquial terms that users type free-hand — resolve them to
    # an existing canonical entry instead of letting them contribute nothing.
    # "thyroid" alone is ambiguous; hypothyroidism is ~90% of thyroid disease, so
    # a bare "thyroid" defaults there.
    "hypothyroidism": {"thyroid", "thyroid disorder", "thyroid problem",
                       "underactive thyroid", "thyroid issue"},
    "diabetes_type2": {"sugar", "high sugar", "blood sugar", "sugar problem"},
    "high_cholesterol": {"cholesterol", "high cholesterol", "dyslipidemia",
                         "hyperlipidemia", "high lipids"},
    "acid_reflux": {"acidity", "gerd", "gas", "gastric"},
    "hypertension": {"bp", "high bp", "high blood pressure", "raised bp"},
    # New canonical: acute upper-respiratory (Pratishyaya) — see _DISEASE_DOSHA_SIGNAL.
    "common_cold": {"cold", "common cold", "cough", "sardi", "sardi khansi",
                    "pratishyaya", "runny nose", "running nose", "flu",
                    "influenza", "nasal congestion", "kasa"},
}
for _ek, _ev in _EXTRA_ALIASES.items():
    CONDITION_ALIASES.setdefault(_ek, set()).update(_ev)

# Reverse index: alias/canonical -> canonical key
_ALIAS_INDEX: dict[str, str] = {}
for _canon, _aliases in CONDITION_ALIASES.items():
    _ALIAS_INDEX[_canon] = _canon
    for _a in _aliases:
        _ALIAS_INDEX[re.sub(r"[^a-z0-9]+", " ", _a.lower()).strip()] = _canon


def _norm_text(value: str) -> str:
    """Lowercase, collapse any non-alphanumeric run to a single space, strip."""
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def _singularize(text: str) -> str:
    """Naive depluralization so 'bleeding disorders' and 'bleeding disorder' match.

    Strips a trailing 's' only from tokens long enough to plausibly be plural (so
    'as'/'is'/'ibs' are left alone) and not ending in 'ss'. Applied symmetrically to
    both sides of a comparison, so words like 'diabetes' transform consistently and
    still match — it only ever ADDS singular/plural matches (safe-biased)."""
    return " ".join(
        tok[:-1] if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss") else tok
        for tok in text.split()
    )


def normalize_condition(raw: str) -> str:
    """Return the canonical key for a free-text/aliased condition, or a cleaned
    underscore form if it is not in the vocabulary (never returns empty for input)."""
    norm = _norm_text(raw)
    if not norm:
        return ""
    if norm in _ALIAS_INDEX:
        return _ALIAS_INDEX[norm]
    return norm.replace(" ", "_")


def normalize_conditions(raw_list) -> list[str]:
    """Normalize + de-duplicate a list of conditions, preserving order."""
    seen: list[str] = []
    for c in raw_list or []:
        key = normalize_condition(c)
        if key and key not in seen:
            seen.append(key)
    return seen


def term_in_condition(condition: str, term: str) -> bool:
    """Precise, case-insensitive containment of `term` within `condition`.

    - Whole-word / whole-phrase match by default: 'heart' matches 'heart disease'
      and 'heart_disease' but NOT 'heartburn'.
    - A term ending in '*' is a prefix stem: 'epilep*' matches 'epilepsy'.
    """
    c = _norm_text(condition)
    t = (term or "").lower().strip()
    if not c or not t:
        return False
    if t.endswith("*"):
        stem = _norm_text(t[:-1])
        if not stem:
            return False
        return any(tok.startswith(stem) for tok in c.split())
    t_norm = _norm_text(t)
    if not t_norm:
        return False
    # Plural-tolerant whole-phrase match so 'bleeding_disorders' (medicine contra)
    # still matches a user's 'bleeding disorder' — a missed contraindication is the
    # dangerous direction. Singularize both sides consistently before matching.
    c_s, t_s = _singularize(c), _singularize(t_norm)
    return re.search(r"\b" + re.escape(t_s) + r"\b", c_s) is not None


def any_term_in_condition(condition: str, terms) -> bool:
    """True if any term in `terms` matches `condition` (precise word/phrase/stem)."""
    return any(term_in_condition(condition, t) for t in terms)


def condition_in_any_term(condition: str, terms) -> bool:
    """True if `condition` (as a word/phrase) appears inside any of `terms` — the
    reverse direction, for when a medicine's contraindication is more specific
    than the user's condition (contra='liver_disease' vs condition='liver')."""
    return any(term_in_condition(t, condition) for t in terms)
