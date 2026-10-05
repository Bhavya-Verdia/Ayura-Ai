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
    # Added 2026-10 after a pass over all 70 onboarding conditions. Each of
    # these changed the plan's movements (impact withheld, spinal or neck load
    # removed, fall risk gated) and said nothing — and each has a standard
    # instruction a physiotherapist gives before the first session.
    {
        # Pregnancy changed the plan more than any condition — a third of the
        # library withheld, a pool notice — and was the one declaration with no
        # note at all: nothing on when to stop, overheating or lying flat.
        "key": "pregnancy",
        "match": ("pregnan", "nursing"),
        "label": "Pregnancy",
        "note": ("Get your obstetrician's or midwife's go-ahead first. Stop and seek care for "
                 "vaginal bleeding, fluid leaking, regular painful contractions, dizziness or "
                 "feeling faint, chest pain, a headache that will not settle, calf pain or "
                 "swelling, or breathlessness before you start. After the first trimester avoid "
                 "lying flat on your back. Keep to an effort where you can still talk, avoid "
                 "getting overheated, and drink water through the session."),
        "source": "ACOG Committee Opinion 804, physical activity in pregnancy (2020)",
    },
    {
        "key": "osteoarthritis",
        "match": ("osteoarthritis", "arthritis", "sandhivata"),
        # Rheumatoid, psoriatic and lupus arthritis have their own note above;
        # a flare is managed differently from a degenerative joint.
        "unless": ("rheumatoid", "psoriatic", "lupus", "gout", "ankylosing"),
        "label": "Osteoarthritis",
        "note": ("Exercise is one of the main treatments for osteoarthritis, not something "
                 "to wait out. Some joint discomfort while training is fine if it stays mild "
                 "(about 2–3 out of 10) and has settled by the next morning; if the joint is "
                 "worse the next day, use less weight or a smaller range next session. This "
                 "plan leaves out jumping and running."),
        "source": "OARSI 2019 and ACR/Arthritis Foundation 2019 osteoarthritis guidelines; "
                  "pain-monitoring model (Thomeé, 1997)",
    },
    {
        "key": "back",
        "match": ("back_pain", "lower_back", "sciatica", "lumbar", "herniated_disc",
                  "slipped_disc"),
        "label": "Back pain / sciatica",
        "note": ("Keep your spine in a neutral position whenever you hold a weight. If pain "
                 "spreads further down your leg during or after an exercise, stop that "
                 "exercise; pain that stays in the back, or moves up towards it, is usually "
                 "safe to keep working through gently. Get urgent care for numbness around "
                 "the groin, new bladder or bowel problems, or weakness in a leg that is "
                 "getting worse."),
        "source": "NICE NG59, low back pain and sciatica (2016, updated 2020)",
    },
    {
        "key": "neck",
        "match": ("cervical", "neck_pain", "neck_injury"),
        "label": "Neck condition",
        "note": ("Keep your neck in line with your spine — no weight resting on the neck, "
                 "and no looking up under load. Stop and get it checked if pain, tingling or "
                 "weakness spreads into an arm."),
        "source": "NICE CKS, neck pain — cervical radiculopathy (2023)",
    },
    {
        "key": "parkinson",
        "match": ("parkinson",),
        "label": "Parkinson's",
        "note": ("Train when your medication is working best. Big, deliberate movements and "
                 "balance practice are part of the benefit, so take your time with them, "
                 "and keep a support within reach for standing work."),
        "source": "European Physiotherapy Guideline for Parkinson's Disease (KNGF/ParkinsonNet, 2014)",
    },
    {
        "key": "ms",
        "match": ("multiple_sclerosis",),
        "label": "Multiple sclerosis",
        "note": ("Getting hot can bring symptoms on for a while — train somewhere cool, keep "
                 "cold water with you and rest between sets. Symptoms that come with "
                 "overheating should settle within about an hour of cooling down; if they "
                 "do not, speak to your MS team."),
        "source": "National MS Society exercise recommendations (Kalb et al., 2020)",
    },
    {
        "key": "lithium",
        "match": ("bipolar", "lithium"),
        "label": "Bipolar disorder",
        "note": ("If you take lithium, heavy sweating can raise its level in your blood. "
                 "Drink water steadily before, during and after training, avoid training in "
                 "heat, and tell your prescriber you have started. Stop and seek advice for "
                 "a new tremor, unsteadiness, confusion, vomiting or diarrhoea."),
        "source": "BNF lithium monograph; NICE CG185 (bipolar disorder)",
    },
]

from engine.movement_risk import unfalse  # noqa: E402

# Shared with the risk maps and both engines; see engine.movement_risk.unfalse.
_unfalse = unfalse


def guidance_for(declared) -> list[dict]:
    """The notes that apply to these declared conditions and injuries, in the
    order the table lists them, one per entry."""
    text = [_unfalse(d) for d in declared or [] if d]
    return [{"key": g["key"], "label": g["label"], "note": g["note"], "source": g["source"]}
            for g in CONDITION_GUIDANCE
            if any(m in t for t in text for m in g["match"])
            and not any(u in t for t in text for u in g.get("unless", ()))]
