"""What each movement does to the body, authored by mechanism.

The contraindication tokens in `clinical.py` name body parts — a knee, a shoulder,
a disc — and a condition only reached a movement when someone had thought to map
it onto one of them. Of the 70 conditions onboarding offers, eight changed a gym
plan at all. Glaucoma, epilepsy, vertigo, osteoporosis's fracture mechanism,
hernia and rheumatoid arthritis are not body parts, and there was no token for
any of them to reach.

The yoga engine solved this months ago with `risk_tags` — the mechanism a pose
works through — and this file gives the gym library the same field, in the same
vocabulary (`engine.movement_risk.RISK_VOCAB`), so one condition map serves both.

Authored per mechanism rather than per movement: each group states its reason
once, and a reviewer confirms the group. A movement appears in every group whose
mechanism it carries.

**Engineering's reasoning, not clinical sign-off.** Like `clinical.py`, none of
this has been read by a practitioner; it belongs in the Vaidya packet.
"""

MECHANISMS: dict[str, dict] = {

    "spinal_flexion": {
        "why": ("Flexing, side-bending or twisting the trunk under load is the movement "
                "associated with vertebral compression fracture in low bone density. "
                "The spine is safest kept neutral while it is loaded; the anti-movement "
                "core work (dead bug, bird dog, Pallof press, planks) trains the same "
                "muscles without it."),
        "movements": [
            "Crunches", "Cable Crunch", "Exercise Ball Crunch", "Russian Twist",
            "Dumbbell Side Bend", "Standing Cable Wood Chop", "Hanging Leg Raise",
            "Leg Raise on Parallel Bars", "Lying Leg Raise", "Hollow Body Hold",
            "Exercise Ball Pull-In", "Good Morning",
        ],
    },

    "intracranial_pressure": {
        "why": ("Head below the heart. Inverted and decline positions raise intraocular "
                "and intracranial pressure, which is the mechanism glaucoma, retinopathy "
                "and a history of stroke are restricted for."),
        "movements": [
            "Decline Push-Up", "Pike Push-Up", "Pike Push-Up - Feet Elevated",
            "Hands-Elevated Pike Push-Up", "Wall Handstand Hold", "Inchworm",
        ],
    },

    "abdominal_pressure": {
        "why": ("The heaviest bracing in the library, and the movements that curl the "
                "trunk against the abdominal wall. Both raise intra-abdominal pressure "
                "sharply — the load a hernia, a healing abdominal incision or an "
                "inflamed bowel is protected from."),
        "movements": [
            "Barbell Squat", "Front Barbell Squat", "Barbell Deadlift", "Sumo Deadlift",
            "Rack Pull", "Barbell Romanian Deadlift", "Good Morning", "Leg Press",
            "Hack Squat", "Push Press", "Barbell Hip Thrust",
            "Crunches", "Cable Crunch", "Exercise Ball Crunch", "Hanging Leg Raise",
            "Leg Raise on Parallel Bars", "Lying Leg Raise", "Hollow Body Hold",
            "Ab Wheel Rollout", "Exercise Ball Pull-In", "Russian Twist",
        ],
    },

    "fall_risk": {
        "why": ("Balance on one leg, or a stepping movement, with load in the hands or on "
                "the back. A loss of balance here is a fall carrying weight — the risk "
                "for vertigo, neuropathy, Parkinson's, epilepsy, and for bone that "
                "fractures when it lands. Split squats with the back foot planted and "
                "machine work keep the same muscles without it."),
        "movements": [
            "Dumbbell Lunges", "Barbell Lunge", "Reverse Lunge", "Barbell Step Ups",
            "Dumbbell Step Ups", "Bulgarian Split Squat", "Stair Climbing",
        ],
    },

    "seizure_risk": {
        "why": ("A load that lands on the body if control is lost for a moment: a bar "
                "across the chest or the neck, a weight held over the face, a hang from "
                "a bar, a moving belt, open water. Machines and cables keep the load on "
                "a track, which is why they are the standard advice for epilepsy."),
        "movements": [
            "Barbell Bench Press", "Incline Barbell Bench Press", "Close-Grip Bench Press",
            "Barbell Floor Press", "Dumbbell Bench Press", "Incline Dumbbell Press",
            "Dumbbell Flyes", "EZ-Bar Skullcrusher", "Lying Triceps Press",
            "Dumbbell Overhead Triceps Extension - Two Hands", "Barbell Squat", "Front Barbell Squat",
            "Barbell Shoulder Press", "Push Press", "Barbell Lunge", "Barbell Step Ups",
            "Good Morning", "Hanging Leg Raise", "Leg Raise on Parallel Bars", "Pull-Up",
            "Chin-Up", "Wall Handstand Hold", "Incline Treadmill Walk", "Stair Climbing",
            "Swimming",
        ],
    },

    "wrist_weight_bearing": {
        "why": ("Bodyweight carried through an extended wrist. Rheumatoid and other "
                "inflammatory arthritis, carpal tunnel and a wrist injury are all "
                "aggravated by it; forearm planks and machine presses spare the joint."),
        "movements": [
            "Push-Up", "Knee Push-Up", "Incline Push-Up", "Decline Push-Up",
            "Close-Grip Push-Up", "Diamond Push-Up", "Incline Close-Grip Push-Up",
            "Pike Push-Up", "Pike Push-Up - Feet Elevated", "Hands-Elevated Pike Push-Up",
            "Wall Handstand Hold", "Plank Shoulder Tap", "Renegade Row",
            "Mountain Climbers", "Burpees", "Bench Dips", "Chest Dip", "Inchworm",
            "Bodyweight Triceps Extension", "Ab Wheel Rollout",
        ],
    },

    "neck_load": {
        "why": ("Load carried by or through the cervical spine: a bar resting on it, "
                "the traps shrugging a heavy load, a hand pulling the head forward. "
                "Restricted for cervical spondylosis, a neck injury and vertigo."),
        "movements": [
            "Barbell Shrug", "Dumbbell Shrug", "Barbell Squat", "Barbell Lunge",
            "Barbell Step Ups", "Good Morning", "Farmer's Walk", "Crunches",
            "Wall Handstand Hold",
        ],
    },

    "spinal_extension": {
        "why": ("The lumbar spine taken toward end-range extension, or loaded there. "
                "Spondylolisthesis, spinal stenosis and facet pain are provoked by it. "
                "Herniated disc is deliberately not mapped here — extension is often "
                "the therapeutic direction for it — which is the yoga engine's reading "
                "too."),
        "movements": [
            "Back Extension", "Superman Hold", "Prone Swimmer", "Barbell Hip Thrust",
            "Wall Handstand Hold", "Push Press",
        ],
    },
}


def risk_tags_by_movement() -> dict[str, list[str]]:
    """{movement name: sorted mechanisms}, the shape the builder writes."""
    out: dict[str, set] = {}
    for tag, group in MECHANISMS.items():
        for name in group["movements"]:
            out.setdefault(name, set()).add(tag)
    return {name: sorted(tags) for name, tags in out.items()}
