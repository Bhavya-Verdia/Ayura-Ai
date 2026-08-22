"""One-shot authoring pass: give every Aushadha compendium entry a selection key.

Run once; the result is committed. Kept in the tree because it is the record of
what was authored and why, and because re-running it is how the enrichment gets
re-applied if `panchakarma_protocols.json` is ever regenerated upstream.

## The problem it fixes

Across 5,400 generated plans covering every dosha, setting, goal, Koshtha and
condition, only 13 of 32 Aushadha entries were ever selected. `_select_aushadha`
matched on the `dosha` field alone and took the first hit, so of the six Vata oils
only Tila Taila — the first — could ever be chosen. Ksheerabala, Mahanarayana,
Bala, Dashamoola and Dhanvantara were authored, cited, and unreachable.

The indication for each was already written down. It was in the `use` prose:
"Neurological disorders, Asthi-Majja Vata", "Joint disorders, muscle disorders",
"Postnatal care". Prose no matcher reads. This adds `indications` — the same
knowledge as condition tokens the engine can match — and fills the missing doses.

Every token is checked against `engine.condition_vocab` by a test, because a token
the matcher cannot match is indistinguishable from an entry with no indication.
"""
import json
import os
import sys
from collections import OrderedDict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

KB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base"))
PROTOCOLS = os.path.join(KB, "panchakarma_protocols.json")

# ── Authored selection keys ───────────────────────────────────────────────────
# `indications` are matched against the patient's conditions. An empty list means
# "no specific indication" — the entry stays selectable as the dosha default, which
# is what Tila Taila, Dashamoola Kashayam and Eranda already were in practice.
#
# NOT CLINICALLY REVIEWED. Each list is derived from the entry's own `use` text,
# which is sourced with the rest of panchakarma_protocols.json (CS/SS/AH/CCRAS).
# Where the prose named a classical category ("Asthi-Majja Vata") the tokens are
# the modern conditions that fall under it; that mapping is the part a reviewer
# most needs to check.

INDICATIONS = {
    "oils_external": {
        "Tila Taila (Sesame oil)": [],
        "Ksheerabala Taila": [
            "sciatica", "neuropathy", "parkinson", "paralysis", "multiple_sclerosis",
            "cervical_spondylosis", "osteoarthritis",
        ],
        "Mahanarayana Taila": [
            "rheumatoid_arthritis", "osteoarthritis", "gout", "frozen_shoulder",
            "back_pain", "cervical_spondylosis", "ankylosing_spondylitis", "fibromyalgia",
        ],
        "Bala Taila": ["fibromyalgia", "chronic_fatigue", "long_covid", "muscular_dystrophy"],
        "Dashamoola Taila": ["asthma", "copd", "bronchitis", "recurrent_cough"],
        "Chandanadi Taila": ["eczema", "psoriasis", "urticaria", "rosacea", "acne", "dermatitis"],
        "Brahmi Taila": ["anxiety", "insomnia", "depression", "adhd", "migraine", "stress"],
        "Dhanvantara Taila": ["postnatal", "postpartum", "cervical_spondylosis", "vertigo"],
        "Sarshapa Taila (Mustard)": ["obesity", "hypothyroidism", "high_cholesterol"],
        "Anu Taila": [],
        "Shadbindu Taila": ["sinusitis", "rhinitis", "allergic_rhinitis", "nasal_polyps"],
    },
    "ghrita_internal": {
        "Tikta Ghrita": [],
        "Mahatiktaka Ghrita": [
            "psoriasis", "eczema", "dermatitis", "vitiligo", "fatty_liver",
            "hepatitis", "urticaria",
        ],
        "Shatavari Ghrita": [
            "pcos", "endometriosis", "infertility", "dysmenorrhea", "menorrhagia",
            "amenorrhea", "menopause",
        ],
        "Brahmi Ghrita": ["anxiety", "depression", "insomnia", "adhd", "memory_loss", "stress"],
        "Triphala Ghrita": ["glaucoma", "dry_eye", "constipation_chronic", "cataract"],
        "Ashwagandha Ghrita": [
            "fibromyalgia", "chronic_fatigue", "long_covid", "hypothyroidism", "insomnia",
        ],
    },
    "kashayam_basti": {
        # Disjoint from the combination formulations below. Two entries in one
        # section claiming the same indication means the later one is unreachable
        # for it — the exact fault this pass exists to remove, reintroduced.
        "Dashamoola Kashayam": [],
        "Rasna Saptak Kashayam": ["gout"],
        "Bala Kashayam": ["fibromyalgia", "chronic_fatigue", "muscular_dystrophy"],
        "Triphala Kashayam": ["constipation_chronic", "obesity", "hemorrhoids"],
    },
    "virechana_drugs": {
        "Trivrit Churna / Trivrit Lehyam": [],
        "Eranda (Castor Oil)": [],
        "Avipattikara Churna": ["acid_reflux", "gastritis", "fatty_liver", "hyperacidity", "gerd"],
        "Triphala Churna": ["constipation_chronic"],
    },
    "vamana_drugs": {
        "Madanaphala Phanta": [],
        "Vacha Churna": ["asthma", "bronchitis", "epilepsy"],
        "Neem bark decoction": ["eczema", "psoriasis", "acne", "diabetes_type2"],
    },
}

