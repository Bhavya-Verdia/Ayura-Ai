"""What a dietitian writes beside the meals: medicine-food interactions and condition notes.

The diet path read `current_medications` nowhere. A 62-year-old on warfarin and
metformin was planned a fruit-only Monday fast and a week of leafy greens that
varied from none to a katori a day — the variation, not the amount, is what moves an
INR. Interactions here are the well-established ones a dietitian checks first, each
with its source; where the interaction is "avoid this food", the food is screened out
of the plan the same way a condition's Apathya is (`screen_protocols`), and where it
is a habit — timing, consistency — it is a note.

Authored, NOT clinically reviewed. Matching is on generic names and the brand names
most common in India; anything unmatched is listed back so it is not read as checked.
"""
from __future__ import annotations

import re

# key: (label, aliases, advice, exclude_terms, source)
MEDICATIONS = {
    "warfarin": (
        "Warfarin / acenocoumarol (blood thinner)",
        ("warfarin", "coumadin", "acenocoumarol", "acitrom", "nicoumalone", "sintrom"),
        "Keep vitamin K steady rather than low: the same amount of leafy greens (palak, "
        "methi, cabbage) each day, not none one week and a lot the next. No high-dose "
        "turmeric, ginger or garlic supplements. Tell your doctor before any big change "
        "in diet.",
        (), "NIH Office of Dietary Supplements, Vitamin K fact sheet; Holbrook et al., Arch Intern Med 2005"),
    "levothyroxine": (
        "Levothyroxine (thyroid hormone)",
        ("levothyroxine", "thyroxine", "thyronorm", "eltroxin", "thyrox", "synthroid", "lethyrox"),
        "Take it on an empty stomach 30-60 minutes before breakfast. Keep soy, calcium "
        "or iron tablets, coffee and high-fibre foods at least 4 hours away from the dose.",
        (), "American Thyroid Association guidelines for hypothyroidism (2014)"),
    "metformin": (
        "Metformin",
        ("metformin", "glycomet", "glucophage", "gluconorm", "obimet"),
        "Take with meals. Long-term use lowers vitamin B12 — include milk, curd or a "
        "fortified food daily and ask for a B12 test once a year.",
        (), "ADA Standards of Care in Diabetes (2024), section 9"),
    "hypoglycaemic": (
        "Insulin or a sulfonylurea (glimepiride, gliclazide, glipizide)",
        ("insulin", "glimepiride", "amaryl", "gliclazide", "glizid", "glipizide",
         "glibenclamide", "glyburide", "daonil", "repaglinide"),
        "Do not skip or delay meals, and keep the snack. Carry glucose tablets or sugar "
        "for a low. Fasting days are not planned for you.",
        (), "ADA Standards of Care in Diabetes (2024), section 6"),
    "statin": (
        "Statin (atorvastatin, simvastatin, lovastatin)",
        ("atorvastatin", "simvastatin", "lovastatin", "atorva", "lipitor", "zocor"),
        "Avoid grapefruit and grapefruit juice, which raise the level of these statins.",
        ("grapefruit", "chakotra"), "US FDA drug labelling (atorvastatin, simvastatin, lovastatin)"),
    "maoi": (
        "MAO inhibitor (or linezolid)",
        ("phenelzine", "tranylcypromine", "isocarboxazid", "selegiline", "moclobemide",
         "linezolid"),
        "Avoid tyramine-rich foods: aged cheese, fermented soy (tempeh, soy sauce), "
        "pickles and anything overripe or fermented for long.",
        ("aged cheese", "cheddar", "tempeh", "soy sauce", "pickle", "achar", "fermented"),
        "US FDA labelling for MAO inhibitors; Gardner et al., J Clin Psychiatry 1996"),
    "potassium_raising": (
        "ACE inhibitor, ARB or spironolactone",
        ("ramipril", "enalapril", "lisinopril", "perindopril", "telmisartan", "losartan",
         "olmesartan", "valsartan", "spironolactone", "eplerenone", "aldactone", "telma",
         "losar", "olmezest"),
        "These raise potassium. Do not use a potassium salt substitute (\"low sodium "
        "salt\"), and do not add large amounts of banana, coconut water or tomato on top "
        "of the plan without asking your doctor.",
        ("salt substitute", "low sodium salt", "lo salt"),
        "KDIGO 2021 blood pressure in CKD; US FDA labelling"),
    "lithium": (
        "Lithium",
        ("lithium", "licab", "lithosun"),
        "Keep salt and fluid intake steady day to day — a sudden low-salt or low-fluid "
        "day raises the lithium level.",
        (), "NICE CG185 (bipolar disorder), lithium monitoring"),
    "iron": (
        "Iron tablets",
        ("ferrous", "iron tablet", "ifa", "livogen", "orofer", "dexorange", "autrin"),
        "Take with a vitamin C food (amla, orange, guava) and keep tea, coffee, milk and "
        "calcium at least 2 hours away.",
        (), "ICMR-NIN (2020); Anemia Mukt Bharat guidance"),
    "calcium": (
        "Calcium tablets",
        ("calcium carbonate", "shelcal", "calcimax", "calcium citrate"),
        "Take with food, and at least 4 hours apart from thyroid or iron tablets.",
        (), "NIH Office of Dietary Supplements, Calcium fact sheet"),
}

