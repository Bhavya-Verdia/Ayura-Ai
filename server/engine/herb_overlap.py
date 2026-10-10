"""Which prescribed herbs is the patient already taking?

A patient on Ashwagandha Churna who is prescribed a formulation containing
Ashwagandha takes it twice. Panchakarma had a check for this and the medicines
plan did not. Medicines is the feature that prescribes the most formulations, and
it is the one a patient is most likely to combine with what they already take.

One matcher serves both. The Panchakarma copy compared raw substrings in both
directions over 28 herbs, so a one-letter entry matched everything and
"Shankhapushpi" never matched "Shankhpushpi". This one works on words, from a
vocabulary built from the two knowledge bases. It:

* folds spellings onto one name (shunti/shunthi, neem/nimba, amla/amalaki,
  vasaka/vasa)
* expands compounds into what is in them, so Triphala overlaps Haritaki and
  Trikatu overlaps Pippali
* ignores carriers. Ghee, honey, jaggery and sesame oil are the vehicle half
  the formulations are made in, and flagging Brahmi Ghrita for "ghee" would
  teach a reader to skip the warning.
* reads "Ashwagandharishta" as Ashwagandha. Patients write the preparation as
  often as the herb, and the classical names fuse the two.

A match is flagged, never withheld. Usually the fix is to stop the one the patient
is taking on their own, not to change a prescribed formulation. That decision
belongs to the patient and their Vaidya.
"""
from __future__ import annotations

import json
import os
import re

_KB = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base")

# The same herb under the names patients and the two KBs actually use.
_SYNONYMS = {
    "shunti": "shunthi", "sunthi": "shunthi", "sonth": "shunthi",
    "manjishtha": "manjistha", "manjishta": "manjistha",
    "kutki": "katuka", "katuki": "katuka",
    "amla": "amalaki", "amlaki": "amalaki", "amalaki": "amalaki",
    "tvak": "twak",
    "neem": "nimba",
    "vasaka": "vasa", "adulsa": "vasa",
    "shankhpushpi": "shankhapushpi", "shankpushpi": "shankhapushpi",
    "mulethi": "yashtimadhu", "licorice": "yashtimadhu",
    "liquorice": "yashtimadhu",
    "turmeric": "haridra", "haldi": "haridra",
    "giloy": "guduchi",
    "gokshur": "gokshura", "gokhru": "gokshura",
    "pipli": "pippali", "pipal": "pippali",
    "arjun": "arjuna",
    "shilajeet": "shilajit", "shilajatu": "shilajit",
    "guggul": "guggulu",
    "dashmool": "dashamoola", "dashamool": "dashamoola", "dashmoola": "dashamoola",
    "chyavanprash": "chyawanprash", "chyawanprasha": "chyawanprash",
    "triphla": "triphala",
    "harad": "haritaki", "harde": "haritaki",
    "baheda": "bibhitaki", "bahera": "bibhitaki",
    "jatamamsi": "jatamansi",
    "tulsi": "tulasi",
    # Classical synonyms the KB's own ingredient lists use.
    "abhaya": "haritaki", "pathya": "haritaki",
    "dhatri": "amalaki",
    "vibhitaki": "bibhitaki",
    "amrita": "guduchi", "amruta": "guduchi", "amrutha": "guduchi",
    "nisha": "haridra",
    "vishwa": "shunthi", "nagara": "shunthi", "ginger": "shunthi",
    "nagarmotha": "musta",
    "bilwa": "bilva", "kutaj": "kutaja", "jeeraka": "jeera",
    "ajamoda": "ajmoda", "ajowan": "ajmoda",
    "kapikachu": "kapikacchu", "lauha": "loha", "abhrak": "abhraka",
    "suvarna": "swarna", "aloe": "kumari",
}

# Compounds named as one ingredient, expanded into what is in them.
_COMPOUNDS = {
    "triphala": {"amalaki", "bibhitaki", "haritaki"},
    "trikatu": {"shunthi", "maricha", "pippali"},
}

# The vehicle or the flavour, not the medicine.
_CARRIERS = {
    "ghee", "ghrita", "go", "honey", "madhu", "jaggery", "guda", "gur", "sita", "sugar",
    "sesame", "tila", "saindhava", "lavana", "salt", "water", "milk", "ksheera",
    "ela", "twak", "tejpatra", "lavanga", "sitopala", "coconut", "beeswax",
    "cardamom", "cinnamon", "dalchini",
}

