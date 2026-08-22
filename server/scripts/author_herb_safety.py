"""One-shot authoring pass: per-herb safety for every Aushadha the engine prescribes.

Run once; the result is committed into `panchakarma_clinical.json` under `herbs`,
and into `panchakarma_protocols.json` as a `components` list on each Sahayoga Dravya
formulation. Kept in the tree as the record of what was authored and why.

## The problem it fixes

The seven Sahayoga Dravya adjuvants — the compound formulations added alongside the
Pradhana Karma for a patient's specific conditions — passed no contraindication gate
at all. They were selected on an indication match and handed over: Shilajit to a
patient with chronic kidney disease, Guggulu to one on thyroxine, Sarpagandha to
someone with depression, Ashwagandha to a hyperthyroid patient. The formulation's
own `caution` field said "avoid in hypotension" for Sarpagandha and nothing read it.

## Why the herb and not the formulation

Ashwagandha's thyroid interaction is a fact about Ashwagandha. It appears in
`manovaha_aushadha`, in the `vata_neurological` Rasayana and in the
`reproductive_male` Rasayana, and gating each formulation separately would mean
authoring it three times and having it drift. Keyed by herb, one entry covers every
place the engine can prescribe it.

It also gives the right REMEDY. A contraindication against one component is a reason
to withhold that component, not the four-herb formulation around it — withholding
the whole thing would deny a psoriasis patient their Kushtha Chikitsa because one
constituent interacts with their warfarin.

NOT CLINICALLY REVIEWED. Every entry states its mechanism so a reviewer can reject
one claim without discarding the table.
"""
import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

KB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base"))
CLINICAL = os.path.join(KB, "panchakarma_clinical.json")
PROTOCOLS = os.path.join(KB, "panchakarma_protocols.json")

# ── Which herbs each formulation actually contains ────────────────────────────
# Parsed out of the `name` strings, which are display prose ("Guduchi + Haridra +
# Amalaki (Triphala Churna) + Shilajit") and cannot be gated as text.
COMPONENTS = {
    "kushtha_aushadha": ["tikta_ghrita", "khadiradi_vati", "manjistha"],
    "medovaha_aushadha": ["guduchi", "haridra", "amalaki", "shilajit"],
    "artava_aushadha": ["shatavari", "ashoka", "dashamoola", "shatapushpa"],
    "manovaha_aushadha": ["brahmi", "ashwagandha", "jatamansi", "shankhpushpi"],
    "pranavaha_aushadha": ["vasaka", "kantakari", "sitopaladi", "talisadi"],
    "annavaha_aushadha": ["kutaja", "bilva", "dadima", "amalaki", "guduchi"],
    "raktavaha_aushadha": ["arjuna", "punarnava", "sarpagandha"],
}

RASAYANA_COMPONENTS = {
    "general_immunity": ["chyawanprash"],
    "vata_neurological": ["ashwagandha"],
    "pitta_inflammatory": ["amalaki"],
    "kapha_metabolic": ["shilajit", "guggulu"],
    "reproductive_female": ["shatavari"],
    "reproductive_male": ["ashwagandha", "kapikacchu"],
    "bone_joint": ["guggulu"],
    "medhya_brain": ["brahmi"],
}

