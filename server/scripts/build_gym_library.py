#!/usr/bin/env python3
"""Build `gym_exercises.json` from the curated movement spec.

The previous library was 902 rows imported by `seed_gym_exercises.py`, which
re-derived `category`, `level` and `mechanic` from substring matches on the
exercise NAME while the upstream dataset carried all three correctly. 176 of 779
imported rows (23%) ended up contradicting their own source. This builder goes
the other way: judgment lives in the spec, prose comes from upstream where
upstream is good, and nothing is inferred from a name.

    python scripts/build_gym_library.py            # write the library
    python scripts/build_gym_library.py --check    # verify it is up to date

Upstream (`free-exercise-db`) is cached at `data/sources/free_exercise_db.json`.
It is a build input, not a runtime dependency.
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gym_library import schema  # noqa: E402
from gym_library.movements_upper import ARMS, BACK, CHEST, SHOULDERS  # noqa: E402
from gym_library.movements_lower import (CONDITIONING, CORE, LEGS,  # noqa: E402
                                         MOBILITY)
from gym_library.movements_fill import FILL  # noqa: E402
from gym_library.movements_home import HOME  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "knowledge_base" / "gym_exercises.json"
CACHE = BASE / "data" / "sources" / "free_exercise_db.json"
# Entries this project authored for the previous library — the bodyweight,
# conditioning and home-user movements that upstream never had. They were the
# most-prescribed movements in the app (`Wall Angel Row` was the single most
# prescribed movement of all 902), so they are a source, not a casualty.
#
# Only the 16 rows the spec actually references, and only their prose fields.
# Carrying all 902 would mean shipping 1.6 MB to serve sixteen, and would leave
# the discarded library's classifying fields sitting where someone could read
# them as authoritative.
LEGACY = BASE / "data" / "sources" / "authored_legacy.json"
UPSTREAM = ("https://raw.githubusercontent.com/yuhonas/free-exercise-db/"
            "main/dist/exercises.json")

SPEC = (CHEST + BACK + SHOULDERS + ARMS + LEGS + CORE + CONDITIONING
        + MOBILITY + FILL + HOME)


# --------------------------------------------------------------- upstream ---
def load_upstream() -> dict:
    """Cached so a build is reproducible offline and a network blip cannot
    silently change the library."""
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        print(f"  fetching {UPSTREAM}")
        with urllib.request.urlopen(UPSTREAM, timeout=60) as r:
            CACHE.write_bytes(r.read())
    return {e["name"]: e for e in json.loads(CACHE.read_text())}


def load_legacy() -> dict:
    return {e["name"]: e for e in json.loads(LEGACY.read_text())}


# ------------------------------------------------------------ derivations ---
def _id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# Volume prescriptions by role and rep style. These used to come from the
# upstream row, which had one `sets_reps` block for every exercise regardless of
# whether it was a deadlift or a wrist circle.
def _sets_reps(entry: dict) -> dict:
    style, role = entry["rep_style"], entry["role"]
    if style == "isometric":
        return {lv: {"sets": s, "reps": t, "rest_seconds": 45}
                for lv, s, t in (("beginner", 3, "20-30 sec"),
                                 ("intermediate", 3, "30-45 sec"),
                                 ("advanced", 4, "45-60 sec"))}
    if style == "time":
        return {lv: {"sets": s, "reps": t, "rest_seconds": 60}
                for lv, s, t in (("beginner", 1, "8-10 min"),
                                 ("intermediate", 1, "12-15 min"),
                                 ("advanced", 1, "15-20 min"))}
    if style == "distance":
        return {lv: {"sets": s, "reps": d, "rest_seconds": 90}
                for lv, s, d in (("beginner", 3, "20 m"),
                                 ("intermediate", 3, "30 m"),
                                 ("advanced", 4, "40 m"))}
    if role == "main":
        return {"beginner": {"sets": 3, "reps": "8-12", "rest_seconds": 90},
                "intermediate": {"sets": 4, "reps": "6-10", "rest_seconds": 120},
                "advanced": {"sets": 5, "reps": "4-8", "rest_seconds": 180}}
    if role in ("warmup", "mobility"):
        return {lv: {"sets": 1, "reps": "8-10", "rest_seconds": 0}
                for lv in ("beginner", "intermediate", "advanced")}
    return {"beginner": {"sets": 2, "reps": "12-15", "rest_seconds": 60},
            "intermediate": {"sets": 3, "reps": "10-12", "rest_seconds": 75},
            "advanced": {"sets": 3, "reps": "8-12", "rest_seconds": 75}}


# Dosha is a PREFERENCE, expressed over movement properties — never over the
# implement. Deriving it from equipment is what marked all 179 barbell exercises
# `pitta: avoid` and hid a barbell from two constitutions in three.
#
# The first correction over-shot: everything that was not high-impact came out
# `good/good/good`, so 144 of 173 movements carried the same value and the field
# discriminated on 17% of the library. A preference that says the same thing
# about almost everything is decoration.
#
# The classical properties, applied to what a movement actually asks of someone:
#
#   Vata  — needs grounding, warmth, rhythm. Unsettled by explosive, irregular
#           and high-impact work; suited by supported, controlled, isometric work.
#   Pitta — needs cooling and non-competition. Aggravated by maximal-intensity
#           and heat-building efforts; suited by moderate, sustainable work.
#   Kapha — needs stimulation and heat. Under-served by passive, slow and
#           low-demand work; suited by vigorous, sustained and heavy efforts.
#
# `avoid` is deliberately never emitted. The pool cut treats the gap between
# `good` and `avoid` as wider than the pool is deep, which is the mechanism that
# turned a mislabel into a ban the first time. A preference should reorder a
# pool, not empty it.
def _dosha(entry: dict) -> dict:
    d = {"vata": "good", "pitta": "good", "kapha": "good"}
    role, pattern, lc = entry["role"], entry["movement_pattern"], entry["load_class"]
    explosive = entry["impact"] == "high" or lc in ("push_press", "kettlebell_swing")
    maximal = role == "main" and entry["equipment"] == "barbell"
    sustained = entry["rep_style"] == "time" and entry["category"] == "cardio"
    passive = role in ("mobility", "warmup")
    stabilising = entry["rep_style"] == "isometric" or pattern in (
        "anti_extension", "anti_rotation", "carry")

    if explosive:
        d["vata"] = "moderate"      # irregular, airborne, ungrounding
        d["pitta"] = "moderate"     # maximal effort builds heat
    if maximal:
        d["pitta"] = "moderate"     # heavy barbell work is competitive and heating
    if sustained and entry["impact"] != "high":
        d["vata"] = "moderate"      # long output depletes before it grounds
    if passive:
        d["kapha"] = "moderate"     # stillness is what Kapha already has too much of
    if stabilising:
        d["vata"] = "good"          # grounding, whatever else is true of it
        if not sustained:
            d["kapha"] = "moderate" # holding still does not move Kapha
    if entry["mechanic"] == "isolation" and role == "accessory":
        d["kapha"] = "moderate"     # small, slow, low metabolic demand
    if role == "finisher" and not explosive:
        d["kapha"] = "good"         # steady conditioning is exactly Kapha's need
        d["pitta"] = "good"
    return d


def _goals(entry: dict) -> dict:
    """Which goals a movement can serve.

    The first version of this read `endurance` as "cardio or a hold", which is
    what the word means in isolation and not what the field is for: it decides
    which movements a plan may draw on, so a push-up scoring false for endurance
    left a home user's endurance plan with zero chest options. Resistance work
    trains muscular endurance — the rep range is the plan's job, not the
    library's."""
    cardio = entry["category"] == "cardio"
    compound = entry["mechanic"] == "compound"
    working = entry["role"] in schema.WORKING_ROLES
    conditioning = entry["role"] == "finisher"
    return {
        "fat_loss": cardio or working or conditioning,
        "muscle_gain": working,
        "endurance": cardio or working or conditioning,
        "strength": working and compound,
        "general_fitness": True,
        "flexibility": entry["role"] == "mobility",
    }


