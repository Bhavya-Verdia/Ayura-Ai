"""
Vaidya reviewer packet generator.

Produces the artifacts a BAMS-qualified Vaidya needs to validate Ayura AI's
classical content quickly (target: ~2 days):

  data/golden/vaidya_medicine_review.csv   — 1 row per medicine, all verifiable
       fields + empty columns to tick (reference_ok / dosage_ok / indication_ok /
       safety_ok / vaidya_notes). Open in Excel/Sheets, sort, tick through.
  data/golden/vaidya_panchakarma_contraindications.csv — 1 row per authored
       Panchakarma contraindication with its stated mechanism, so a reviewer can
       confirm or reject one claim at a time. The whole file is unreviewed.
  data/golden/vaidya_reviewer_packet.md    — instructions, summary stats, and the
       golden-case clinical sign-off section.

This is the instrument that turns "AI-generated, looks credible" into
"validated against N BAMS practitioners" — the only path to a true 10/10 on the
classical axis. Run:  cd server && ./venv/bin/python scripts/reviewer_packet.py
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

DATA = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
OUT = os.path.join(DATA, "golden")
os.makedirs(OUT, exist_ok=True)


def _fmt_list(v):
    if isinstance(v, list):
        return "; ".join(str(x) for x in v)
    return str(v or "")


def build_panchakarma_contraindication_csv():
    """One row per authored Panchakarma contraindication, with its stated mechanism.

    `panchakarma_clinical.json` is authored, not reviewed — `contraindications_reviewed`
    is false on every entry. It gates the most invasive procedures in the app (emesis,
    purgation, enema, bloodletting), so it needs the same row-by-row sign-off the
    medicine KB gets. Each row carries the mechanism precisely so a reviewer can
    reject one claim without discarding the file.
    """
    clinical = json.load(open(os.path.join(DATA, "knowledge_base", "panchakarma_clinical.json"), encoding="utf-8"))
    cols = ["scope", "procedure", "severity", "condition", "stated_mechanism",
            "severity_ok", "mechanism_ok", "should_be", "vaidya_notes"]
    rows = []

    def emit(scope, name, entry):
        for severity in ("hard", "soft"):
            for condition, mechanism in sorted((entry.get(severity) or {}).items()):
                rows.append({
                    "scope": scope, "procedure": name, "severity": severity,
                    "condition": condition, "stated_mechanism": mechanism,
                    "severity_ok": "", "mechanism_ok": "", "should_be": "", "vaidya_notes": "",
                })

    for karma, entry in clinical.get("pradhana_karma", {}).items():
        emit("pradhana_karma", karma, entry)
    for tid, entry in clinical.get("therapies", {}).items():
        if isinstance(entry, dict):
            emit("therapy", tid, entry)
    # Per-herb safety for the Sahayoga Dravya adjuvants and the Rasayana. These gate
    # the same patients as the procedure rows above and must not reach the reviewer
    # by a different route — or, as they did until now, by none at all.
    for herb, entry in clinical.get("herbs", {}).items():
        if isinstance(entry, dict):
            emit("herb", entry.get("display", herb), entry)

    path = os.path.join(OUT, "vaidya_panchakarma_contraindications.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return path, len(rows)


def build_medicine_csv():
    meds = json.load(open(os.path.join(DATA, "knowledge_base", "ayurvedic_medicines.json"), encoding="utf-8"))
    meds = sorted(meds, key=lambda m: m.get("name", ""))
    cols = [
        "id", "name", "type", "indications", "rasa", "guna", "virya", "vipaka",
        "karma", "dosage", "dosage_pediatric", "anupana", "contraindications",
        "drug_interactions", "pregnancy_safe", "afi_reference", "classical_text_reference",
        # ── reviewer columns (leave blank for the Vaidya) ──
        "reference_ok (Y/N)", "dosage_ok (Y/N)", "indication_ok (Y/N)",
        "safety_ok (Y/N)", "vaidya_corrections",
    ]
    path = os.path.join(OUT, "vaidya_medicine_review.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for m in meds:
            w.writerow([
                m.get("id", ""), m.get("name", ""), m.get("type", ""),
                _fmt_list(m.get("conditions")), _fmt_list(m.get("rasa")),
                _fmt_list(m.get("guna")), m.get("virya", ""), m.get("vipaka", ""),
                _fmt_list(m.get("karma")), m.get("dosage", ""), m.get("dosage_pediatric", ""),
                _fmt_list(m.get("anupana")), _fmt_list(m.get("contraindications")),
                _fmt_list(m.get("drug_interactions")), m.get("pregnancy_safe", ""),
                m.get("afi_reference", ""), m.get("classical_text_reference", ""),
                "", "", "", "", "",
            ])
    return path, len(meds)


def build_packet_md(n_meds, n_pk=0):
    golden_path = os.path.join(OUT, "golden_cases.json")
    cases = json.load(open(golden_path, encoding="utf-8")) if os.path.exists(golden_path) else []

    lines = [
        "# Ayura AI — Vaidya Validation Packet",
        "",
        "_For a BAMS-qualified Ayurvedic practitioner. Estimated effort: ~2 days._",
        "",
        "## Why this exists",
        "Ayura AI's engine logic and data hygiene are independently tested. What only you "
        "can certify is **classical accuracy**: that the references are real, the dosages "
        "are correct, the formulations fit their indications, and the safety flags are right. "
        "Your sign-off is what lets the team say *“validated against N BAMS practitioners.”*",
        "",
        "## Part 1 — Medicines (highest priority)",
        f"Open **`vaidya_medicine_review.csv`** ({n_meds} formulations). For each row, tick:",
        "",
        "- **reference_ok** — is the AFI / classical-text reference real and correct for THIS formulation? (This is the #1 credibility risk — a single fabricated reference discredits the whole KB.)",
        "- **dosage_ok** — is the dose + Anupana clinically correct?",
        "- **indication_ok** — do the listed conditions match the classical use?",
        "- **safety_ok** — are contraindications, pregnancy flag, and drug interactions correct?",
        "- **vaidya_corrections** — free text for any fix.",
        "",
        "Sort by `type` or `indications` to review related formulations together. Anything "
        "marked N with a correction is gold — it goes straight back into the KB.",
        "",
        "## Part 2 — Panchakarma contraindications  (`vaidya_panchakarma_contraindications.csv`)",
        f"{n_pk} authored contraindications gating Vamana, Virechana, Basti, Nasya, Raktamokshana, "
        "the 23 supporting therapies, and the individual herbs in every Aushadha the plan "
        "prescribes. **None has been clinically reviewed** — "
        "`contraindications_reviewed` is false on the whole file. Part 1 carries the larger "
        "credibility risk; this part carries the larger safety risk, because these are the "
        "only procedures in the app that can injure a patient directly.",
        "",
        "Each row states the *mechanism* by which the condition and the procedure conflict, so you "
        "can reject a single claim without discarding the file. Columns to fill:",
        "- **severity_ok** — is `hard` (withhold + substitute) vs `soft` (proceed modified) right?",
        "- **mechanism_ok** — is the stated reason correct?",
        "- **should_be** — `hard`, `soft` or `remove` if the severity is wrong.",
        "",
        "Rows with scope `herb` are per-constituent: a `hard` row withholds that herb from "
        "whichever formulation contains it and leaves the rest, so severity here decides "
        "between dropping one ingredient and dropping a whole preparation.",
        "",
        "Missing entries matter as much as wrong ones: if a condition should bar a procedure and "
        "is not listed, add a row.",
        "",
        "## Part 3 — Clinical case sign-off",
        f"Below are {len(cases)} synthetic patient cases run through the engines (deterministic, "
        "no AI). For each, confirm the core decisions are what you would prescribe, or note the "
        "correction. Full per-case detail with a grading grid is in **`golden_review.md`**.",
        "",
        "| # | Case | Pradhana Karma | Shodhana/Shamana | Agni | Prescribe as-is? (Y/N) | Correction |",
        "|---|---|---|---|---|---|---|",
    ]
    for i, c in enumerate(cases, 1):
        pk = c.get("panchakarma", {})
        lines.append(
            f"| {i} | {c.get('label','')} | {pk.get('pradhana_karma','')} | "
            f"{pk.get('shodhana_or_shamana','')} | {pk.get('agni_name','')} |  |  |"
        )
    lines += [
        "",
        "## Part 4 — Sign-off",
        "",
        "- Reviewer (name, BAMS/MD reg. no.): ____________________",
        "- Date: ____________  ",
        "- Overall: medicines reviewed ___/%d · PK contraindications reviewed ___/%d · cases reviewed ___/%d"
        % (n_meds, n_pk, len(cases)),
        "- Summary judgement (1–5) on classical accuracy of: "
        "Medicines __ · Panchakarma __ · Diet __ · Yoga __ · Routine __",
        "",
        "> Return the filled CSV + this page; corrections are folded back into the knowledge base.",
        "",
    ]
    path = os.path.join(OUT, "vaidya_reviewer_packet.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main():
    csv_path, n = build_medicine_csv()
    pk_path, n_pk = build_panchakarma_contraindication_csv()
    md_path = build_packet_md(n, n_pk)
    print("Vaidya reviewer packet generated:")
    print(f"  {csv_path}  ({n} medicines)")
    print(f"  {pk_path}  ({n_pk} panchakarma contraindications)")
    print(f"  {md_path}")
    print("\nGive all three to a BAMS Vaidya. Filled CSV corrections fold straight back into the KB.")


if __name__ == "__main__":
    main()