# ── Per-herb safety ───────────────────────────────────────────────────────────
# `display` is what a patient sees when the component is named or withheld.
# `hard` withholds the component. `soft` keeps it with a stated modification.
# `medication_classes` feed the existing drug-herb interaction checker.
HERBS = {
    "ashwagandha": {
        "display": "Ashwagandha",
        "hard": {
            "hyperthyroidism": "Raises T3 and T4; adding it to a thyrotoxic state worsens it.",
            "pregnancy": "Traditionally abortifacient in higher doses; withheld pending Vaidya supervision.",
        },
        "soft": {
            "autoimmune": "Immunostimulant — may aggravate autoimmune activity. Introduce alone and monitor.",
            "hypothyroidism": "Raises thyroid hormone, so thyroxine dose may need review — check TFTs at 6 weeks.",
            "depression": "Sedating at higher doses; take the evening dose only and review if fatigue worsens.",
        },
        "medication_classes": ["thyroid_hormone", "sedatives", "immunosuppressants"],
    },
    "shilajit": {
        "display": "Shilajit",
        "hard": {
            "chronic_kidney_disease": "Mineral pitch with a substantial mineral and fulvic acid load that a reduced GFR cannot clear.",
            "kidney_disease": "As chronic kidney disease — mineral load requires intact renal clearance.",
            "hemochromatosis": "Iron-rich; contraindicated where iron already accumulates.",
            "gout": "Purine and mineral load can precipitate an attack.",
        },
        "soft": {
            "hypertension": "Some preparations carry a sodium load — use a purified (Shodhita) grade and monitor BP.",
            "diabetes_type2": "Lowers blood glucose; monitor alongside oral hypoglycaemics.",
        },
        "medication_classes": ["diabetes_meds"],
    },
    "guggulu": {
        "display": "Guggulu",
        "hard": {
            "pregnancy": "Uterine stimulant — contraindicated throughout pregnancy.",
            "hyperthyroidism": "Guggulsterones are thyroid-stimulating and worsen a thyrotoxic state.",
            "ibd_crohns": "Gastric irritant; aggravates active inflammatory bowel disease.",
            "ulcerative_colitis": "As IBD — irritant to inflamed bowel mucosa.",
        },
        "soft": {
            "hypothyroidism": "Thyroid-stimulating, so it may reduce the thyroxine requirement — check TFTs.",
            "gastritis": "Take after food; Guggulu is a known gastric irritant.",
            "bleeding_disorder": "Mild antiplatelet effect — avoid around any procedure.",
        },
        "medication_classes": ["thyroid_hormone", "blood_thinners"],
    },
    "sarpagandha": {
        "display": "Sarpagandha (Rauwolfia)",
        "hard": {
            "depression": "Reserpine depletes central monoamines and is a documented cause of drug-induced depression, including suicidality. This is the sharpest entry in the table: the formulation was previously given on a hypertension match with no check for a psychiatric history.",
            "bipolar": "As depression — reserpine can precipitate a depressive episode.",
            "ptsd": "As depression — monoamine depletion in a patient with active psychiatric illness.",
            "hypotension": "Potent antihypertensive; the formulation's own caution field said so and nothing read it.",
            "pregnancy": "Crosses the placenta; associated with neonatal depression and nasal congestion.",
            "peptic_ulcer": "Increases gastric acid secretion.",
            "parkinson": "Monoamine depletion worsens parkinsonism directly.",
        },
        "soft": {
            "hypertension": "Only under qualified Vaidya supervision, and only if BP remains raised after Panchakarma — not as a first measure.",
        },
        "medication_classes": ["blood_pressure_meds", "antidepressants", "sedatives"],
    },
    "guduchi": {
        "display": "Guduchi (Tinospora)",
        "hard": {},
        "soft": {
            "autoimmune": "Immunomodulatory — may aggravate autoimmune activity; introduce alone.",
            "fatty_liver": "Rare idiosyncratic hepatitis is reported with prolonged use; limit to 6 weeks and check LFTs.",
            "hepatitis": "As fatty liver — monitor LFTs and stop at any rise.",
            "diabetes_type2": "Lowers blood glucose; monitor with oral hypoglycaemics.",
        },
        "medication_classes": ["diabetes_meds", "immunosuppressants"],
    },
    "amalaki": {
        "display": "Amalaki (Amla)",
        "hard": {
            "hemochromatosis": "Vitamin C content markedly enhances non-haem iron absorption.",
        },
        "soft": {
            "acid_reflux": "Sour (Amla Rasa) — take with food or after it, never on an empty stomach.",
            "bleeding_disorder": "Mild antiplatelet effect; stop a week before any procedure.",
            "diabetes_type2": "Lowers blood glucose; monitor with oral hypoglycaemics.",
        },
        "medication_classes": ["blood_thinners", "diabetes_meds"],
    },
    "haridra": {
        "display": "Haridra (Turmeric)",
        "hard": {
            "gallstones": "Stimulates gallbladder contraction and can impact a stone in the cystic duct.",
        },
        "soft": {
            "bleeding_disorder": "Antiplatelet effect at therapeutic doses; stop before any procedure.",
            "acid_reflux": "Can aggravate reflux at higher doses; take with food.",
        },
        "medication_classes": ["blood_thinners"],
    },
    "brahmi": {
        "display": "Brahmi (Bacopa)",
        "hard": {},
        "soft": {
            "hypothyroidism": "Raises T4 in animal studies — check TFTs if taken long term.",
            "bradycardia": "Can slow the heart rate further.",
            "asthma": "Cholinergic effect may aggravate bronchospasm; stop at any tightness.",
        },
        "medication_classes": ["thyroid_hormone", "sedatives"],
    },
    "jatamansi": {
        "display": "Jatamansi",
        "hard": {},
        "soft": {
            "hypotension": "Sedative and mildly hypotensive; rise slowly.",
            "depression": "Sedating — take at night only and review if daytime fatigue worsens.",
        },
        "medication_classes": ["sedatives", "antidepressants"],
    },
    "shankhpushpi": {
        "display": "Shankhpushpi",
        "hard": {},
        "soft": {
            "hypotension": "Mildly hypotensive and sedative.",
            "epilepsy": "Reported to reduce phenytoin levels — do not take within 2 hours of an anticonvulsant.",
        },
        "medication_classes": ["sedatives", "anticonvulsants"],
    },
    "shatavari": {
        "display": "Shatavari",
        "hard": {
            "fibroids": "Phytoestrogenic; contraindicated where an oestrogen-sensitive tumour is present.",
        },
        "soft": {
            "pcos": "Phytoestrogenic — beneficial in Artava Kshaya but review with the treating physician in oestrogen-dominant PCOS.",
            "obesity": "Guru and Brimhana; increases Kapha and weight.",
        },
        "medication_classes": ["oral_contraceptives"],
    },
    "kapikacchu": {
        "display": "Kapikacchu (Mucuna)",
        "hard": {
            "parkinson": "Contains L-DOPA. Taken alongside prescribed levodopa it stacks the dose unpredictably — a Vaidya and the treating neurologist must set this together.",
            "psychosis": "Dopaminergic — can precipitate or worsen psychosis.",
        },
        "soft": {
            "depression": "Dopaminergic; may interact with antidepressants — introduce alone.",
        },
        "medication_classes": ["antidepressants"],
    },
    "punarnava": {
        "display": "Punarnava",
        "hard": {},
        "soft": {
            "chronic_kidney_disease": "Diuretic — monitor electrolytes and fluid balance.",
            "hypotension": "Diuretic action can lower blood pressure further.",
        },
        "medication_classes": ["blood_pressure_meds"],
    },
    "arjuna": {
        "display": "Arjuna",
        "hard": {},
        "soft": {
            "hypotension": "Mildly hypotensive and negatively chronotropic.",
            "heart_disease": "Cardioactive — must be added to, never substituted for, prescribed cardiac medication.",
        },
        "medication_classes": ["blood_pressure_meds"],
    },
    "vasaka": {
        "display": "Vasaka (Adhatoda)",
        "hard": {
            "pregnancy": "Oxytocic — contraindicated throughout pregnancy.",
        },
        "soft": {
            "bleeding_disorder": "Mild antiplatelet effect.",
        },
        "medication_classes": [],
    },
    "kantakari": {
        "display": "Kantakari",
        "hard": {"pregnancy": "Solanaceous and traditionally avoided in pregnancy."},
        "soft": {},
        "medication_classes": [],
    },
    "sitopaladi": {
        "display": "Sitopaladi Churna",
        "hard": {},
        "soft": {
            "diabetes_type2": "Sugar-based (Sita) and classically taken with honey — use the sugar-free preparation and monitor glucose.",
        },
        "medication_classes": ["diabetes_meds"],
    },
    "talisadi": {
        "display": "Talisadi Churna",
        "hard": {},
        "soft": {
            "diabetes_type2": "Sugar-based — use the sugar-free preparation.",
            "acid_reflux": "Contains Maricha and Pippali; can aggravate reflux.",
        },
        "medication_classes": ["diabetes_meds"],
    },
    "kutaja": {
        "display": "Kutaja",
        "hard": {"constipation_chronic": "Grahi (astringent, binding) — worsens constipation directly."},
        "soft": {},
        "medication_classes": [],
    },
    "bilva": {
        "display": "Bilva",
        "hard": {"constipation_chronic": "Grahi — binding, and aggravates constipation."},
        "soft": {"diabetes_type2": "Lowers blood glucose; monitor with oral hypoglycaemics."},
        "medication_classes": ["diabetes_meds"],
    },
    "dadima": {
        "display": "Dadima (Pomegranate)",
        "hard": {},
        "soft": {
            "hypertension": "Inhibits CYP3A4 and can raise levels of several antihypertensives.",
        },
        "medication_classes": ["blood_pressure_meds"],
    },
    "manjistha": {
        "display": "Manjistha",
        "hard": {"pregnancy": "Emmenagogue — traditionally avoided in pregnancy."},
        "soft": {"chronic_kidney_disease": "Colours the urine red, which can mask haematuria — warn the patient and their physician."},
        "medication_classes": [],
    },
    "khadiradi_vati": {
        "display": "Khadiradi Vati",
        "hard": {},
        "soft": {"dry_mouth": "Astringent and drying; sip water between doses."},
        "medication_classes": [],
    },
    "tikta_ghrita": {
        "display": "Tikta Ghrita",
        "hard": {
            "high_ama": "Ghrita over undigested Ama binds it deeper into the Srotas — Deepana-Pachana first.",
            "acute_pancreatitis": "A fat load is directly contraindicated in pancreatitis.",
        },
        "soft": {
            "high_cholesterol": "A daily ghee-based preparation needs lipid monitoring.",
            "obesity": "Guru and Snigdha — increases Kapha and Meda.",
        },
        "medication_classes": [],
    },
    "dashamoola": {
        "display": "Dashamoola",
        "hard": {},
        "soft": {"pregnancy": "Used postnatally in the tradition; during pregnancy only under Vaidya supervision."},
        "medication_classes": [],
    },
    "ashoka": {
        "display": "Ashoka",
        "hard": {},
        "soft": {
            "fibroids": "Phytoestrogenic — review with the treating physician where an oestrogen-sensitive tumour is present.",
            "amenorrhea": "Raktasthambhaka (styptic) — indicated for heavy bleeding, and the wrong direction for absent menses.",
        },
        "medication_classes": ["oral_contraceptives"],
    },
    "shatapushpa": {
        "display": "Shatapushpa",
        "hard": {"pregnancy": "Emmenagogue and uterine stimulant."},
        "soft": {},
        "medication_classes": [],
    },
    "chyawanprash": {
        "display": "Chyawanprash",
        "hard": {},
        "soft": {
            "diabetes_type2": "Sugar-based — use the sugar-free preparation and monitor glucose.",
            "hemochromatosis": "Amalaki-rich and therefore iron-absorption-enhancing.",
        },
        "medication_classes": ["diabetes_meds"],
    },
}


