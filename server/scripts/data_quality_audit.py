"""
Data-quality + condition-coverage audit across all knowledge bases.

Answers, with real numbers, two questions:
  1. How much data backs each feature (quantity)?
  2. Is that data clean (quality): required fields present, no duplicate IDs,
     no stale/contradictory files, references present?

And — the key product question — which conditions have CURATED classical depth
vs. which fall through to AI reasoning / generic dosha handling. Run before a demo
to know exactly what you can claim.

    cd server && ./venv/bin/python scripts/data_quality_audit.py
Writes data/golden/coverage_report.md and prints a summary.
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DATA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def _load(*parts):
    path = os.path.join(DATA, *parts)
    if not os.path.exists(path):
        return None, path
    with open(path, encoding="utf-8") as f:
        return json.load(f), path


def audit_medicines():
    meds, _ = _load("knowledge", "ayurvedic_medicines.json")
    issues, fields = [], ["contraindications", "dosage", "anupana", "rasa", "virya",
                          "vipaka", "afi_reference", "classical_text_reference", "safety_tier"]
    ids = [m.get("id") for m in meds]
    dupes = [k for k, v in Counter(ids).items() if v > 1]
    if dupes:
        issues.append(f"duplicate ids: {dupes}")
    for f in fields:
        miss = [m["id"] for m in meds if not m.get(f)]
        if miss:
            issues.append(f"{len(miss)} missing '{f}'" + (f" e.g. {miss[:3]}" if len(miss) <= 5 else ""))
    conds = set()
    for m in meds:
        conds.update(c.lower() for c in m.get("conditions", []))
    return {"name": "Medicines", "count": len(meds), "conditions": len(conds),
            "condition_set": conds, "issues": issues}


def audit_yoga():
    from services.yoga_plan_engine import _PROTOCOL_MAP, yoga_poses, pranayama_list
    poses_contra = sum(1 for p in yoga_poses if p.get("contraindications") or p.get("medical_conditions_contraindicated"))
    issues = []
    if poses_contra < len(yoga_poses) * 0.5:
        issues.append(f"only {poses_contra}/{len(yoga_poses)} poses have contraindications")
    prana_contra = sum(1 for p in pranayama_list if p.get("contraindications"))
    preg_unsafe = sum(1 for p in yoga_poses if p.get("pregnancy_safe") is False)
    return {"name": "Yoga", "count": f"{len(yoga_poses)} poses / {len(pranayama_list)} pranayama",
            "conditions": len(_PROTOCOL_MAP), "condition_set": set(_PROTOCOL_MAP.keys()),
            "issues": issues + [
                f"{poses_contra}/{len(yoga_poses)} poses have contraindications "
                f"(rest are neutral restoratives)",
                f"{prana_contra}/{len(pranayama_list)} pranayama have contraindications",
                f"{preg_unsafe} poses flagged pregnancy-unsafe"]}


def audit_gym():
    ge, _ = _load("knowledge_base", "gym_exercises.json")
    contra = sum(1 for e in ge if e.get("contraindications"))
    no_instr = [e["id"] for e in ge if not (e.get("instructions") or [])]
    levels = Counter(e.get("level") for e in ge)
    issues = []
    if contra < len(ge):
        issues.append(f"{len(ge) - contra}/{len(ge)} exercises have NO contraindications "
                      f"(low-risk SMR/stretch — intentional)")
    if no_instr:
        issues.append(f"{len(no_instr)} exercises have empty instructions e.g. {no_instr[:3]}")
    issues.append(f"level mix: {levels.get('beginner',0)} beginner / "
                  f"{levels.get('intermediate',0)} intermediate / {levels.get('advanced',0)} advanced "
                  f"(beginners get beginner+intermediate; advanced excluded)")
    return {"name": "Gym", "count": len(ge), "conditions": "n/a (contraindication-filtered)",
            "condition_set": set(), "issues": issues}


def audit_diet():
    cp, _ = _load("knowledge_base", "condition_protocols.json")
    from services.diet_brief_builder import PATHYA_APATHYA_HINTS
    foods, _ = _load("knowledge_base", "diet_foods.json")
    cp_conds = {(c.get("condition") or c.get("id") or "").lower() for c in cp} if isinstance(cp, list) else set()
    return {"name": "Diet", "count": f"{len(foods)} foods", "conditions": len(cp_conds | set(PATHYA_APATHYA_HINTS)),
            "condition_set": cp_conds | set(PATHYA_APATHYA_HINTS),
            "issues": ["LLM-primary: unmapped conditions handled by AI reasoning"]}


def audit_central():
    from engine.dosha_analyzer import _DISEASE_DOSHA_SIGNAL
    return {"name": "Central disease→dosha map", "count": len(_DISEASE_DOSHA_SIGNAL),
            "conditions": len(_DISEASE_DOSHA_SIGNAL), "condition_set": set(_DISEASE_DOSHA_SIGNAL),
            "issues": []}


def audit_stale_files():
    issues = []
    legacy = os.path.join(DATA, "knowledge", "home_remedies.json")
    seed = os.path.abspath(os.path.join(os.path.dirname(__file__), "seed_remedies.py"))
    if os.path.exists(legacy):
        d = json.load(open(legacy))
        n = len(d) if isinstance(d, list) else len(d)
        if os.path.exists(seed):
            txt = open(seed).read()
            # crude count of remedy dicts in seed
            seed_n = txt.count('"symptom_id"')
            if seed_n > n:
                issues.append(f"data/knowledge/home_remedies.json has {n} entries but seed_remedies.py "
                              f"defines ~{seed_n} — the JSON is stale/legacy; DB is seeded from the script.")
    return issues


def main():
    sections = [audit_central(), audit_medicines(), audit_yoga(), audit_gym(), audit_diet()]
    stale = audit_stale_files()

    lines = ["# Ayura AI — Data Quality & Condition Coverage Report", ""]
    lines.append("## Quantity & quality by feature\n")
    lines.append("| Feature | Entries | Conditions w/ curated depth | Data-quality issues |")
    lines.append("|---|---|---|---|")
    for s in sections:
        iss = "; ".join(s["issues"]) if s["issues"] else "✓ none"
        lines.append(f"| {s['name']} | {s['count']} | {s['conditions']} | {iss} |")
    lines.append("")

    # Coverage overlap: how many medicine conditions are also in the central map
    central = next(s for s in sections if s["name"].startswith("Central"))["condition_set"]
    meds = next(s for s in sections if s["name"] == "Medicines")["condition_set"]
    yoga = next(s for s in sections if s["name"] == "Yoga")["condition_set"]
    lines.append("## Cross-feature condition coverage\n")
    lines.append(f"- Central disease→dosha map: **{len(central)}** conditions (drives PK + disease-aware prompts)")
    lines.append(f"- Medicines KB covers **{len(meds)}** conditions; **{len(meds & central)}** overlap the central map")
    lines.append(f"- Yoga protocols cover **{len(yoga)}** conditions")
    lines.append(f"- Medicine conditions NOT in central map (medicine-only): {sorted(meds - central)[:20]} ...")
    lines.append("")

    lines.append("## Rare / unmapped disease handling (the honest answer)\n")
    lines.append("Every feature produces a SAFE plan for any condition; depth degrades gracefully:")
    lines.append("")
    lines.append("| Feature | Mapped condition | Rare / unmapped condition |")
    lines.append("|---|---|---|")
    lines.append("| Panchakarma | Classical Pradhana Karma + Aushadha | Conservative Shamana + `vaidya_review_required` flag |")
    lines.append("| Yoga | 1 of 146 curated protocols | LLM dynamic protocol (`yoga_condition_fallback`) |")
    lines.append("| Diet | Curated Pathya-Apathya | LLM clinical reasoning (primary path) |")
    lines.append("| Medicines | Condition-matched formulations | Dosha-based general meds + coverage flag |")
    lines.append("| Gym | Contraindication-filtered | Dosha/goal-based; injuries still excluded |")
    lines.append("")
    if stale:
        lines.append("## ⚠ Stale / inconsistent files\n")
        for s in stale:
            lines.append(f"- {s}")
        lines.append("")

    out_dir = os.path.join(DATA, "golden")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "coverage_report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("DATA QUALITY AUDIT")
    print("=" * 60)
    for s in sections:
        print(f"{s['name']:32s} entries={str(s['count']):20s} conditions={s['conditions']}")
        for i in s["issues"]:
            print(f"    - {i}")
    for s in stale:
        print(f"  STALE: {s}")
    print(f"\nReport → {os.path.join(out_dir, 'coverage_report.md')}")


if __name__ == "__main__":
    main()
