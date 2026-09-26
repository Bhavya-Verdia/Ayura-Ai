"""What a movement DOES to the body, and which conditions that endangers.

Shared by the yoga and gym engines. A pose and a lift are different things, but
a head-below-heart position raises intraocular pressure whichever feature
prescribed it, and a practitioner with glaucoma is the same person in both.

`risk_tags` on a pose or a movement name the mechanism; the maps below name the
conditions and injuries each mechanism is dangerous for. Matching is by
substring over the practitioner's declared condition, so "inguinal_hernia" and
"hernia" both reach `abdominal_pressure`.
"""

# Conditions used to be mapped onto whichever pose tag was vaguely nearby:
# hernia onto knee_injury, epilepsy onto heart_disease, migraine onto
# high_blood_pressure, wrist onto shoulder_injury. Those tags describe a
# different body part, so the poses that actually endanger those users were
# never the ones removed — blocking knee poses does nothing for a hernia.
#
# These map to what a pose *does* (`risk_tags` in the KB), so the exclusion
# matches the mechanism: abdominal pressure for hernia, intracranial pressure
# for glaucoma and retinal detachment, loaded spinal flexion for osteoporosis.
_CONDITION_RISK_TAGS: dict[str, set[str]] = {
    "hernia":               {"abdominal_pressure"},
    "inguinal_hernia":      {"abdominal_pressure"},
    "hiatal_hernia":        {"abdominal_pressure"},
    "abdominal_surgery":    {"abdominal_pressure", "wrist_weight_bearing"},
    "recent_surgery":       {"abdominal_pressure"},
    "ulcer":                {"abdominal_pressure"},
    "ibd":                  {"abdominal_pressure"},
    "diverticulitis":       {"abdominal_pressure"},
    # Onboarding's own ids, which the substrings above do not reach: "ibd" is in
    # `ibd_crohns` but not in `ulcerative_colitis`, the other inflammatory bowel
    # disease it offers. Straining against a closed glottis is the textbook
    # aggravator of haemorrhoids.
    "ulcerative_colitis":   {"abdominal_pressure"},
    "hemorrhoid":           {"abdominal_pressure"},

    "glaucoma":             {"intracranial_pressure"},
    "retinal_detachment":   {"intracranial_pressure"},
    "retinopathy":          {"intracranial_pressure"},
    "migraine":             {"intracranial_pressure"},
    "sinusitis":            {"intracranial_pressure"},
    "stroke":               {"intracranial_pressure", "fall_risk"},

    "epilepsy":             {"seizure_risk", "intracranial_pressure", "fall_risk"},
    "seizure":              {"seizure_risk", "intracranial_pressure", "fall_risk"},

    "vertigo":              {"fall_risk", "neck_load", "intracranial_pressure"},
    "bppv":                 {"fall_risk", "neck_load", "intracranial_pressure"},
    "labyrinthitis":        {"fall_risk", "neck_load", "intracranial_pressure"},
    "vestibular":           {"fall_risk", "neck_load", "intracranial_pressure"},
    "parkinson":            {"fall_risk"},
    "multiple_sclerosis":   {"fall_risk"},
    "neuropathy":           {"fall_risk"},

    "osteoporosis":         {"spinal_flexion", "fall_risk", "spinal_extension"},
    "osteopenia":           {"spinal_flexion"},
    "compression_fracture": {"spinal_flexion", "spinal_extension"},

    # Spinal EXTENSION — backbending. The mechanism vocabulary covered flexion but
    # not its opposite, so an entire movement class (18 poses) had no mechanism at
    # all and could only be caught by a pose's hand-written contraindication list.
    #
    # Herniated disc is deliberately NOT mapped here. Extension is frequently the
    # therapeutic direction for a posterior disc herniation, and excluding backbends
    # for those users would be actively wrong — it is already covered by its own
    # contraindication tokens where individual poses call for it. These four are the
    # conditions where loading into extension is the recognised problem.
    "spondylolisthesis":    {"spinal_extension"},
    "spondylolysis":        {"spinal_extension"},
    "spinal_stenosis":      {"spinal_extension"},
    "facet":                {"spinal_extension"},

    "carpal_tunnel":        {"wrist_weight_bearing"},
    "wrist_injury":         {"wrist_weight_bearing"},
    "rheumatoid_arthritis": {"wrist_weight_bearing"},
    # The other inflammatory arthritides onboarding offers; both reach the small
    # joints of the hand and wrist the way rheumatoid arthritis does.
    "lupus":                {"wrist_weight_bearing"},
    "scleroderma":          {"wrist_weight_bearing"},

    "cervical_spondylosis": {"neck_load"},
    "cervical_disc":        {"neck_load"},
    "neck_injury":          {"neck_load"},
    "whiplash":             {"neck_load"},
}

# Injury free-text → risk mechanism, for the same reason as above.
_INJURY_RISK_TAGS: dict[str, set[str]] = {
    "wrist":  {"wrist_weight_bearing"},
    "hand":   {"wrist_weight_bearing"},
    "neck":   {"neck_load"},
    "hernia": {"abdominal_pressure"},
    "balance": {"fall_risk"},
}


# Words people type for injuries the maps already know under a different name.
# Only unambiguous ones: "ACL" is a knee, "rotator cuff" is a shoulder. Vague terms
# like "surgery" or "pain everywhere" are deliberately absent — they should fall
# through to `unmatched_limitations` and be shown to the user, not guessed at.
_LIMITATION_ALIASES = {
    "acl": "knee", "mcl": "knee", "meniscus": "knee", "patella": "knee", "kneecap": "knee",
    "rotator cuff": "shoulder", "frozen shoulder": "shoulder", "impingement": "shoulder",
    "sciatica": "lower_back", "slipped disc": "lower_back", "herniated disc": "lower_back",
    "lumbar": "lower_back", "disc": "lower_back",
    "carpal tunnel": "wrist", "cervical": "neck", "whiplash": "neck",
    "plantar": "ankle", "achilles": "ankle", "sprained ankle": "ankle",
    "sacroiliac": "hip", "si joint": "hip", "labral": "hip",
}


RISK_VOCAB = frozenset(
    tag for tags in (*_CONDITION_RISK_TAGS.values(), *_INJURY_RISK_TAGS.values())
    for tag in tags)


def condition_risk_tags(conditions) -> set:
    """Mechanisms to avoid for these declared conditions."""
    risks: set = set()
    for cond in conditions or []:
        key = str(cond).lower()
        for k, tags in _CONDITION_RISK_TAGS.items():
            if k in key:
                risks.update(tags)
    return risks


def injury_risk_tags(injuries) -> set:
    """Mechanisms to avoid for these declared injuries or limitations."""
    risks: set = set()
    for inj in injuries or []:
        key = str(inj).lower()
        for k, tags in _INJURY_RISK_TAGS.items():
            if k in key:
                risks.update(tags)
    return risks
