#!/usr/bin/env python3
"""RETIRED. `diet_foods.json` is authored, not generated.

This script produced the entire Ayurvedic layer of the 150-food library from a ten-row
table of category defaults, roughly six hand-listed name overrides per axis, and
substring matches on the food's id (`if "bitter" in name`). What that produced, measured
over its own output:

  * **Six distinct rasa combinations** across 150 foods, 78 of them simply `["sweet"]`.
    Six rasas admit 63 non-empty combinations; the authored library uses 24.
  * **Zero foods with sour Vipaka.** The generator can only ever write `madhura` or
    `katu`, so one of the three classical values was unreachable and every sour food —
    tomato, curd, lemon, tamarind, banana — carried a Vipaka that could not be right.
    The authored library has 12.
  * **`season_suitable: ["all"]` on every row.** The field decided nothing, and the
    Ritucharya scoring in `diet_plan_engine` had nothing to score against.
  * **`best_for` empty on 140 of 150**, populated by six substring rules.
  * **No `guna` field at all** — while `diet_llm_generator`'s system prompt requires
    every meal to cite "Rasa (taste), Guna (quality), Virya (potency), Vipaka", so the
    model invented that axis on every meal of every plan.
  * **Nutrition a per-category constant on 109 of 150.** 27 vegetables reported
    identical calories, protein, carbs, fat and fibre. Coconut sat at 50 kcal and
    0.2 g fat against roughly 354 kcal and 33 g. The engine sums these into the macro
    bar the user reads.
  * **Five rows whose vipaka contradicted their own rasa**, because vipaka came from
    the category before rasa was overridden by name.

Against the authored library, the values this script wrote differ on 83 of 150 rows for
rasa, 46 for vipaka, 42 for virya, 134 for dosha effect, 128 for nutrition and all 150
for ritu. An eighty-fourth row, `raw_papaya`, carries the same two rasas in the other
order — which is a difference too, since the first is the dominant one, but it is not
the same kind of difference and is not counted above.

The library is now built by `scripts/build_diet_library.py` from the curated spec in
`scripts/diet_library/`, one module per category. Judgment lives in the spec, the
definitional maps in `diet_library.schema.to_kb_row` do the translation, and nothing is
inferred from a name.

Kept as a refusing stub rather than deleted for the reason `scripts/seed_gym_exercises.py`
and `scripts/seed_panchakarma_therapies.py` are: running it is the one action that would
quietly undo the authored library, and a missing file is easier to restore from git than
a quietly regenerated one is to notice.
"""
import sys

MESSAGE = __doc__


def main():
    print(MESSAGE)
    print("Refusing to run. Use:  python scripts/build_diet_library.py --write")
    sys.exit(1)


if __name__ == "__main__":
    main()
