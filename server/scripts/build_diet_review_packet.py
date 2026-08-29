"""Generate the clinical review packet for the authored diet food library.

All 150 foods carry `reviewed: false`. Every Ayurvedic value in the file is an
authored judgement, and 708 of the claims are clinical: this food is Pathya in that
condition, that food is Apathya in this one. The engine composes meals from them and
the LLM path is grounded on the corpus built from them, so a wrong Apathya is a food
withheld from a patient and a wrong Pathya is a food put in front of one.

## Why this is not shaped like the gym packet

`build_gym_review_packet.py` groups by mechanism and sorts by partial coverage,
because those tags were produced by RULES — the errors are systematic, so the
reviewable unit is the rule rather than the row. That reasoning does not transfer.
This library is authored row by row; a mistake in one row says nothing about the next,
and there is no rule to review instead.

What replaces it is a different question: **where does a claim disagree with the row
that carries it?** The library's own schema requires that an effect running against
both rasa and virya state a Prabhava — a departure needs a stated reason. The clinical
tags were never held to that rule. So the screen applies it to them, and what surfaces
is the seam between two systems of reasoning:

    olive_oil       Pathya in high_cholesterol   — but guru, snigdha, Kapha +1
    walnuts         Pathya in high_cholesterol   — but guru, snigdha, Kapha +1
    broccoli        Apathya in hypothyroid       — but laghu, Kapha -1

Those are not Ayurvedic claims. Olive oil and walnuts are indicated because
unsaturated fat lowers LDL, and brassicas are withheld because of goitrogens. Both may
well be right — but they are biomedical findings entered into a classical field, and
the app presents the result to the user as Ayurveda. Whether `high_cholesterol` is
being reasoned about as Medoroga (where guru snigdha is Apathya) or as a lipid panel
(where olive oil is indicated) is a question only a Vaidya can settle, and it changes
every row in that condition at once.

The screen is a SCREEN, not a finding. It states which rule fired so a reviewer can
dismiss it in one read.

Run: cd server && ./venv/bin/python scripts/build_diet_review_packet.py
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "data" / "golden"
KB = BASE / "data" / "knowledge_base" / "diet_foods.json"

# The conditions the app reasons about as Kapha/Meda accumulation. A food withheld
# from or indicated for one of these can be judged against the row's own guna and
# dosha effect, which is what makes the screen possible at all.
_KAPHA_MEDA = {"obesity", "hypothyroid", "thyroid", "fatty_liver", "high_cholesterol",
               "diabetes", "pcos"}
# Grahani and IBS admit ruksha, Vata-raising foods through the Grahi (binding) action —
# which is exactly the kind of departure the library requires a Prabhava for.
_GRAHI = {"grahani", "ibs", "diarrhea"}


def _load():
    return json.loads(KB.read_text(encoding="utf-8"))


def _fmt(v):
    return "; ".join(str(x) for x in v) if isinstance(v, (list, tuple)) else str(v or "")


def _profile(row):
    a = row["ayurvedic"]
    d = a["dosha_effect"]
    return (set(a.get("guna") or []), d,
            f"V{d['vata']:+d} P{d['pitta']:+d} K{d['kapha']:+d}")


def screen(row, condition, kind):
    """Does this clinical claim disagree with the row carrying it?

    Returns the name of the rule that fired and what it saw, or ("", "").

    Each rule asks the question the library already asks of its own dosha effects:
    the claim runs against the food's stated qualities — is there a reason on record?
    A row with a Prabhava has answered that; a row without has not.
    """
    guna, d, _ = _profile(row)
    has_reason = bool(row["ayurvedic"].get("prabhava"))

    if condition in _KAPHA_MEDA:
        if kind == "pathya" and d["kapha"] > 0 and "guru" in guna and not has_reason:
            return ("indicated_in_kapha_condition_but_kapha_building",
                    "guru and Kapha-raising, with no Prabhava stating why it is given")
        if kind == "apathya" and d["kapha"] < 0 and "laghu" in guna and not has_reason:
            return ("withheld_in_kapha_condition_but_kapha_reducing",
                    "laghu and Kapha-reducing, so the classical profile does not "
                    "explain the restriction")
    if condition in _GRAHI and kind == "pathya":
        if "ruksha" in guna and d["vata"] > 0 and not has_reason:
            return ("indicated_in_grahani_but_ruksha_vata_raising",
                    "ruksha and Vata-raising; defensible through Grahi action, but "
                    "no Prabhava states it")
    if condition == "acidity" and kind == "pathya" and d["pitta"] > 0:
        return ("indicated_in_amlapitta_but_pitta_raising",
                "raises Pitta by its own dosha effect")
    return ("", "")


def build_clinical_claims(rows):
    """One row per (food x condition) Pathya/Apathya claim — the safety-critical axis.

    Sorted by condition rather than by food, because that is the unit a clinician
    reasons in: "what is Apathya in Amlapitta" is answered once for the whole group,
    and an outlier is visible only next to its peers. Screened rows sort to the top of
    their condition.
    """
    out = []
    for row in rows:
        ref = row.get("nighantu_ref") or {}
        extrapolated = ref.get("text") == "modern_extrapolated"
        _, _, dosha = _profile(row)
        a = row["ayurvedic"]
        for kind in ("pathya", "apathya"):
            for condition in row.get(f"{kind}_for", []):
                rule, saw = screen(row, condition, kind)
                out.append({
                    "condition": condition,
                    "claim": kind,
                    "food": row["name"],
                    "food_id": row["id"],
                    "prep_state": row["prep_state"],
                    "rasa": _fmt(a["rasa"]),
                    "guna": _fmt(a.get("guna")),
                    "virya": a["virya"],
                    "vipaka": a["vipaka"],
                    "dosha_effect": dosha,
                    "prabhava": a.get("prabhava") or "",
                    "classical_entry": "no — extrapolated" if extrapolated else ref.get("text", ""),
                    "screen_rule": rule,
                    "screen_saw": saw,
                    "claim_ok": "", "should_be": "", "vaidya_notes": "",
                })
    out.sort(key=lambda r: (r["condition"], r["screen_rule"] == "", r["claim"], r["food"]))
    return out


def build_extrapolations(rows):
    """The foods with no classical entry, with the reasoning that stood in for one.

    These are where a fabricated citation would live if there were one. The `varga`
    field on an extrapolated row is not a Varga — it is the analogy that was drawn and
    the reason it was drawn, written to be rejected in one read.
    """
    out = []
    for row in rows:
        ref = row.get("nighantu_ref") or {}
        if ref.get("text") != "modern_extrapolated":
            continue
        a = row["ayurvedic"]
        _, _, dosha = _profile(row)
        out.append({
            "food": row["name"], "food_id": row["id"], "category": row["category"],
            "prep_state": row["prep_state"],
            "stated_reasoning": ref.get("varga", ""),
            "rasa": _fmt(a["rasa"]), "guna": _fmt(a.get("guna")),
            "virya": a["virya"], "vipaka": a["vipaka"], "dosha_effect": dosha,
            "pathya_for": _fmt(row.get("pathya_for")),
            "apathya_for": _fmt(row.get("apathya_for")),
            "gates_a_condition": "yes" if row.get("apathya_for") else "no",
            "analogy_ok": "", "profile_ok": "", "should_be": "", "vaidya_notes": "",
        })
    # Rows that withhold a food from a patient on no classical basis go first.
    out.sort(key=lambda r: (r["gates_a_condition"] != "yes", r["food"]))
    return out


def build_prabhava(rows):
    """Every stated Prabhava — by definition a claim that overrides the general rule.

    `schema.validate` admits a dosha effect running against both rasa and virya only
    when one of these is present, so each is load-bearing: it is the sentence that let
    the row into the corpus. If a Prabhava is wrong the row should not be there at all.
    """
    out = []
    for row in rows:
        a = row["ayurvedic"]
        if not a.get("prabhava"):
            continue
        _, _, dosha = _profile(row)
        out.append({
            "food": row["name"], "food_id": row["id"], "category": row["category"],
            "stated_prabhava": a["prabhava"],
            "rasa": _fmt(a["rasa"]), "guna": _fmt(a.get("guna")),
            "virya": a["virya"], "vipaka": a["vipaka"], "dosha_effect": dosha,
            "source": (row.get("nighantu_ref") or {}).get("text", ""),
            "prabhava_ok": "", "should_be": "", "vaidya_notes": "",
        })
    out.sort(key=lambda r: (r["category"], r["food"]))
    return out


def build_viruddha(rows):
    """Authored Viruddha Ahara pairs. A combination claim, not a property claim."""
    out = []
    for row in rows:
        for other in row.get("viruddha_with", []):
            out.append({
                "food": row["name"], "food_id": row["id"],
                "incompatible_with": other,
                "rasa": _fmt(row["ayurvedic"]["rasa"]),
                "virya": row["ayurvedic"]["virya"],
                "source": (row.get("nighantu_ref") or {}).get("text", ""),
                "pair_ok": "", "missing_pairs": "", "vaidya_notes": "",
            })
    out.sort(key=lambda r: (r["food"], r["incompatible_with"]))
    return out


def build_foods(rows):
    """One row per food: the six Ayurvedic axes, to be signed off as a whole."""
    out = []
    for row in rows:
        a = row["ayurvedic"]
        ref = row.get("nighantu_ref") or {}
        _, _, dosha = _profile(row)
        n = row.get("nutrition_per_100g") or {}
        out.append({
            "food": row["name"], "food_id": row["id"], "category": row["category"],
            "prep_state": row["prep_state"],
            "rasa": _fmt(a["rasa"]), "guna": _fmt(a.get("guna")),
            "virya": a["virya"], "vipaka": a["vipaka"],
            "dosha_effect": dosha, "prabhava": a.get("prabhava") or "",
            "season_suitable": _fmt(row.get("season_suitable")),
            "source": ref.get("text", ""), "varga_or_reasoning": ref.get("varga", ""),
            "kcal_per_100g": n.get("calories", ""),
            "nutrition_source": row.get("nutrition_source", ""),
            "rasa_ok": "", "guna_ok": "", "virya_ok": "", "vipaka_ok": "",
            "dosha_ok": "", "ritu_ok": "", "vaidya_notes": "",
        })
    out.sort(key=lambda r: (r["category"], r["food"]))
    return out


def _write(name, rows):
    path = OUT / name
    if not rows:
        return path, 0
    # newline="\n", not "" — csv writes \r\n per RFC 4180, git normalises it to \n on
    # commit, and the file is then dirty the moment it is regenerated. The drift test
    # would be comparing line endings rather than content.
    with path.open("w", newline="\n", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    return path, len(rows)


def build_packet_md(rows, counts, screened):
    total_claims = counts["claims"]
    by_rule = defaultdict(int)
    for r in screened:
        by_rule[r["screen_rule"]] += 1
    rule_lines = "\n".join(
        f"| `{rule}` | {n} |" for rule, n in sorted(by_rule.items(), key=lambda kv: -kv[1]))

    return f"""# Ayura AI — Diet Knowledge Base Review Packet

