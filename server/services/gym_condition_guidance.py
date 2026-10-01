"""What a practitioner with a condition needs to know before training.

Removing movements is half of it. For a good share of the conditions onboarding
offers, no movement is the problem — the session is. Someone on insulin can do
every exercise in the library and still go hypoglycaemic halfway through it. An
asthmatic needs the longer warm-up that prevents the attack, and someone with
ME/CFS needs to be told that NICE advises *against* the fixed, stepped-up
programme this plan otherwise is. A gym plan for those people that said nothing
was a plan for somebody else.

Each entry is matched by substring against the declared conditions and
injuries, the same way `engine.movement_risk` matches, and states its source.
These are safety notes, not a treatment plan, and none of them has been read by a
clinician yet — they belong in the review packet with the rest of the gym
clinical layer.
"""

CONDITION_GUIDANCE: list[dict] = [
    {
        "key": "diabetes",
        "match": ("diabetes",),
        "label": "Diabetes",
        "note": ("If you use insulin or a sulfonylurea, check your blood glucose before "
                 "training. Below about 5.6 mmol/L (100 mg/dL), eat 15–30 g of fast "
                 "carbohydrate first; with type 1 and a reading above about 13.9 mmol/L "
                 "(250 mg/dL) with ketones, skip the session. Carry glucose tablets or "
                 "juice, and check your feet afterwards if you have any numbness. If you "
                 "have diabetic eye disease, ask your doctor before lifting heavy."),
        "source": "ADA position statement on physical activity and diabetes (Colberg et al., 2016)",
    },
    {
        "key": "respiratory",
        "match": ("asthma", "copd", "bronchitis"),
        "label": "Asthma / lung condition",
        "note": ("Keep your reliever inhaler with you. A longer, gradual warm-up — ten "
                 "minutes building from easy to moderate — reduces exercise-triggered "
                 "symptoms. Avoid training in cold, dry air, and stop if wheezing or chest "
                 "tightness does not settle with your inhaler."),
        "source": "GINA 2024 report, exercise-induced bronchoconstriction",
    },
    {
        "key": "epilepsy",
        "match": ("epilep", "seizure"),
        "label": "Epilepsy",
        "note": ("Train with someone who knows your condition and what to do in a seizure. "
                 "This plan uses machines and cables in place of free bars held over the "
                 "body. Never swim alone, and skip training after a missed dose, a poor "
                 "night's sleep or when you feel an aura."),
        "source": "ILAE Task Force on Sports and Epilepsy (Capovilla et al., 2016)",
    },
    {
        "key": "cardiac",
        "match": ("heart", "cardiac", "atrial_fibrillation", "arrhythmia", "angina"),
        "label": "Heart condition",
        "note": ("Get your cardiologist's clearance and a target heart rate before starting. "
                 "Stop straight away for chest pain or pressure, unusual breathlessness, "
                 "dizziness or palpitations. If you take a beta-blocker your heart rate will "
                 "not reflect effort — use the talk test: you should be able to speak in "
                 "short sentences throughout."),
        "source": "ACSM's Guidelines for Exercise Testing and Prescription, 11th ed.",
    },
    {
        "key": "hypertension",
        "match": ("hypertension", "high_blood_pressure"),
        "label": "High blood pressure",
        "note": ("Breathe out on every effort and never hold your breath. If a reading "
                 "before training is 180/110 or higher, skip the session and speak to your "
                 "doctor. Cool down gradually rather than stopping suddenly."),
        "source": "ACSM's Guidelines for Exercise Testing and Prescription, 11th ed.",
    },
    {
        "key": "eye_pressure",
        "match": ("glaucoma", "retinopathy", "retinal"),
        "label": "Glaucoma / eye disease",
        "note": ("Keep your head above your heart — this plan leaves out decline and "
                 "inverted positions — and breathe out on every effort, because holding "
                 "your breath raises the pressure inside the eye. Tell your eye doctor you "
                 "are starting resistance training."),
        "source": "American Academy of Ophthalmology patient guidance on exercise and glaucoma",
    },
    {
        "key": "low_bp",
        "match": ("low_blood_pressure", "hypotension"),
        "label": "Low blood pressure",
        "note": ("Get up slowly from lying and seated exercises, drink water before and "
                 "during the session, and stop and sit down if you feel light-headed."),
        "source": "General clinical guidance for orthostatic hypotension",
    },
    {
        "key": "anemia",
        "match": ("anemia", "anaemia", "menorrhagia"),
        "label": "Anaemia / heavy periods",
        "note": ("Less oxygen reaches your muscles, so the same weight feels harder. Work at "
                 "a lower effort than the plan suggests until your levels are treated, and "
                 "stop for dizziness, breathlessness or a racing heart."),
        "source": "General clinical guidance",
    },
    {
        "key": "thyroid_over",
        "match": ("hyperthyroid",),
        "label": "Overactive thyroid",
        "note": ("Until your levels are controlled, keep effort moderate: an overactive "
                 "thyroid already raises your heart rate, and hard intervals add to it. "
                 "Stop for palpitations."),
        "source": "General clinical guidance",
    },
    {
        "key": "fatigue",
        "match": ("chronic_fatigue", "long_covid", "fibromyalgia"),
        "label": "Chronic fatigue / long COVID / fibromyalgia",
        "note": ("Start well below what you think you can do. If symptoms get worse in the "
                 "24–48 hours after a session, that session was too much — drop back rather "
                 "than pushing through. For ME/CFS, NICE advises against fixed, stepped-up "
                 "exercise programmes like the progression in this plan; use it only with a "
                 "clinician who knows your condition, and stay within your energy limits."),
        "source": "NICE NG206 (ME/CFS, 2021); WHO long COVID rehabilitation guidance",
    },
    {
        "key": "kidney",
        "match": ("kidney_disease", "ckd", "chronic_kidney"),
        "label": "Kidney disease",
        "note": ("Keep to the fluid limits your nephrologist sets, and do not add protein "
                 "or creatine supplements to support this plan without their agreement."),
        "source": "KDIGO 2024 CKD guideline, lifestyle section",
    },
    {
        "key": "kidney_stones",
        "match": ("kidney_stone",),
        "label": "Kidney stones",
        "note": "Drink water through and after the session — sweat loss concentrates urine.",
        "source": "General clinical guidance",
    },
    {
        "key": "osteoporosis",
        "match": ("osteoporosis", "osteopenia"),
        "label": "Osteoporosis",
        "note": ("Strength and weight-bearing work are part of the treatment. Keep your "
                 "spine straight whenever you are holding a weight — this plan leaves out "
                 "crunches, twists and side bends for that reason — and practise balance so "
                 "a fall is less likely."),
        "source": "Too Fit to Fracture consensus (Giangregorio et al., 2014)",
    },
    {
        "key": "inflammatory_joint",
        "match": ("rheumatoid", "lupus", "gout", "psoriatic", "ankylosing"),
        "label": "Inflammatory joint condition",
        "note": ("During a flare, rest the inflamed joints and train around them. Work in "
                 "ranges that do not hurt; some stiffness is expected, sharp pain is not."),
        "source": "EULAR recommendations for physical activity in inflammatory arthritis (2018)",
    },
    {
        "key": "neuropathy",
        "match": ("neuropathy",),
        "label": "Peripheral neuropathy",
        "note": ("Check your feet for blisters or cuts after every session, wear well-fitted "
                 "shoes, and keep a hand near support during standing work."),
        "source": "ADA position statement on physical activity and diabetes (Colberg et al., 2016)",
    },
    {
        "key": "vertigo",
        "match": ("vertigo", "bppv", "vestibular"),
        "label": "Vertigo / balance",
        "note": ("Move slowly between lying, sitting and standing, and pause before walking "
                 "off. Keep a hand near support during standing exercises."),
        "source": "General clinical guidance",
    },
    {
        "key": "migraine",
        "match": ("migraine",),
        "label": "Migraine",
        "note": ("Hard exertion, dehydration and skipped meals are common triggers: eat and "
                 "drink before training, and avoid training in heat."),
        "source": "General clinical guidance",
    },
    {
        "key": "abdominal",
        "match": ("hernia", "abdominal_surgery", "hemorrhoid"),
        "label": "Hernia / abdominal surgery / haemorrhoids",
        "note": ("Breathe out on every effort and never strain against a held breath. After "
                 "abdominal surgery or a C-section, wait for your surgeon's clearance before "
                 "starting."),
        "source": "General clinical guidance",
    },
]


def _unfalse(term) -> str:
    """"heart" is a substring of "heartburn", which is reflux, not a heart
    condition — and it reached the cardiac note and the intensity ceiling."""
    return str(term).lower().replace("heartburn", "acid_reflux")


def guidance_for(declared) -> list[dict]:
    """The notes that apply to these declared conditions and injuries, in the
    order the table lists them, one per entry."""
    text = [_unfalse(d) for d in declared or [] if d]
    return [{"key": g["key"], "label": g["label"], "note": g["note"], "source": g["source"]}
            for g in CONDITION_GUIDANCE
            if any(m in t for t in text for m in g["match"])]