# condition key: (label, note, source)
CONDITION_NOTES = {
    "anemia": ("Anaemia",
               "Food alone does not correct anaemia — keep taking any iron or folic acid "
               "you were prescribed. Pair iron-rich foods (greens, dal, ragi, dates) with "
               "vitamin C, and keep tea and coffee an hour away from meals.",
               "ICMR-NIN (2020); Anemia Mukt Bharat"),
    "diabetes": ("Diabetes",
                 "Keep carbohydrate similar at each main meal, from whole grains and "
                 "pulses. Check your sugar if a day feels unusual, and treat a low (under "
                 "70 mg/dL) with glucose, not with the next meal.",
                 "ADA Standards of Care in Diabetes (2024)"),
    "kidney_disease": ("Kidney disease",
                       "Potassium and phosphorus limits depend on your blood results; "
                       "leaching vegetables (cut, soak, boil and discard the water) lowers "
                       "potassium. No salt substitutes. Protein is capped in this plan.",
                       "KDIGO 2020 nutrition in CKD"),
    "hypertension": ("High blood pressure",
                     "Salt under 5 g a day (about one level teaspoon in all), and none from "
                     "pickles, papad or packaged snacks. The plan is built the DASH way: "
                     "vegetables, fruit, pulses and whole grains.",
                     "WHO sodium guideline (2023); DASH trial"),
    "heart_disease": ("Heart disease",
                      "Fat is kept to about a quarter of energy and saturated fat low; "
                      "ghee in small measured amounts. Fried foods are left out.",
                      "AHA/ACC 2019; AHA dietary guidance 2021"),
    "high_cholesterol": ("High cholesterol",
                         "Oats, barley and pulses supply the soluble fibre that lowers LDL; "
                         "saturated fat is kept under 7% of energy.",
                         "AHA dietary guidance 2021"),
    "gout": ("Gout",
             "Drink 2.5-3 L of water a day unless told otherwise, avoid sweetened drinks "
             "and alcohol, and keep weight steady — crash diets raise uric acid.",
             "ACR gout guideline (2020)"),
    "celiac": ("Coeliac disease",
               "Strictly gluten-free, including cross-contamination: separate flour, tawa "
               "and utensils. Oats only if certified gluten-free. Most hing (asafoetida) "
               "sold in India is mixed with wheat flour — use a labelled gluten-free one.",
               "ACG coeliac guideline (2023)"),
    "lactose_intolerance": ("Lactose intolerance",
                            "Curd and buttermilk are usually better tolerated than milk; small "
                            "amounts of milk with a meal often are too.",
                            "NIDDK, lactose intolerance"),
    "ibs": ("IBS",
            "If symptoms persist, a 4-6 week low-FODMAP trial with a dietitian is the "
            "evidence-based next step.",
            "ACG IBS guideline (2021)"),
    "ibd": ("Crohn's disease / ulcerative colitis",
            "Protein is raised for inflammatory bowel disease. During a flare, or if you "
            "have a stricture, you need a low-fibre (low-residue) version — tell your "
            "gastroenterologist. Iron, vitamin B12 and vitamin D are often low; ask for "
            "them to be checked.",
            "ESPEN guideline on clinical nutrition in IBD (2023)"),
    "osteoporosis": ("Osteoporosis",
                     "Aim for 1000-1200 mg calcium a day (milk, curd, ragi, sesame, paneer) "
                     "and adequate vitamin D; protein at every meal.",
                     "ICMR-NIN (2020); NOF clinician's guide"),
    "hypothyroid": ("Hypothyroidism",
                    "Cooked brassicas and soy are fine in normal amounts; keep them away "
                    "from the thyroid tablet, not out of the diet.",
                    "American Thyroid Association (2014)"),
    "pcos": ("PCOS",
             "A 5-10% weight loss improves cycles and insulin resistance; whole grains, "
             "pulses and protein at each meal keep glucose steady.",
             "International PCOS guideline (2023)"),
    "fatty_liver": ("Fatty liver",
                    "A 7-10% weight loss reduces liver fat; avoid sweetened drinks and "
                    "refined flour.", "AASLD NAFLD guidance (2023)"),
    "kidney_stones": ("Kidney stones",
                      "Drink enough to pass 2.5 L of urine a day, keep salt low, and do not "
                      "cut dairy — normal calcium lowers stone risk.",
                      "AUA kidney stone guideline (2019)"),
    "pregnancy": ("Pregnancy",
                  "Keep taking the iron-folic acid and calcium your doctor prescribed, use "
                  "iodised salt, and avoid raw papaya, unpasteurised milk and large doses "
                  "of any herb.",
                  "ICMR-NIN (2020); MoHFW antenatal guidance"),
}