# Vamana drugs carried no dose at all, so the engine's Vamana day action hardcoded
# its own text and the KB rows were decorative. Emetic dosing is titrated to Vega
# (number of bouts) rather than fixed, so each dose records the quantity AND says
# what it is titrated against — a bare number here would be the more dangerous
# thing to write.
VAMANA_DOSES = {
    "Madanaphala Phanta": {
        "dose": "Phanta of 8–12 Madanaphala fruits, ~100–200 ml",
        "dose_note": "Titrated to Vega, not to volume. Samyak Yoga is 8 Vegas; stop at bile, "
                     "blood or 12 Vegas. Administered by a Vaidya only.",
    },
    "Vacha Churna": {
        "dose": "3–5 g with warm water",
        "dose_note": "Secondary emetic, given with or after Madanaphala when Vegas are "
                     "inadequate. Titrated to Vega.",
    },
    "Neem bark decoction": {
        "dose": "50–100 ml warm decoction",
        "dose_note": "Mildest option, for Avara Shuddhi in low Bala. Titrated to Vega.",
    },
}

# `rasayana_by_condition` is keyed by condition in the KB and was selected by dosha
# alone, so a PCOS patient and an arthritis patient both received the generic dosha
# Rasayana while Shatavari and Laksha Guggulu — authored for exactly them — sat
# unused. These are the conditions each key names.
RASAYANA_INDICATIONS = {
    "general_immunity": [],
    "vata_neurological": ["sciatica", "neuropathy", "parkinson", "paralysis", "multiple_sclerosis"],
    "pitta_inflammatory": ["rheumatoid_arthritis", "psoriasis", "eczema", "gastritis", "colitis"],
    "kapha_metabolic": ["obesity", "diabetes_type2", "hypothyroidism", "high_cholesterol", "fatty_liver"],
    "reproductive_female": ["pcos", "endometriosis", "infertility", "dysmenorrhea", "amenorrhea"],
    "reproductive_male": ["infertility", "low_libido", "oligospermia"],
    "bone_joint": ["osteoarthritis", "osteoporosis", "ankylosing_spondylitis", "gout", "fracture"],
    "medhya_brain": ["anxiety", "depression", "insomnia", "adhd", "migraine", "memory_loss"],
}

# `reproductive_male` and `reproductive_female` share "infertility". Gender decides
# between them; without it the first match would always win and half the users would
# get the wrong Rasayana for the same recorded condition.
RASAYANA_GENDER = {"reproductive_female": "female", "reproductive_male": "male"}