# Contraindications, derived from MECHANISM — what the movement does to a joint
# or to blood pressure — and unioned with whatever the spec states outright.
#
# The previous library's tags came from `fill_gym_contraindications.py`, which
# matched keywords against exercise names. That is the pass whose 884 outputs the
# clinical packet exists to review, and sampling a dozen of its rules found four
# faults. These rules read the same authored fields the engine now programmes
# from — pattern, load class, impact, equipment — so a fault here is a fault in
# one rule over one mechanism, which is a thing a clinician can actually rule on.
#
# They are still DERIVED, and still need that review. `contraindication_basis`
# records which tags a human wrote and which a rule did, so the packet can put
# them in different columns instead of presenting all of them as equally settled.
_ELBOW_LOADS = {"curl", "hammer_curl", "preacher_curl", "triceps_extension",
                "skullcrusher", "triceps_pushdown"}
_AXIAL_LOADS = {"deadlift", "back_squat", "front_squat", "hack_squat",
                "good_morning", "push_press", "romanian_deadlift"}


def _derived_contraindications(entry: dict) -> set:
    tags: set = set()
    pattern, eq = entry["movement_pattern"], entry["equipment"]
    loaded = bool(entry["load_class"])
    lc = entry["load_class"]

    if pattern == "hinge" and loaded:
        tags |= {"herniated_disc", "lower_back_pain"}
    if pattern == "squat":
        tags.add("bad_knee")
        if eq == "barbell":
            tags |= {"herniated_disc", "osteoporosis"}
    if pattern == "lunge":
        tags |= {"bad_knee", "knee_replacement"}
    # Overhead work, and the shoulder isolation that takes the arm through the
    # same arc. `rotator_cuff` and `shoulder_injury` are two names a practitioner
    # may give the same restriction, and the engine treats them as separate
    # tokens — so a rule that emits one and not the other leaves half the people
    # who declared a shoulder problem unprotected.
    if pattern in ("push_v", "pull_v"):
        tags |= {"shoulder_injury", "rotator_cuff"}
    if lc in ("lateral_raise", "front_raise", "upright_row", "dip", "fly",
              "pullover", "straight_arm_pulldown"):
        tags |= {"shoulder_injury", "rotator_cuff"}
    # Loaded horizontal pressing. A bench press is among the most shoulder-
    # stressful lifts there is and carried no shoulder tag at all. The floor
    # press is deliberately exempt: its reduced range is exactly why it is the
    # press that a restricted shoulder can still do.
    if pattern == "push_h" and loaded and lc != "floor_press":
        tags |= {"shoulder_injury", "rotator_cuff"}
    if pattern in ("push_h", "push_v") and eq == "bodyweight":
        tags.add("wrist_injury")
    if entry["bucket"] == "core" and pattern in ("anti_extension", "rotation",
                                                 "isolation"):
        tags |= {"herniated_disc", "lower_back_pain"}
    if entry["impact"] == "high":
        tags |= {"bad_knee", "knee_replacement", "hypertension", "heart_disease"}
    if lc in _ELBOW_LOADS:
        tags.add("elbow_injury")
    if lc == "shrug":
        tags |= {"cervical_spondylosis", "neck_injury"}
    # Breath-holding strain against a heavy axial load. `hypertension` is the
    # tag the engine already uses for this mechanism, and for the over-60 age
    # proxy that rides on it.
    if lc in _AXIAL_LOADS and eq == "barbell":
        tags |= {"hypertension", "osteoporosis"}
    return tags


