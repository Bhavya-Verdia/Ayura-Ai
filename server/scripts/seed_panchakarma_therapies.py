#!/usr/bin/env python3
"""RETIRED. `panchakarma_therapies.json` is authored, not generated.

This script held a 23-row Python copy of the file and rewrote it wholesale. It was
written when the rows carried only scheduling attributes, and it stopped being a
generator the first time a field was authored into the JSON without being copied
back here — which happened twice, in opposite directions, and neither showed up as
a failing test because nothing ran the script.

What running it would have deleted, verified against the file as it stands:

  * `contraindications`, `contraindications_reviewed` and `contraindications_basis`
    on all eight Pradhana rows that carry them — the pregnancy and nursing bars on
    Vamana, Virechana, both clinical Basti rows, Matra Basti, both Nasya rows and
    Raktamokshana. Those fields exist so the data agrees with the gate the engine
    applies; a run would have put the two back out of agreement, silently.
  * `karma`, `karma_reviewed` and `karma_basis` on all 23 rows. The engine derives
    `_KARMA_ROWS` from that tag, so a run would empty the map the declared-capability
    gate uses to find a Karma's rows and every Karma would be withdrawn as having
    "no route" for the patient's setting.

It is kept as a refusing stub rather than deleted for the same reason
`scripts/seed_gym_exercises.py` is: running it is the one action that would quietly
undo authored clinical data, and a missing file is easier to restore from git than
a quietly regenerated one is to notice.

Edit `server/data/knowledge_base/panchakarma_therapies.json` directly. Its shape is
enforced by `server/tests/test_panchakarma_karma_tag.py` and the contraindication
tests beside it.
"""
import sys

MESSAGE = __doc__


def main():
    print(MESSAGE)
    print("Refusing to run. Edit data/knowledge_base/panchakarma_therapies.json instead.")
    sys.exit(1)


if __name__ == "__main__":
    main()