_For a BAMS-qualified Vaidya. Estimated effort: ~1.5 days if worked in the order below._

## Why this exists

`diet_foods.json` holds **{counts['foods']} foods**, and **every one of them carries
`reviewed: false`**. The file is authored — each Rasa, Guna, Virya, Vipaka, dosha
effect and Ritu is a judgement someone made and wrote down, with a citation where one
exists and a stated extrapolation where none does.

What engineering can certify is already certified: the file is generated from a spec
that no one can hand-edit, a validator refuses a dosha effect that contradicts both
rasa and virya unless a Prabhava is stated, and 30 tests hold the library and the
knowledge base together. **None of that says the values are clinically right.**

The reason it matters is that these values act. The rule engine composes meals from
them, and the LLM path is grounded on a corpus built from them, so:

- a wrong **Apathya** withholds a food from a patient who could have eaten it
- a wrong **Pathya** puts a food in front of a patient who should not

There are **{total_claims} clinical claims** ({counts['pathya']} Pathya,
{counts['apathya']} Apathya) across **{counts['conditions']} conditions**.

## What replaced the derived library

Until 2026-08-29 this file was generated by a script that produced the whole Ayurvedic
layer from a ten-row table of category defaults plus substring matches on the food's
id. It emitted **six** distinct rasa combinations for 150 foods, `season_suitable`
of `["all"]` on every row, no Guna axis at all, and **no sour Vipaka** — a value
unreachable in its table, and therefore wrong for every sour food in the library.