# Prenatal training is declared unsupported: the plan generates, and it carries a
# notice saying it is not a prenatal programme. That is a decision about SCOPE,
# and it does not excuse the library from having a defensible answer here — an
# unanswered field reads as `false` and empties the plan entirely, which is what
# a blank produced.
#
# So: a conservative allowlist, stated as a rule rather than left implicit, and
# flagged for the clinical review packet rather than presented as settled. Every
# exclusion below is a mechanism, not a movement name.
def _pregnancy_safe(entry: dict) -> bool:
    if entry["pregnancy_safe"] is not None:
        return entry["pregnancy_safe"]
    if entry["impact"] != "none":
        return False                                    # landing force
    if entry["skill_floor"] == "advanced":
        return False                                    # falls and failures
    if entry["bucket"] == "core" and entry["movement_pattern"] in (
            "anti_extension", "rotation", "isolation"):
        return False                                    # supine trunk work, twisting
    if entry["load_class"] in ("deadlift", "back_squat", "front_squat",
                               "push_press", "good_morning", "hip_thrust"):
        return False                                    # maximal axial load, Valsalva
    if entry["movement_pattern"] == "hinge" and entry["equipment"] == "barbell":
        return False
    if "Prone" in entry["name"] or "Superman" in entry["name"]:
        return False                                    # lying face down
    return True