# Words the KB's ingredient strings carry that name no herb: "Other herbs",
# "Self-generated alcohol", "Rock salt", "Shuddha Gandhaka". Left in the
# vocabulary, a patient typing "dry ginger" would match on "dry".
_NOISE = {
    "and", "other", "herbs", "total", "classical", "self", "generated", "alcohol",
    "cow", "rock", "dry", "green", "true", "more", "dravyas", "stem", "flowers",
    "shuddha", "vata", "vatahara", "tikta", "moola", "hara", "kala", "vera", "nal",
    "indu", "satva", "vida", "fresh", "pure", "organic", "with", "the",
}

# How the herb is prepared. Dropped from what a patient typed, so "Brahmi
# Ghrita" reads as Brahmi.
_FORMS = {
    "churna", "churnam", "vati", "vatika", "gutika", "tablet", "tablets", "tab", "tabs",
    "capsule", "capsules", "cap", "caps", "ghritam", "taila", "tailam", "oil", "kwath",
    "kwatha", "kashayam", "kashaya", "asava", "arishta", "avaleha", "lehyam", "leha",
    "rasayana", "powder", "syrup", "juice", "extract", "bhasma", "pishti", "leaf",
    "root", "bark", "seed", "fruit", "base", "daily", "twice", "once",
}


def _canon(word: str) -> str:
    return _SYNONYMS.get(word, word)


def _load_vocabulary() -> set[str]:
    vocab: set[str] = set(_COMPOUNDS) | set(_SYNONYMS.values())
    try:
        with open(os.path.join(_KB, "ayurvedic_medicines.json")) as f:
            for med in json.load(f):
                for ing in med.get("ingredients") or []:
                    for w in _words(ing.split(" (")[0]):
                        vocab.add(_canon(w))
    except (OSError, ValueError):
        pass
    try:
        with open(os.path.join(_KB, "panchakarma_clinical.json")) as f:
            for key in (json.load(f).get("herbs") or {}):
                for w in key.split("_"):
                    vocab.add(_canon(w))
    except (OSError, ValueError):
        pass
    return {w for w in vocab
            if len(w) >= 3 and w not in _CARRIERS and w not in _FORMS and w not in _NOISE}


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z]+", str(text).lower()) if w]


_VOCAB = _load_vocabulary()
# Longest first, so "ashwagandharishta" reads as ashwagandha and not as some
# shorter herb that happens to prefix it.
_PREFIXES = sorted((w for w in _VOCAB | set(_SYNONYMS) if len(w) >= 5),
                   key=len, reverse=True)


def herbs_in(text: str) -> set[str]:
    """The canonical herbs a free-text entry or an ingredient name refers to."""
    found: set[str] = set()
    for raw in _words(text):
        w = _canon(raw)
        if w in _CARRIERS or w in _FORMS or w in _NOISE or len(w) < 3:
            continue
        if w not in _VOCAB:
            w = next((p for p in _PREFIXES if w.startswith(p)), None)
            if not w:
                continue
            w = _canon(w)
        found |= _COMPOUNDS.get(w, {w})
    return found


def already_taking(ingredients: list[str], taken: list[str]) -> list[dict]:
    """Each declared medicine that overlaps these ingredients, with the overlap.

    `ingredients` are display names ("Haritaki (Terminalia chebula)") or KB keys;
    `taken` is what the patient typed.
    """
    by_herb: dict[str, str] = {}
    for ing in ingredients or []:
        label = str(ing).split(" (")[0].replace("_", " ").strip()
        for h in herbs_in(label):
            by_herb.setdefault(h, label.title() if label.islower() else label)
    hits = []
    for entry in taken or []:
        shared = sorted({by_herb[h] for h in herbs_in(entry) if h in by_herb})
        if shared:
            hits.append({"already_taking": str(entry).strip(), "herbs": shared})
    return hits


def declared_ayurvedic(prefs_doc: dict | None) -> list[str]:
    """Every Ayurvedic medicine the patient has said they take, from either form.

    It is asked on the Panchakarma form and on the remedies form, and both
    engines prescribe herbs. A medicine declared on one form has to reach the
    check on the other.
    """
    seen: dict[str, str] = {}
    for feature in ("panchakarma", "remedies"):
        for m in ((prefs_doc or {}).get(feature) or {}).get("current_ayurvedic_medicines") or []:
            m = str(m).strip()
            if m:
                seen.setdefault(m.lower(), m)
    return list(seen.values())
