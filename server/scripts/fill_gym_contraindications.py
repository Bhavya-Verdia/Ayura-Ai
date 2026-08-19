#!/usr/bin/env python3
"""RETIRED. Contraindications are part of the authored library now.

This was a one-shot pass that inferred biomechanical contraindications for the
647 imported exercises that had none, by matching keywords against exercise
names. It is the pass whose 884 outputs the clinical review packet exists to
review, and sampling roughly a dozen of its rules turned up four faults.

Two reasons it is a stub rather than a deleted file:

  * Running it against the curated library would fill in tags nobody authored,
    beside tags somebody did, with no way to tell them apart afterwards. The
    packet's `contraindications_authored` column depends on that distinction.
  * Its inputs were names. `("bent over", ...)` tagged every exercise with those
    words for `herniated_disc` — including the chest-supported rows, whose whole
    point is that the bench takes the spine out of it.

Contraindications now come from two places, and `scripts/build_gym_library.py`
records which:

  * authored — written for the movement in `scripts/gym_library/movements_*.py`
  * derived  — a mechanism rule in the builder, reading the movement's authored
               pattern, load class, impact and equipment; never its name

To change one, edit the spec and rebuild:

    python scripts/build_gym_library.py
    python scripts/build_gym_review_packet.py
"""
import sys

MESSAGE = __doc__


def main():
    print(MESSAGE)
    print("Refusing to run. Edit scripts/gym_library/ and rebuild instead.")
    sys.exit(1)


if __name__ == "__main__":
    main()