Nothing in that layer was ever reviewed either, so **no review is being discarded**.
The count did not reset; it was always zero.

## Work in this order

The tiers are ordered by what a wrong answer costs and by how far the claim sits from
a citable source — not by size. The first two are small and decisive.

### 1. `vaidya_diet_screened_claims.csv` — {counts['screened']} rows · start here

Claims that disagree with the food carrying them. The library already requires that a
dosha effect running against both rasa and virya state a Prabhava; these are the
clinical claims that would not survive the same test, with the rule that fired.

{rule_lines and '| rule | rows |\n|---|---|\n' + rule_lines}

Most of these are one question asked repeatedly: **is a modern indication being
entered into a classical field?** Olive oil and walnuts are Pathya in
`high_cholesterol` while being guru, snigdha and Kapha-raising — indicated because
unsaturated fat lowers LDL, which is not a Rasa-Guna-Virya-Vipaka argument. Brassicas
are Apathya in `hypothyroid` on goitrogens, not on their Ayurvedic profile.

They may be right. But whether `high_cholesterol` is Medoroga here (guru snigdha is
Apathya) or a lipid panel (olive oil is indicated) settles every row in that condition
at once, so answer it once and the tier collapses.

**A worked example of what this tier is for.** All three crucifers are Apathya in
`hypothyroid` and `thyroid`, and the library carries them **cooked** — there is no raw
row. But `diet_plan_engine`'s own protocol for both conditions avoids
`broccoli_raw`, `cabbage_raw` and `cauliflower_raw`, and the patient brief says the
Apathya is "raw crucifers". Goitrogen activity falls substantially with cooking, which
is presumably why the other two sources say raw.