# The engine hardcoded six condition-specific Niruha formulations in an if/elif
# chain, matched by raw substring (`"kidney" in m`, which also matches "kidney" in
# any longer word) while every safety gate in the file uses `term_in_condition`.
# The formulations themselves are good clinical content and are kept — they move
# here, as data, where they can be reviewed, matched precisely, and sit beside the
# four single-herb Kashayams they were shadowing.
BASTI_COMBINATIONS = [
    {
        "name": "Rasna Saptak + Bala Kashayam",
        "dosha": "vata",
        "use": "Asthi-Majja Gata Vata — ankylosing spondylitis, spondylosis",
        "indications": ["ankylosing_spondylitis", "cervical_spondylosis", "spondylosis", "spondylitis"],
    },
    {
        "name": "Bala + Dashamoola Kashayam",
        "dosha": "vata",
        "use": "Neurological Vata disorders — Gridhrasi (sciatica), Kampavata (Parkinson's)",
        "indications": ["sciatica", "neuropathy", "parkinson", "paralysis", "multiple_sclerosis"],
    },
    {
        "name": "Dashamoola + Rasna + Eranda Kashayam",
        "dosha": "vata",
        "use": "Amavata / Sandhivata / Vatarakta — inflammatory and degenerative joint disease",
        "indications": ["rheumatoid_arthritis", "osteoarthritis", "frozen_shoulder"],
    },
    {
        "name": "Dashamoola + Bilva Kashayam",
        "dosha": "vata",
        "use": "Grahani / Pakwashaya Vata — IBS, chronic constipation, bloating",
        "indications": ["ibs", "bloating", "colitis"],
    },
    {
        "name": "Dashamoola + Shatavari + Ashoka Kashayam",
        "dosha": "vata",
        "use": "Artavavaha Srotas Shuddhi — gynaecological Vata-Kapha",
        "indications": ["pcos", "endometriosis", "fibroids", "dysmenorrhea", "menorrhagia"],
    },
    {
        "name": "Gokshura + Varuna Kashayam",
        "dosha": "vata",
        "use": "Mutravaha Srotas — renal and urinary Vata pacification. Matra Basti only in "
               "renal disease; Niruha is avoided.",
        "indications": ["chronic_kidney_disease", "kidney_disease", "kidney_stones", "recurrent_uti"],
    },
]


def main():
    with open(PROTOCOLS, encoding="utf-8") as f:
        protocols = json.load(f, object_pairs_hook=OrderedDict)

    compendium = protocols["aushadha_compendium"]
    touched = 0

    for section, by_name in INDICATIONS.items():
        for entry in compendium[section]:
            name = entry["name"]
            if name not in by_name:
                raise SystemExit(f"unauthored entry in {section}: {name!r}")
            entry["indications"] = by_name[name]
            if name in VAMANA_DOSES:
                entry.update(VAMANA_DOSES[name])
            touched += 1

    existing = {e["name"] for e in compendium["kashayam_basti"]}
    for combo in BASTI_COMBINATIONS:
        if combo["name"] not in existing:
            compendium["kashayam_basti"].append(combo)
            touched += 1

    rasayana = protocols["paschat_karma"]["rasayana_integration"]["rasayana_by_condition"]
    for key, entry in rasayana.items():
        if key not in RASAYANA_INDICATIONS:
            raise SystemExit(f"unauthored rasayana key: {key!r}")
        entry["indications"] = RASAYANA_INDICATIONS[key]
        if key in RASAYANA_GENDER:
            entry["gender"] = RASAYANA_GENDER[key]
        touched += 1

    compendium["_authoring_note"] = (
        "`indications` and the Vamana `dose` fields are AUTHORED and NOT CLINICALLY "
        "REVIEWED — see scripts/enrich_aushadha.py for what was derived from what. "
        "Each list is the condition-token form of the entry's own `use` prose, which "
        "the engine could not match on. An empty list means no specific indication: "
        "the entry remains selectable as the dosha default."
    )

    with open(PROTOCOLS, "w", encoding="utf-8") as f:
        json.dump(protocols, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"enriched {touched} entries in {os.path.relpath(PROTOCOLS)}")


if __name__ == "__main__":
    main()