def main():
    with open(CLINICAL, encoding="utf-8") as f:
        clinical = json.load(f, object_pairs_hook=OrderedDict)

    clinical["herbs"] = OrderedDict(sorted(HERBS.items()))
    clinical["_herbs_note"] = (
        "Per-HERB safety, not per-formulation. Ashwagandha's thyroid interaction is a "
        "fact about Ashwagandha and applies in the Manovaha adjuvant, the "
        "vata_neurological Rasayana and the reproductive_male Rasayana alike; keying "
        "it to the herb means one entry rather than three that can drift. It also "
        "gives the right remedy: a contraindication against one component withholds "
        "THAT component, not the four-herb formulation around it. AUTHORED, NOT "
        "CLINICALLY REVIEWED."
    )

    with open(CLINICAL, "w", encoding="utf-8") as f:
        json.dump(clinical, f, indent=2, ensure_ascii=False)
        f.write("\n")

    with open(PROTOCOLS, encoding="utf-8") as f:
        protocols = json.load(f, object_pairs_hook=OrderedDict)

    for entry in protocols["aushadha_compendium"]["sahayoga_dravya"]:
        components = COMPONENTS[entry["id"]]
        unknown = [c for c in components if c not in HERBS]
        if unknown:
            raise SystemExit(f"{entry['id']}: components with no safety entry: {unknown}")
        entry["components"] = components

    rasayana = protocols["paschat_karma"]["rasayana_integration"]["rasayana_by_condition"]
    for key, entry in rasayana.items():
        components = RASAYANA_COMPONENTS[key]
        unknown = [c for c in components if c not in HERBS]
        if unknown:
            raise SystemExit(f"rasayana {key}: components with no safety entry: {unknown}")
        entry["components"] = components

    with open(PROTOCOLS, "w", encoding="utf-8") as f:
        json.dump(protocols, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"authored {len(HERBS)} herbs; "
          f"tagged {len(COMPONENTS)} adjuvants and {len(rasayana)} Rasayana entries")


if __name__ == "__main__":
    main()