So the library may be withholding cooked brassicas from every hypothyroid patient on a
caution that applies to the raw form. Please answer directly: **is cooked broccoli
Apathya in Galaganda, or only raw?** If only raw, these six rows come out.

Related and separate: `thyroid` and `hypothyroid` are two distinct conditions in this
app, not aliases, and eight foods are tagged identically for both. `thyroid` is the
umbrella (the brief maps it to Galaganda), so it covers hyperthyroid patients too —
for whom a goitrogen restriction may be exactly backwards. Worth one ruling.

### 2. `vaidya_diet_extrapolations.csv` — {counts['extrapolations']} rows

Foods with **no classical entry**, where an analogy stood in for a citation. The
`stated_reasoning` column is the analogy and the reason it was drawn, written to be
rejected in one read. **{counts['extrapolations_gating']} of them withhold a food from at
least one condition** on that basis, and those sort first.

Two questions per row: is the analogy sound, and does the profile follow from it.

### 3. `vaidya_diet_prabhava.csv` — {counts['prabhava']} rows

Every stated Prabhava. Each is load-bearing: the validator admits a row whose dosha
effect contradicts both its rasa and its virya **only** when one is present, so this
sentence is what let the row into the corpus. A wrong Prabhava is not a wrong note on
a good row — the row should not be there.

### 4. `vaidya_diet_viruddha.csv` — {counts['viruddha']} pairs across {counts['viruddha_foods']} foods

Authored Viruddha Ahara pairs. Also tell us what is **missing**: the
`missing_pairs` column is for combinations that should be here and are not, which is
the failure this file cannot show you on its own.

### 5. `vaidya_diet_clinical_claims.csv` — {total_claims} rows

The full Pathya/Apathya matrix, sorted **by condition** so each is one screen. This is
the long tier; it is also the one where an outlier is obvious next to its peers, which
is why it is grouped this way rather than by food.

### 6. `vaidya_diet_foods.csv` — {counts['foods']} rows

The six Ayurvedic axes per food, for whole-row sign-off. Tick columns are per axis, so
a row can be accepted on Rasa and rejected on Vipaka.

## How to record a verdict

Every CSV has empty `*_ok` columns and a `vaidya_notes` column. Use:

- **`y`** — correct as written
- **`n`** — wrong; put the correction in `should_be`
- **`?`** — defensible but not how you would write it; note why

A blank stays unreviewed. Partial returns are useful: a finished tier 1 and 2 is worth
more than a half-finished pass over all 150 foods, and the tiers are independent.

## What happens to your answers

`reviewed` becomes `true` per row only where a verdict was recorded. Corrections are
applied to `scripts/diet_library/` — the spec, not the JSON — and the knowledge base is
regenerated from it, so a correction cannot be silently lost in a later rebuild. The
nutrition corpus is reseeded from the same file, and `--check` fails if the two drift.

Rejections are as useful as confirmations. A row you reject is removed or corrected;
a row nobody looks at ships as it is, which is the situation this packet exists to end.
"""


def main() -> int:
    rows = _load()
    claims = build_clinical_claims(rows)
    screened = [r for r in claims if r["screen_rule"]]
    extrap = build_extrapolations(rows)
    counts = {
        "foods": len(rows),
        "claims": len(claims),
        "pathya": sum(1 for r in claims if r["claim"] == "pathya"),
        "apathya": sum(1 for r in claims if r["claim"] == "apathya"),
        "conditions": len({r["condition"] for r in claims}),
        "screened": len(screened),
        "extrapolations": len(extrap),
        "extrapolations_gating": sum(1 for r in extrap if r["gates_a_condition"] == "yes"),
        "prabhava": sum(1 for r in rows if r["ayurvedic"].get("prabhava")),
        "viruddha": sum(len(r.get("viruddha_with", [])) for r in rows),
        "viruddha_foods": sum(1 for r in rows if r.get("viruddha_with")),
    }

    OUT.mkdir(parents=True, exist_ok=True)
    written = [
        _write("vaidya_diet_screened_claims.csv", screened),
        _write("vaidya_diet_extrapolations.csv", extrap),
        _write("vaidya_diet_prabhava.csv", build_prabhava(rows)),
        _write("vaidya_diet_viruddha.csv", build_viruddha(rows)),
        _write("vaidya_diet_clinical_claims.csv", claims),
        _write("vaidya_diet_foods.csv", build_foods(rows)),
    ]
    md = OUT / "vaidya_diet_packet.md"
    md.write_text(build_packet_md(rows, counts, screened), encoding="utf-8")

    for path, n in written:
        print(f"  {path.relative_to(BASE)}  {n} rows")
    print(f"  {md.relative_to(BASE)}")
    print(f"\n{counts['foods']} foods, {counts['claims']} clinical claims, "
          f"{counts['screened']} screened, 0 reviewed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
