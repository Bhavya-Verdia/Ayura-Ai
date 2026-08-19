#!/usr/bin/env python3
"""RETIRED. The gym library is no longer imported — it is authored.

This script used to build `gym_exercises.json` from free-exercise-db. It is kept
as a stub rather than deleted because running it is the one action that would
silently undo the curated library, and a missing file is easier to restore from
git than a quietly re-imported one is to notice.

What it did, and why that is not recoverable by patching it:

  * It re-derived `category` from a substring match on the exercise NAME
    (`if "stretch" in name`), discarding the upstream field. 57 stretches, 31
    plyometrics and 70 olympic/powerlifting/strongman lifts were filed as plain
    `strength` — 176 of 779 rows, 23%, contradicting their own source. The
    downstream effect was that 46% of generated training days prescribed a
    stretch as a working set.
  * It set `level` by asking whether the word "beginner" appeared in the name,
    turning upstream's 523 beginner movements into 56. Every foundational lift
    became "intermediate", which is why a beginner-only gate was impossible and
    a 118 kg sedentary beginner was prescribed `Pullups 3x15-20`.
  * It read `mechanic` (compound/isolation) for one narrow bodyweight special
    case and then dropped it, so the engine had to infer compound-ness by
    counting secondary muscles — and decided a fly was a compound.
  * It branched on `ex["bodyPart"]`, a key this dataset does not have. That
    branch could never fire.
  * It derived `dosha_suitability` from the EQUIPMENT, marking all 179 barbell
    exercises `pitta: avoid` and hiding a barbell from two constitutions in
    three. That was fixed in the data and never here, so every run reintroduced
    it.

The library is now built by `scripts/build_gym_library.py` from the curated spec
in `scripts/gym_library/`. Upstream is still used — for instructions and
anatomy, where it is good — but nothing is inferred from a name.
"""
import sys

MESSAGE = __doc__


def main():
    print(MESSAGE)
    print("Refusing to run. Use:  python scripts/build_gym_library.py")
    sys.exit(1)


if __name__ == "__main__":
    main()
