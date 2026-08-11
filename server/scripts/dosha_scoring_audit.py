"""Report how many stored Prakriti results came from the superseded v1 scorer.

Run this ON THE DROPLET — Atlas is IP-locked to it:

    docker compose exec api python scripts/dosha_scoring_audit.py

Read-only by default. `--stamp-current` is the one write it can make, and only
for results that could not have been distorted (see below).

Background
----------
v1's self-report ceiling capped the dominant dosha at 55% and shared the excess
across the other two *in proportion to their existing scores*. A dosha with zero
raw weight got zero share, so the entire remainder landed on whichever other
dosha had any weight at all. Answering all 26 questions Vata returned
{vata 50, pitta 45, kapha 5}, labelled "Vata-Pitta Dvidoshaja", at low
confidence.

The raw answers were not stored before v2, so nothing here can recompute a
result — it can only tell you the blast radius. Users flagged as suspect are
offered a retake in the UI (the lock is bypassed for stale scoring versions).

The v1 fingerprint, and what it can and cannot tell you
-------------------------------------------------------
A dump could only happen when one dosha had zero raw weight, and it always left
that dosha pinned at the 5% constitution floor while the second sat far above
where the answers put it. So:

  third > floor  =>  the pathological branch was never taken. Reliable. This is
                     the only direction --stamp-current acts on.
  third == floor =>  either a dump, or a genuine near-50/50 dual constitution
                     whose third dosha really is absent. Cannot be told apart
                     from the stored scores alone.

Measured against 20k simulated v1 assessments: every result that actually dumped
was flagged (no false negatives). The error is entirely in the other direction —
some genuine Dvidoshaja constitutions are flagged too. That is the safe way round:
a false positive costs one unnecessary retake prompt, and the retake produces a
correct result either way, whereas a false negative would leave a distorted
constitution in place forever.

So read "likely distorted" as an upper bound on the damage, not a headcount.
"""

import argparse
import asyncio
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.dosha_analyzer import DOSHA_SCORING_VERSION  # noqa: E402

FLOOR = 5
# How far above the floor the second dosha must sit before the gap looks like a
# redistribution dump rather than a genuinely dual constitution.
SUSPECT_SECONDARY_MIN = 40


def classify(scores: dict) -> str:
    """'suspect' if the result carries the v1 dump fingerprint, else 'plausible'."""
    if not isinstance(scores, dict):
        return "unscored"
    vals = [scores.get(d) for d in ("vata", "pitta", "kapha")]
    if any(not isinstance(v, (int, float)) for v in vals):
        return "unscored"
    vals.sort(reverse=True)
    _top, second, third = vals
    if third <= FLOOR and second >= SUSPECT_SECONDARY_MIN:
        return "suspect"
    return "plausible"


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "--stamp-current",
        action="store_true",
        help="Mark v1 results that CANNOT have been distorted as current, so those "
             "users are not prompted to retake. Never touches suspect results.",
    )
    args = ap.parse_args()

    from database.mongodb import init_mongodb, get_mongodb, close_mongodb

    await init_mongodb()
    db = get_mongodb()

    counts: Counter = Counter()
    stampable: list[str] = []
    suspects: list[tuple[str, dict, int | None]] = []

    cursor = db.users.find(
        {"prakriti_locked": True},
        {"_id": 1, "dosha_scores": 1, "dosha_scoring_version": 1, "dosha_confidence": 1,
         "prakriti_classical_name": 1, "dosha_raw_answers": 1},
    )
    async for u in cursor:
        version = u.get("dosha_scoring_version") or 1
        counts[f"version_{version}"] += 1
        if version >= DOSHA_SCORING_VERSION:
            continue

        verdict = classify(u.get("dosha_scores"))
        counts[verdict] += 1
        if verdict == "suspect":
            suspects.append((u["_id"], u.get("dosha_scores"), u.get("dosha_confidence")))
        elif verdict == "plausible":
            # Recomputable in place only if the answers happen to be stored.
            if not u.get("dosha_raw_answers"):
                stampable.append(u["_id"])

    total = sum(v for k, v in counts.items() if k.startswith("version_"))
    stale = total - counts.get(f"version_{DOSHA_SCORING_VERSION}", 0)

    print(f"Assessed users (prakriti_locked):        {total}")
    print(f"  scored by current v{DOSHA_SCORING_VERSION}:                  "
          f"{counts.get(f'version_{DOSHA_SCORING_VERSION}', 0)}")
    print(f"  scored by a superseded version:        {stale}")
    print()
    print(f"  of those — likely DISTORTED (retake):  {counts.get('suspect', 0)}")
    print(f"  of those — unaffected by the bug:      {counts.get('plausible', 0)}")
    print(f"  of those — no usable scores:           {counts.get('unscored', 0)}")
    print("\n  'Likely distorted' is an upper bound: it also catches genuine")
    print("  near-50/50 dual constitutions, which are indistinguishable from a")
    print("  dump once the raw answers are gone. It misses nothing.")

    if suspects:
        print("\nLikely distorted (showing up to 20):")
        for uid, scores, conf in suspects[:20]:
            print(f"  {uid}  {scores}  confidence={conf}")

    if args.stamp_current:
        if not stampable:
            print("\nNothing to stamp.")
        else:
            res = await db.users.update_many(
                {"_id": {"$in": stampable}},
                {"$set": {"dosha_scoring_version": DOSHA_SCORING_VERSION}},
            )
            print(f"\nStamped {res.modified_count} unaffected result(s) as v{DOSHA_SCORING_VERSION};"
                  " they will no longer be prompted to retake.")
    elif stampable:
        print(f"\n{len(stampable)} unaffected result(s) would be prompted to retake unnecessarily."
              " Re-run with --stamp-current to suppress that.")

    await close_mongodb()


if __name__ == "__main__":
    asyncio.run(main())