_IBD = re.compile(r"crohn|colitis|\bibd\b|inflammatory bowel", re.I)


def has_ibd(user_profile: dict) -> bool:
    return any(_IBD.search(str(c)) for c in user_profile.get("medical_history") or [])


def medication_matches(user_profile: dict) -> tuple[list[dict], list[str]]:
    """([interaction dicts], [medications nothing matched])."""
    found, unmatched, seen = [], [], set()
    for med in user_profile.get("current_medications") or []:
        text = str(med).lower()
        hit = False
        for key, (label, aliases, advice, exclude, source) in MEDICATIONS.items():
            if any(re.search(rf"\b{re.escape(a)}", text) for a in aliases):
                hit = True
                if key not in seen:
                    seen.add(key)
                    found.append({"key": key, "medication": label, "advice": advice,
                                  "avoid": list(exclude), "source": source})
        if not hit and text.strip():
            unmatched.append(str(med))
    return found, unmatched


def screen_protocols(user_profile: dict) -> dict:
    """Medication exclusions in the `extra_terms` shape the food screen reads, keyed by
    a pseudo-condition so they pass through the same scans as an Apathya. Also the
    one age rule that is a food rather than an energy figure: no caffeine under 18
    (AAP), which put green tea in a 12-year-old's plan."""
    out = {}
    try:
        child = int(user_profile.get("age") or 99) < 18
    except (TypeError, ValueError):
        child = False
    if child:
        out["child_caffeine"] = {"name": "Under 18", "reason": "No caffeine for children (AAP).",
                                 "terms": ["green tea", "black tea", "coffee", "espresso"]}
    for m in medication_matches(user_profile)[0]:
        if m["avoid"]:
            out[f"med_{m['key']}"] = {"name": m["medication"],
                                      "reason": f"Interacts with {m['medication']}.",
                                      "terms": m["avoid"]}
    return out


def clinical_notes(user_profile: dict, conditions: list[str]) -> list[dict]:
    notes, seen = [], set()
    keys = [str(c).lower() for c in conditions]
    if has_ibd(user_profile):
        keys.insert(0, "ibd")
    if user_profile.get("pregnancy_or_nursing") and str(
            user_profile.get("pregnancy_status") or "pregnant").lower() != "nursing":
        keys.insert(0, "pregnancy")
    aliases = {"diabetes_type2": "diabetes", "diabetes_type1": "diabetes",
               "chronic_kidney_disease": "kidney_disease", "hypothyroidism": "hypothyroid",
               "lactose": "lactose_intolerance", "anaemia": "anemia"}
    for k in keys:
        k = aliases.get(k, k)
        if k in CONDITION_NOTES and k not in seen:
            seen.add(k)
            label, note, source = CONDITION_NOTES[k]
            notes.append({"topic": label, "note": note, "source": source})
    return notes


# ── What the person will eat ─────────────────────────────────────────────────

# Jain: no root or underground vegetables (they are uprooted with the life in them),
# no honey, no mushrooms or fermented foods kept overnight. Dry ginger (saunth) is
# taken; fresh ginger is a root and is not.
_JAIN_TERMS = ("onion", "garlic", "potato", "aloo", "carrot", "beetroot", "radish", "mooli",
               "sweet potato", "yam", "suran", "colocasia", "arbi", "fresh ginger",
               "turnip", "honey", "mushroom", "lotus stem")
