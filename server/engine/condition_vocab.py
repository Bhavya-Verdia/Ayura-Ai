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
    # The canonical name has to be the one the central disease map uses, or the
    # alias resolves to a key nothing can look up: "low bp" normalised to
    # `hypotension`, `_DISEASE_DOSHA_SIGNAL` calls it `low_blood_pressure`, and the
    # lookup returned nothing for a condition both tables knew about.
    "low_blood_pressure": {"low blood pressure", "low bp", "hypotension"},
    "heart_disease": {"cardiac", "cardiac disease", "cardiovascular disease",
                      "coronary artery disease", "ischemic heart disease", "hridroga"},
    "anemia": {"iron deficiency", "iron deficiency anemia", "pandu", "anaemia"},
    "hypothyroidism": {"hypothyroid", "low thyroid", "underactive thyroid"},
    "hyperthyroidism": {"hyperthyroid", "overactive thyroid"},
    "acid_reflux": {"acidity", "gerd", "heartburn", "amlapitta", "acid peptic disease"},
    "ibs": {"irritable bowel syndrome", "grahani"},
    "fatty_liver": {"nafld", "liver disease", "hepatic steatosis"},
    "chronic_kidney_disease": {"ckd", "renal disease", "kidney disease", "vrikka roga"},
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
    # Includes lay / colloquial terms users type free-hand ("gas", "acidity").
    "acid_reflux": {"hyperacidity", "amlapitta", "acid peptic disease",
                    "acidity", "gerd", "gas", "gastric"},
    "ibs": {"ibs c", "ibs d", "irritable bowel", "spastic colon"},
    "gout": {"vatarakta", "uric acid", "hyperuricemia"},
    "anemia": {"pandu", "pandu roga"},
    "migraine": {"ardhavabhedaka", "chronic migraine", "cluster headache"},
    "hemorrhoids": {"piles", "arsha", "bawaseer", "haemorrhoids"},
    "heart_disease": {"cardiovascular disease", "cardiac rehabilitation",
                      "heart surgery recovery", "coronary artery disease"},
    "diabetes_type2": {"prameha", "madhumeha", "prediabetes", "insulin resistance",
                       "sugar", "high sugar", "blood sugar", "sugar problem"},
    "fibromyalgia": {"fms", "fibromyalgia syndrome"},
    "rheumatoid_arthritis": {"inflammatory arthritis", "autoimmune arthritis"},
    "cervical_spondylosis": {"cervical disc", "cervical radiculopathy", "cervical spondylitis", "neck arthritis"},
    "vertigo": {"bppv", "labyrinthitis", "dizziness", "bhrama"},
    "constipation_chronic": {"constipation", "chronic constipation", "vibandha"},
    "recurrent_uti": {"uti", "urinary tract infection", "mutrakrichra"},
    "long_covid": {"long covid fatigue", "post covid", "post covid fatigue"},
    "hyperthyroidism": {"hyperthyroid", "thyrotoxicosis"},
    # "thyroid" alone is ambiguous; hypothyroidism is ~90% of thyroid disease,
    # so a bare "thyroid" defaults there.
    "hypothyroidism": {"hypothyroid", "hashimotos thyroiditis", "thyroid",
                       "thyroid disorder", "thyroid problem",
                       "underactive thyroid", "thyroid issue"},
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
    # `hypercholesterolemia` is the name `snehapana_home.soft` writes it under; the
    # app records `high_cholesterol`, so the ghee-dose caution never reached anyone.
    "high_cholesterol": {"cholesterol", "high cholesterol", "dyslipidemia",
                         "hyperlipidemia", "high lipids", "hypercholesterolemia",
                         "hypercholesterolaemia"},
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


# Second-chance index keyed on the alias with every separator removed. "diabetes
# type 2", "diabetes_type_2" and the canonical "diabetes_type2" are one string once
# punctuation and spacing are gone, and they were three different lookups — the
# first two resolved to nothing.
#
# This only ever matches strings that are already identical apart from separators,
# so it cannot invent a link between two conditions: "hypertension" and
# "hypotension" compact to different words and stay apart. What it removes is a
# class of miss that has nothing to do with medicine and everything to do with how
# somebody typed.
_COMPACT_INDEX: dict[str, str] = {}
for _alias, _target in _ALIAS_INDEX.items():
    _COMPACT_INDEX.setdefault(re.sub(r"[^a-z0-9]+", "", _alias), _target)


def _compact(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


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
    if (compact := _compact(norm)) in _COMPACT_INDEX:
        return _COMPACT_INDEX[compact]
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


def condition_matches_term(condition: str, term: str) -> bool:
    """`term_in_condition`, plus the synonym knowledge this module already holds.

    `term_in_condition` compares strings. It does not consult the alias table, so a
    contraindication written under one of two names for the same disease never fires
    against the other — and this module's whole reason for existing is that it knows
    they are the same disease.

    Three live examples, all silent:
      - `raktamokshana.hard.hypotension` — a HARD bar on bloodletting. The app
        records that condition as `low_blood_pressure`, which is listed right here
        as an alias of `hypotension`. The bar had never once fired.
      - `vamana.soft.gerd` and `snehapana_home.soft.gerd` — the app records
        `acid_reflux`, of which `gerd` is a listed alias.
      - `snehapana_home.soft.hypercholesterolemia` — the app records
        `high_cholesterol`.

    Matching is still safe-biased and still refuses raw substrings: the extra path
    fires only when the vocabulary states outright that the two names resolve to one
    canonical condition. `hypotension` and `hypertension` normalise to different
    keys and stay distinct, which is the case the string matcher was written for.
    """
    if term_in_condition(condition, term):
        return True
    canon_c = normalize_condition(condition)
    canon_t = normalize_condition(term)
    if not canon_c or not canon_t:
        return False
    return canon_c == canon_t or term_in_condition(canon_c, canon_t)


def any_term_in_condition(condition: str, terms) -> bool:
    """True if any term in `terms` matches `condition` (precise word/phrase/stem)."""
    return any(term_in_condition(condition, t) for t in terms)


def condition_in_any_term(condition: str, terms) -> bool:
    """True if `condition` (as a word/phrase) appears inside any of `terms` — the
    reverse direction, for when a medicine's contraindication is more specific
    than the user's condition (contra='liver_disease' vs condition='liver')."""
    return any(term_in_condition(t, condition) for t in terms)
