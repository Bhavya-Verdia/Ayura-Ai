# Ayura AI — Gym Knowledge Base Review Packet

_For a clinical exercise professional: a physiotherapist, sports physician, or
BAMS practitioner with exercise-prescription training. Estimated effort: ~half a day._

## Why this exists

The gym feature's engine logic is independently tested — 270+ automated tests
cover the programming, the load prescription, the scheduling and the safety
gating, and a plan sweep across eleven profile types confirms that no exercise
carrying a contraindication ever reaches a practitioner who declared that
condition.

**What none of that can certify is whether the contraindications are right.**

The library holds **173 movements**, and **none** of them carries
`contraindications_reviewed`. That is the last thing standing between this
feature and launch, and it is the one thing engineering cannot do for itself.

## What changed since the previous version of this packet

The previous packet asked for review of **902 exercises, 884 of them unreviewed,
carrying 242 tag rules of which 116 were applied inconsistently.**

That library was imported from a public dataset (`free-exercise-db`) by a script
that re-derived `category`, `level` and `mechanic` from substring matches on the
exercise NAME, discarding the upstream fields that stated all three correctly.
176 of 779 imported rows — 23% — ended up contradicting their own source. The
consequences reached the plan: **46% of generated training days prescribed a
stretch as a working set**, and 502 of the 902 rows were never prescribed to
anybody across a 28,320-day sweep.

**The library is now authored rather than imported.** 173 movements, curated to
cover every region and equipment tier a plan can ask for, with the fields the
engine programmes from stated explicitly instead of inferred from names. Upstream
is still used — for exercise instructions and anatomy, where it is good — but
nothing about how a movement is programmed comes from it. The same sweep now
prescribes a stretch as a working set on 0% of days.

Two consequences for you:

1. **The review is about half the size it was**, and it is a review of authored
   rows rather than an audit of keyword matches: 34 tag rules across 12
   mechanism groups, 19 of them applied inconsistently.
2. **The 18 previously-reviewed rows are gone, and the count reset to zero.**
   This is a real cost, stated plainly rather than papered over. Those 18 were
   `Brachialis-Smr`, `Latissimus Dorsi-Smr`, `Rhomboids-Smr`, `Gironda Sternum
   Chins`, `London Bridges` and a dozen like them — foam-rolling entries and
   specialty variants that a curated library correctly does not contain. No
   review of a movement that survived curation was discarded.

## How the tags got here

Every contraindication on a movement is one of two things, and the CSV tells you
which:

- **Authored** — written deliberately for that movement. Listed in the
  `contraindications_authored` column.
- **Derived** — produced by a mechanism rule in `scripts/build_gym_library.py`.
  A loaded hinge carries `herniated_disc` and `lower_back_pain`; overhead work
  carries `shoulder_injury` and `rotator_cuff`; high-impact work carries
  `bad_knee`, `knee_replacement`, `hypertension` and `heart_disease`; a heavy
  axial barbell lift carries `hypertension` and `osteoporosis` for the
  breath-holding strain.

The derived rules read the movement's authored **pattern, load class, impact and
equipment** — never its name. That is the difference from the previous version of
this packet: a fault is now a fault in one rule over one mechanism, which is
something you can rule on in a sentence, rather than a keyword that happened to
match a word in a title.

## Priority order

1. **The 19 rows marked `REVIEW` in `gym_mechanism_review.csv`**, top to bottom.
   They are the mechanism groups where a tag applies to some of the group and not
   the rest. Some of these are deliberate: `row/back` carries `herniated_disc` on
   3 of 11 because a bent-over barbell row loads the spine and a chest-supported
   row does not. Confirming that distinction is as useful as correcting one.
2. **The four decisions below**, which engineering made and which need a
   clinician's confirmation.
3. **Cardiovascular tagging as a whole** — `(locomotion)/cardio` is the group
   with the widest spread and the worst consequences.

## Four decisions needing your confirmation

1. **Prenatal safety is a derived allowlist.** Prenatal training is declared
   unsupported — the plan generates and carries a notice saying it is not a
   prenatal programme. But the field cannot be left blank (an unanswered
   `pregnancy_safe` reads as `false` and empties the plan entirely), so it is a
   stated conservative rule: excluded if the movement has any landing impact, an
   advanced skill floor, is supine or rotational trunk work, is a maximal axial
   barbell lift, or is performed lying face down. **Confirm the rule, or replace
   it.**

2. **`hypertension` is used as the age proxy for cardiovascular strain**, the way
   `osteoporosis` is used for axial loading. It means a practitioner over 60 is
   kept away from breath-holding strain work and maximal conditioning whether or
   not they have declared a cardiovascular condition. **Confirm the threshold
   (60) and the mechanism.**

3. **Impact work is withheld at obese BMI classifications** — jumping, skipping,
   running, at every training age. Resistance work is untouched. The reasoning is
   landing force through the knee and ankle. **Confirm, and say whether it should
   also apply at `overweight`.**

4. **`skill_floor` is separated from `level`.** `level` is the training age at
   which a movement is appropriate to *programme*; `skill_floor` is the training
   age needed to *perform* it at all. A pull-up is `skill_floor: intermediate` —
   an untrained 118 kg beginner cannot do one, and used to be prescribed
   `3 x 15-20` of them. Barbell lifts are `skill_floor: beginner`, on the view
   that they are coached from day one. **Confirm that split, and the pull-up and
   barbell placements in particular.**

## What happens to your answers

Every `N` with a correction goes into the movement spec in
`scripts/gym_library/`, and is covered by a regression test so it cannot silently
revert. Rows you confirm get `contraindications_reviewed: true`, which is the
field this packet exists to raise — currently from zero.

Regenerate this packet after any library change:

```bash
python scripts/build_gym_library.py       # rebuild the library from the spec
python scripts/build_gym_review_packet.py
```