# Not "kand": raw banana's library name is Kadali Kanda, and it grows above ground.

# What people type when they say what they will not eat, in the words the food
# library uses. The scans' own vernacular map carries ~80 words chosen for safety
# terms; these are the everyday vegetable and staple names a dislike is written in.
_DISLIKE_WORDS = {
    "lauki": "bottle gourd", "ghiya": "bottle gourd", "dudhi": "bottle gourd",
    "turai": "ridge gourd", "tori": "ridge gourd", "tinda": "tinda", "parwal": "parwal",
    "kaddu": "pumpkin", "bhopla": "pumpkin", "bhindi": "okra", "ladyfinger": "okra",
    "gobhi": "cauliflower", "phool gobhi": "cauliflower", "patta gobhi": "cabbage",
    "baingan": "brinjal", "eggplant": "brinjal", "karela": "bitter gourd",
    "palak": "spinach", "methi": "methi", "arbi": "colocasia", "shakarkandi": "sweet potato",
    "kathal": "jackfruit", "matar": "peas", "mushroom": "mushroom", "shimla mirch": "capsicum",
    "rajma": "rajma", "chole": "chhole", "chana": "chana", "arhar": "toor", "toor": "toor",
    "masoor": "masoor", "moong": "moong", "urad": "urad", "besan": "besan",
    "suji": "semolina", "rava": "semolina", "dalia": "broken wheat", "daliya": "broken wheat",
    "sabudana": "sabudana", "makhana": "makhana", "dahi": "curd", "chaas": "buttermilk",
    "gud": "jaggery", "kela": "banana", "papita": "papaya", "anar": "pomegranate",
    "amrood": "guava", "ragi": "ragi", "bajra": "bajra", "jowar": "jowar",
}
_NO_ONION_GARLIC = ("onion", "garlic", "pyaz", "lehsun")
_CUISINE = {
    "north_indian": "North Indian (roti, dal, sabzi, khichdi, kadhi, paratha)",
    "south_indian": "South Indian (idli, dosa, upma, sambar, rasam, poriyal, curd rice)",
    "east_indian": "East Indian (rice, dal, shukto, light vegetable jhol, chirer pulao)",
    "west_indian": "West Indian (bhakri, thepla, dhokla, varan bhat, kadhi, poha)",
}


def preference_protocols(diet_prefs: dict) -> dict:
    """Dislikes and restrictions as pseudo-condition protocols for the food screen."""
    out = {}
    restrictions = set(diet_prefs.get("dietary_restrictions") or [])
    if "jain" in restrictions:
        out["pref_jain"] = {"name": "Jain diet", "reason": "Not eaten on a Jain diet.",
                            "terms": list(_JAIN_TERMS)}
    elif "no_onion_garlic" in restrictions:
        out["pref_no_onion_garlic"] = {"name": "No onion or garlic",
                                       "reason": "You do not eat onion or garlic.",
                                       "terms": list(_NO_ONION_GARLIC)}
    dislikes = []
    for d in diet_prefs.get("food_dislikes") or []:
        word = str(d).strip().lower()
        if len(word) >= 3:
            dislikes.append(word)
            if word in _DISLIKE_WORDS:
                dislikes.append(_DISLIKE_WORDS[word])
    if dislikes:
        out["pref_dislikes"] = {"name": "Foods you dislike", "reason": "You said you do not eat this.",
                                "terms": dislikes}
    return out


def preference_brief_lines(diet_prefs: dict) -> list[str]:
    lines = []
    cuisine = diet_prefs.get("cuisine_preference") or "any"
    if cuisine in _CUISINE:
        lines.append(f"CUISINE: lean toward {_CUISINE[cuisine]} dishes the patient grew up with.")
    restrictions = set(diet_prefs.get("dietary_restrictions") or [])
    if "jain" in restrictions:
        lines.append("JAIN: no root or underground vegetables (onion, garlic, potato, carrot, "
                     "beetroot, radish, fresh ginger, yam), no honey, no mushrooms; dry ginger "
                     "is fine. Last meal before sunset.")
    elif "no_onion_garlic" in restrictions:
        lines.append("NO ONION OR GARLIC in any meal; use hing, ginger and cumin for flavour.")
    if diet_prefs.get("food_dislikes"):
        lines.append("DOES NOT EAT: " + ", ".join(diet_prefs["food_dislikes"]) + ".")
    return lines