# Energy cost per minute of work. Conditioning entries state their own; the rest
# are derived, because the honest input is how much muscle a movement moves and
# how hard, and that is exactly what `pattern`, `mechanic` and `role` record.
#
# Three flat values (3 / 5 / 7) covered 159 of 173 movements before this, which
# put a barbell squat and a lateral raise a single point apart. The engine turns
# these into the session's calorie estimate, so a flat table makes every session
# burn roughly the same amount whatever is in it.
_HEAVY_PATTERNS = {"squat", "hinge", "lunge", "carry"}
_LIGHT_PATTERNS = {"isolation", "rotation", "anti_rotation", "anti_extension"}


def _calories(entry: dict) -> int:
    if entry["calories_per_minute"]:
        return entry["calories_per_minute"]
    if entry["role"] in ("mobility", "warmup"):
        return 3
    pattern = entry["movement_pattern"]
    if entry["mechanic"] == "isolation":
        # Small muscle, small range, little of the body moving.
        return 4 if pattern in _LIGHT_PATTERNS else 5
    if pattern in _HEAVY_PATTERNS:
        # The whole lower body plus the trunk, under load.
        return 9 if entry["equipment"] in ("barbell", "machine") else 8
    if pattern in ("push_h", "push_v", "pull_h", "pull_v"):
        return 7 if entry["equipment"] in ("barbell", "machine", "cable",
                                           "dumbbell") else 6
    return 6


def _modification(entry: dict) -> str:
    if entry.get("modification"):
        return entry["modification"]
    prog = entry.get("progression") or {}
    if prog.get("easier"):
        return f"Too hard? Use {prog['easier']}. " + (
            f"Too easy? Move to {prog['harder']}." if prog.get("harder") else
            "Too easy? Add load or slow the tempo.")
    if entry["role"] in ("mobility", "warmup"):
        return "Ease into the range; never stretch into pain."
    return ("Slow the tempo or pause a beat to make it harder; shorten the range "
            "or reduce the load if form breaks down.")


