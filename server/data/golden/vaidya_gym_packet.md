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
engine programmes from stated explicitly instead of inferred from names. Every
instruction is written for this product too: 89 of the 120 entries that reused
the dataset's prose carried a defect, including a dumbbell exercise whose steps
told you to pick up a barbell and two that instructed holding your breath under
load — the exact mechanism `hypertension` is tagged for. Upstream now supplies
muscle lists and nothing else. The same sweep now prescribes a stretch as a
working set on 0% of days.

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

**Every one of the 173 movements now carries a hand-written clinical judgment
with a stated reason.** Contraindications, pregnancy suitability and dosha were
derived by rule until this pass; they are now authored per movement in
`scripts/gym_library/clinical.py`, and the CSV carries three columns for each:

- **`contraindications`** — the answer that ships.
- **`why`** — the mechanism, in a sentence. This is what makes your job
  confirmation rather than archaeology: you read the reasoning and agree or
  disagree with it, instead of inferring intent from a list of tags.
- **`what_a_rule_would_have_said`** — what the previous mechanism rule produced.

**The last column is where to look first.** The authored answer differs from the
rule on **89 of the 173 movements**, and each difference is a decision somebody
made. Three that show why the rules were not enough:

| movement | rule said | authored | reason |
|---|---|---|---|
| `Barbell Bench Press` | pregnancy-safe | **not** pregnancy-safe | The rule modelled impact, skill and load, and had no concept of body position. Every supine press came out safe. |
| `Wall Slide` | avoid with shoulder injury | **no restriction** | It is a scapular rehab drill — the rule withheld the treatment from the people it is for. |
| `Renegade Row` | no restriction | shoulder + low back | A plank held under a rowing load. No single mechanism rule saw it. |

Nothing here has been read by a practitioner. `contraindications_reviewed` stays
false on all 173 until one does — this is engineering's best reasoning, written
down so it can be checked.

## Priority order

1. **The rows where the authored answer differs from the rule** — the
   `what_a_rule_would_have_said` column in `gym_exercise_review.csv`. 89 of 173.
   Then the rows marked `REVIEW` in `gym_mechanism_review.csv`, top to bottom.
   They are the mechanism groups where a tag applies to some of the group and not
   the rest. Some of these are deliberate: `row/back` carries `herniated_disc` on
   3 of 11 because a bent-over barbell row loads the spine and a chest-supported
   row does not. Confirming that distinction is as useful as correcting one.
2. **The four decisions below**, which engineering made and which need a
   clinician's confirmation.
3. **Cardiovascular tagging as a whole** — `(locomotion)/cardio` is the group
   with the widest spread and the worst consequences.

## Four decisions needing your confirmation

1. **Prenatal suitability is now decided per movement, and 91 of 173 pass.**
   Prenatal training is still declared unsupported — the plan generates and
   carries a notice saying it is not a prenatal programme — but the field cannot
   be left blank, because an unanswered `pregnancy_safe` reads as `false` and
   empties the plan entirely. The reasoning behind each is in the `why` column;
   the recurring grounds for exclusion are supine and prone positions, landing
   impact, hanging, loaded spinal flexion, and maximal bracing. **Confirm the
   grounds, and spot-check the movements that pass.**

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

## Risk mechanisms — the conditions that are not body parts

`gym_risk_mechanism_review.csv`, eight rows. The contraindication tags above name
body parts, and until 2026-09 only 8 of the 70 conditions onboarding offers
changed a gym plan at all. Glaucoma, epilepsy, vertigo, a hernia and rheumatoid
arthritis had nothing to reach.

Each movement now also carries the **mechanism** it works through — spinal
flexion, head below heart, intra-abdominal pressure, fall risk, a load that lands
on the body if control is lost, wrist weight-bearing, neck load, lumbar extension —
in the same vocabulary the yoga engine uses, and one shared map
(`engine/movement_risk.py`) names the conditions each mechanism is withheld for.
Joint conditions (osteoarthritis, rheumatoid arthritis, gout, fibromyalgia,
neuropathy, declared obesity) now also withhold landing impact.

Each row states the reason once and lists its movements. **Rule on the group:**
is the mechanism right, are the listed movements the ones that carry it, and are
the conditions the right ones. Two choices to confirm specifically:

- **Fall risk is not withheld by age alone.** Balance and stepping are what older
  adults most need to keep; the conditions that make a fall likely or dangerous
  (osteoporosis, vertigo, neuropathy, Parkinson's, epilepsy) withhold it instead.
- **Herniated disc is not mapped to spinal extension**, matching the yoga engine:
  extension is often the therapeutic direction for a posterior herniation.

## Before-you-train notes

`gym_condition_guidance_review.csv`, one row per note. For diabetes, asthma,
epilepsy, heart disease and a dozen others no movement is the problem — the
session is — so the plan now shows a short note before the first set, each with
its published source. **Confirm the wording and the thresholds** (the glucose
and blood-pressure cut-offs in particular), and say whether any note should stop
the plan being generated rather than accompany it.

Alongside them, **sets of 3-5 at near-maximal load are replaced with 8-12** for
hypertension, heart disease, glaucoma and retinopathy, a hernia or recent
abdominal surgery, pregnancy and everyone over 60. The mechanism is the
Valsalva manoeuvre. Confirm the list, and whether diabetes (for its retinopathy
risk) belongs on it.

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
