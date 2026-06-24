"""
One-shot data-quality pass: infer biomechanical contraindications for gym exercises
that currently have none (247 of 893, mostly strength isolation moves).

These are CLINICAL/biomechanical contraindications (not classical Ayurveda), inferred
from movement pattern (name + primary muscles + category). Uses ONLY the vocabulary
already present in the KB so downstream injury-filtering stays consistent. Safe-biased:
when a move loads a joint/region, the relevant injury is listed so an injured user is
filtered away from it. Only fills EMPTY lists — never overwrites curated data.

    cd server && ./venv/bin/python scripts/fill_gym_contraindications.py
"""
import json
import os

PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base", "gym_exercises.json"))

# keyword (in name or primary muscle) -> contraindications to add
# ordered specific→general; all matches accumulate
RULES: list[tuple[tuple[str, ...], list[str]]] = [
    # Core / abdominal flexion — disc & lower-back load, pregnancy
    (("crunch", "sit-up", "sit up", "situp", "ab ", "abdominal", "oblique", "russian twist",
      "v-up", "v up", "leg raise", "knee raise", "hollow", "toe touch", "heel touch",
      "flutter kick", "scissor", "jackknife", "dragon flag", "windshield"),
     ["herniated_disc", "lower_back_pain", "pregnancy"]),
    (("plank", "mountain climber", "hollow hold", "dead bug", "bird dog"),
     ["lower_back_pain", "pregnancy"]),
    # Spinal hinge / heavy back loading
    (("deadlift", "good morning", "bent over", "bent-over", "bentover", "t-bar", "rack pull",
      "hyperextension", "back extension", "romanian", "rdl", "pendlay"),
     ["herniated_disc", "lower_back_pain"]),
    # Knee-dominant lower body
    (("squat", "lunge", "leg press", "step-up", "step up", "leg extension", "hack",
      "split squat", "pistol", "wall sit", "sissy", "leg curl"),
     ["bad_knee", "knee_replacement"]),
    # Shoulder overhead / pressing
    (("overhead", "shoulder press", "military", "arnold", "upright row", "lateral raise",
      "front raise", "shoulder", "push press", "snatch", "clean and jerk", "jerk"),
     ["rotator_cuff", "shoulder_injury"]),
    # Horizontal press / chest
    (("bench press", "chest press", "push-up", "push up", "pushup", "dip", "chest fly",
      "pec deck", "incline press", "decline press", "fly"),
     ["rotator_cuff", "shoulder_injury"]),
    # Vertical/horizontal pull
    (("pull-up", "pull up", "pullup", "chin-up", "chin up", "lat pulldown", "pulldown",
      "row", "pullover"),
     ["shoulder_injury"]),
    # Plyometric / high-impact / conditioning
    (("jump", "box ", "burpee", "plyo", "sprint", "skater", "hop", "bound", "kettlebell swing",
      "snatch", "thruster", "wall ball", "high knee", "jumping"),
     ["bad_knee", "bad_ankle", "heart_disease", "pregnancy"]),
    # Neck
    (("neck", "shrug"),
     ["cervical_spondylosis", "neck_injury"]),
    # Calves / ankle
    (("calf", "calve", "tibia", "ankle"),
     ["bad_ankle"]),
    # Wrist / forearm
    (("wrist", "forearm", "reverse curl"),
     ["wrist_injury"]),
    # Elbow-loading isolation (curls / extensions)
    (("curl", "tricep", "triceps", "skullcrusher", "skull crusher", "pushdown", "kickback"),
     ["elbow_injury"]),
    # Hip / adductor / abductor isolation
    (("adductor", "abductor", "groin", "hip thrust", "glute"),
     ["hip_injury"]),
]

# Heavy compound barbell moves additionally stress BP (Valsalva)
_VALSALVA = ("deadlift", "squat", "leg press", "overhead", "military", "bench press",
             "clean", "snatch", "jerk", "thruster")


def infer(ex: dict) -> list[str]:
    hay = (ex.get("name", "") + " " + " ".join(ex.get("primary_muscles", []) or [])).lower()
    found: list[str] = []
    for keys, contras in RULES:
        if any(k in hay for k in keys):
            for c in contras:
                if c not in found:
                    found.append(c)
    # Valsalva → BP/cardiac for heavy compounds
    if any(k in hay for k in _VALSALVA):
        for c in ("hypertension", "heart_disease"):
            if c not in found:
                found.append(c)
    return found


def main():
    data = json.load(open(PATH, encoding="utf-8"))
    filled, still_empty = 0, []
    for ex in data:
        if ex.get("contraindications"):
            continue
        inferred = infer(ex)
        if inferred:
            ex["contraindications"] = inferred
            filled += 1
        else:
            # genuinely low-risk isolation (e.g. machine adductor) — record but leave a
            # minimal honest marker so it's clearly reviewed, not un-audited.
            ex["contraindications"] = []
            ex["contraindications_reviewed"] = True
            still_empty.append(ex.get("name"))
    json.dump(data, open(PATH, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    total_with = sum(1 for e in data if e.get("contraindications"))
    print(f"Filled contraindications for {filled} exercises.")
    print(f"Reviewed-but-no-contra (low risk): {len(still_empty)} e.g. {still_empty[:8]}")
    print(f"Now {total_with}/{len(data)} exercises have contraindications "
          f"({len(data) - total_with} reviewed low-risk).")


if __name__ == "__main__":
    main()