# --------------------------------------------------------------- assembly ---
def build(upstream: dict, legacy: dict) -> tuple:
    out, errors, seen = [], [], set()
    for entry in SPEC:
        name = entry["name"]
        if name in seen:
            errors.append(f"{name}: duplicate entry in the spec")
            continue
        seen.add(name)

        # Upstream first, then this project's own earlier authoring. Both are
        # prose sources; neither supplies judgment — every classifying field on
        # the row below comes from the spec.
        src = upstream.get(entry["src"]) if entry["src"] else None
        leg = legacy.get(entry["src"]) if entry["src"] else None
        if entry["src"] and src is None and leg is None:
            errors.append(f"{name}: src {entry['src']!r} found in neither source")

        instructions = (entry["instructions"] or (src or {}).get("instructions")
                        or (leg or {}).get("instructions"))
        pm = (entry["primary_muscles"] or (src or {}).get("primaryMuscles")
              or (leg or {}).get("primary_muscles") or [])
        sm = (entry["secondary_muscles"] or (src or {}).get("secondaryMuscles")
              or (leg or {}).get("secondary_muscles") or [])

        row = {
            "id": _id(name),
            "name": name,
            "category": entry["category"],
            "equipment": entry["equipment"],
            "level": entry["level"],
            "skill_floor": entry["skill_floor"],
            "primary_muscles": list(pm),
            "secondary_muscles": list(sm),
            "bucket": entry["bucket"],
            "movement_pattern": entry["movement_pattern"],
            "mechanic": entry["mechanic"],
            "family": entry["family"],
            "role": entry["role"],
            "canonical": entry["canonical"],
            "load_class": entry["load_class"],
            "impact": entry["impact"],
            "unilateral": entry["unilateral"],
            "rep_style": entry["rep_style"],
            "instructions": list(instructions or []),
            "coaching_cue": entry["cue"],
            "progression": {k: v for k, v in (entry["progression"] or {}).items() if v},
            "sets_reps": _sets_reps(entry),
            "contraindications": sorted(set(entry["contraindications"])
                                        | _derived_contraindications(entry)),
            "contraindications_authored": sorted(set(entry["contraindications"])),
            "pregnancy_safe": _pregnancy_safe(entry),
            "dosha_suitability": entry["dosha_suitability"] or _dosha(entry),
            "goal_suitability": entry["goal_suitability"] or _goals(entry),
            "calories_per_minute": _calories(entry),
            "modification": _modification(entry),
            "source": (entry["src"] if src else
                       f"authored ({entry['src']})" if leg else "authored"),
        }
        # `contraindications_reviewed` is the field the clinical packet exists to
        # raise. 18 rows carried it, and a rebuild that silently dropped them
        # would be discarding the only clinician-checked data in the library —
        # so it is carried across for any movement that survived the curation.
        row["contraindications_reviewed"] = bool(
            (leg or {}).get("contraindications_reviewed"))
        errors.extend(schema.validate({**entry, **row}))
        out.append(row)

    out.sort(key=lambda r: (r["bucket"], r["role"], r["name"]))
    return out, errors


def coverage(rows: list) -> dict:
    """Every (bucket, equipment tier) a plan can be asked for needs enough
    options that four weeks do not repeat. Reported so a thin cell is visible
    before a user finds it — the old library had five bodyweight back exercises
    and three of them were prone raises."""
    tier = {"bodyweight": "BW", "bands": "BW", "dumbbell": "DB",
            "kettlebell": "DB", "barbell": "BB", "machine": "MC", "cable": "MC"}
    cells = {}
    for r in rows:
        if r["role"] not in schema.WORKING_ROLES:
            continue
        cells.setdefault((r["bucket"], tier.get(r["equipment"], "OT")),
                         []).append(r["name"])
    return cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="fail if the written library differs from the spec")
    args = ap.parse_args()

    upstream = load_upstream()
    rows, errors = build(upstream, load_legacy())

    if errors:
        print(f"\n  {len(errors)} spec error(s):")
        for e in errors:
            print(f"    - {e}")
        sys.exit(1)

    payload = json.dumps(rows, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        current = OUT.read_text() if OUT.exists() else ""
        if current != payload:
            print("  gym_exercises.json is stale — run scripts/build_gym_library.py")
            sys.exit(1)
        print(f"  gym_exercises.json is in sync ({len(rows)} movements)")
        return

    OUT.write_text(payload)
    by_role = {}
    for r in rows:
        by_role[r["role"]] = by_role.get(r["role"], 0) + 1
    print(f"  wrote {OUT.name}: {len(rows)} movements")
    print(f"  by role: {by_role}")
    thin = {k: v for k, v in coverage(rows).items() if len(v) < 3}
    if thin:
        print(f"\n  thin cells (<3 working options):")
        for (bucket, t), names in sorted(thin.items()):
            print(f"    {bucket:10} {t}  {len(names)}  {names}")


if __name__ == "__main__":
    main()
