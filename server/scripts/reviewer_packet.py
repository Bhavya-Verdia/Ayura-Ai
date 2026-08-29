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
  data/golden/vaidya_contraindication_tokens.csv — 1 row per contraindication token
       in the medicines / home-remedy KBs with what a non-clinician decided it means,
       because making these fire at all required interpreting them.
  data/golden/vaidya_panchakarma_karma_tags.csv — 1 row per Purvakarma/Paschat therapy
       with the Pradhana Karma courses it was tagged to AND the ones it was excluded
       from, since the exclusion is the half that changes a plan.
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

    # "This disease contraindicates nothing" is a clinical claim like any other, and
    # the one most likely to be wrong by omission — it is what 23 diseases in the
    # central map were implicitly asserting before anyone had assessed them. The
    # reviewer sees the assertion and the reason for it, in the same sheet.
    for condition, reason in sorted(clinical.get("assessed_no_contraindication", {}).items()):
        if condition == "_note":
            continue
        rows.append({
            "scope": "assessed_no_contraindication", "procedure": "(all five Karma)",
            "severity": "none", "condition": condition, "stated_mechanism": reason,
            "severity_ok": "", "mechanism_ok": "", "should_be": "", "vaidya_notes": "",
        })

    path = os.path.join(OUT, "vaidya_panchakarma_contraindications.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return path, len(rows)


def build_contraindication_token_csv():
    """One row per contraindication token in the medicines / home-remedy KBs, with
    what it was decided to mean.

    The KBs' contraindication lists were written as prose and fed to a gate that
    compared them to `medical_history` as strings, so 140 of the 164 distinct tokens
    could never match anything. Making them fire meant *deciding* what each one
    means — that `autoimmune_disease` covers type 1 diabetes, that `uncontrolled_
    diabetes` has to bar every diabetic because the app cannot know how controlled
    anyone is, that `pitta_excess` reads an assessed Vikriti and not a constitution.

    Each of those is a clinical judgement made by a non-clinician, and each is the
    difference between a formulation being withheld and being prescribed. They are
    listed here for the same row-by-row confirmation the Panchakarma sheet gets.
    """
    from engine.contraindication_tokens import (
        CAUTION_TOKENS, CONDITION_TOKENS, DERIVED_TOKENS, RED_FLAG_TOKENS, classify,
    )

    kb = os.path.join(DATA, "knowledge_base")
    users: dict[str, list[str]] = {}

    def walk(node, name=None):
        if isinstance(node, dict):
            label = node.get("name") or node.get("symptom_display") or node.get("symptom_id") or name
            for key, value in node.items():
                if key == "contraindications" and isinstance(value, list):
                    for tok in value:
                        users.setdefault(str(tok).lower(), []).append(str(label))
                else:
                    walk(value, label)
        elif isinstance(node, list):
            for item in node:
                walk(item, name)

    for fname in ("ayurvedic_medicines.json", "home_remedies.json"):
        walk(json.load(open(os.path.join(kb, fname), encoding="utf-8")))

    cols = ["token", "kind", "interpreted_as", "entries_affected", "example_entries",
            "interpretation_ok", "should_be", "vaidya_notes"]
    rows = []
    for token in sorted(users):
        kind = classify(token)
        if kind == "condition":
            meaning = "bars: " + ", ".join(CONDITION_TOKENS[token])
        elif kind == "derived":
            meaning = "derived state: " + DERIVED_TOKENS[token][1]
        elif kind == "caution":
            meaning = "shown to the user: " + CAUTION_TOKENS[token]
        elif kind == "red_flag":
            meaning = "shown to the user: " + RED_FLAG_TOKENS[token]
        else:
            meaning = "matched directly — the app records this condition under this name"
        entries = sorted(set(users[token]))
        rows.append({
            "token": token, "kind": kind, "interpreted_as": meaning,
            "entries_affected": len(entries), "example_entries": "; ".join(entries[:4]),
            "interpretation_ok": "", "should_be": "", "vaidya_notes": "",
        })

    path = os.path.join(OUT, "vaidya_contraindication_tokens.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    return path, len(rows)


KARMA_VOCAB = ("vamana", "virechana", "basti", "basti_matra", "nasya", "raktamokshana")


def build_karma_tag_csv():
    """One row per Purvakarma/Paschat therapy and the Karma courses it belongs to.

    Every row in `panchakarma_therapies.json` carries a `karma` list naming the
    Pradhana Karma courses it is part of, and the engine scores the therapy pool with
    it — a Nasya plan now leads its preparation with Shirodhara and a Basti plan no
    longer opens on Snehapana. The nine `pradhana` rows are excluded here: their karma
    is an identity (the Vamana row performs Vamana) and carries no `karma_reviewed`
    flag, because there is nothing in it for a reviewer to accept or reject.

    The 14 rows that remain each assert a classical indication, `karma_reviewed` is
    false on all of them, and they were authored by a non-clinician from the classical
    references quoted in `karma_basis`.

    `karma_excluded` is a column rather than an omission because the exclusions are
    what actually move a plan. Snehapana tagged to Vamana and Virechana is unremarkable;
    Snehapana *withheld* from the Basti and Nasya courses is the claim — that Basti's
    Purvakarma is Abhyanga plus Swedana and its internal sneha arrives as Anuvasana.
    A reviewer who only saw the inclusions would be reading half of each decision.
    """
    therapies = json.load(open(os.path.join(DATA, "knowledge_base", "panchakarma_therapies.json"), encoding="utf-8"))
    cols = ["therapy_id", "therapy_name", "phase", "karma_claimed", "karma_excluded",
            "stated_basis", "claim_ok (Y/N)", "should_be", "vaidya_notes"]
    rows = []
    for t in therapies:
        if t.get("phase") == "pradhana":
            continue
        claimed = list(t.get("karma") or ())
        rows.append({
            "therapy_id": t.get("id", ""),
            "therapy_name": t.get("name", ""),
            "phase": t.get("phase", ""),
            "karma_claimed": _fmt_list(claimed),
            "karma_excluded": _fmt_list([k for k in KARMA_VOCAB if k not in claimed]),
            "stated_basis": t.get("karma_basis", ""),
            "claim_ok (Y/N)": "", "should_be": "", "vaidya_notes": "",
        })

    path = os.path.join(OUT, "vaidya_panchakarma_karma_tags.csv")
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


def build_packet_md(n_meds, n_pk=0, n_tokens=0, n_karma=0):
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
        "## Part 3 — Contraindication tokens  (`vaidya_contraindication_tokens.csv`)",
        f"{n_tokens} tokens appear in the medicines and home-remedy contraindication "
        "lists. They were written as notes for a human and then used as a machine gate, "
        "which matched them against the patient's history as plain strings — so most of "
        "them never fired. Making them work required deciding what each one means: which "
        "recorded diagnoses `autoimmune_disease` covers, whether `uncontrolled_diabetes` "
        "must bar every diabetic when the app cannot know how controlled anyone is, "
        "whether `pitta_excess` may be read off a constitution when no Vikriti assessment "
        "exists. **Those decisions were made by a non-clinician**, and each one moves a "
        "formulation between prescribed and withheld. Tick `interpretation_ok`, or write "
        "what it should be.",
        "",
        "## Part 4 — Panchakarma Karma tags  (`vaidya_panchakarma_karma_tags.csv`)",
        f"{n_karma} preparation and aftercare therapies, each tagged with the Pradhana "
        "Karma courses it belongs to. The engine scores its therapy pool with this tag, so "
        "it decides what a patient is actually prepared with: a Nasya plan now leads with "
        "Shirodhara (Murdha Taila) rather than internal ghee, and a Basti plan no longer "
        "opens on Snehapana. Measured across 9,720 Shodhana plans, 10.4% changed schedule.",
        "",
        "The nine Pradhana rows are not here — that the Vamana row performs Vamana is an "
        "identity, not a claim. These 14 are claims, authored by a non-clinician from the "
        "references quoted in `stated_basis`, and `karma_reviewed` is false on all of them.",
        "",
        "**Read `karma_excluded` as carefully as `karma_claimed`.** The exclusions are what "
        "move a plan. Snehapana tagged to Vamana and Virechana is unremarkable; Snehapana "
        "*withheld* from the Basti and Nasya courses is the actual assertion — that Basti's "
        "Purvakarma is Abhyanga plus Swedana and its internal sneha arrives as Anuvasana, and "
        "that neither Nasya nor Raktamokshana takes internal oleation. Likewise Samsarjana "
        "Krama is withheld from Nasya and Raktamokshana on the grounds that neither empties a "
        "Koshtha. If any of those exclusions is wrong, a patient is being prepared for the "
        "wrong procedure.",
        "",
        "- **claim_ok** — is the set of courses right, inclusions and exclusions together?",
        "- **should_be** — the corrected list, if not.",
        "",
        "## Part 5 — Diet food library  (separate packet)",
        "The 150-food library is large enough to need its own document and its own "
        "ordering, so it ships as **`vaidya_diet_packet.md`** with six CSVs beside it. "
        "It holds 708 clinical claims — this food is Pathya in that condition, that "
        "food is Apathya in this one — across 20 conditions, and `reviewed` is false "
        "on every one of the 150 rows.",
        "",
        "Start with `vaidya_diet_screened_claims.csv` (12 rows). Those are the claims "
        "that disagree with the food carrying them, and most of them are the same "
        "question: a modern indication entered into a classical field. Olive oil is "
        "Pathya in high cholesterol while being guru, snigdha and Kapha-raising. "
        "Answering that once settles a whole condition at a time.",
        "",
        "## Part 6 — Clinical case sign-off",
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
        "## Part 7 — Sign-off",
        "",
        "- Reviewer (name, BAMS/MD reg. no.): ____________________",
        "- Date: ____________  ",
        "- Overall: medicines reviewed ___/%d · PK contraindications reviewed ___/%d · "
        "contraindication tokens reviewed ___/%d · Karma tags reviewed ___/%d · "
        "cases reviewed ___/%d"
        % (n_meds, n_pk, n_tokens, n_karma, len(cases)),
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
    tok_path, n_tok = build_contraindication_token_csv()
    karma_path, n_karma = build_karma_tag_csv()
    md_path = build_packet_md(n, n_pk, n_tok, n_karma)
    print("Vaidya reviewer packet generated:")
    print(f"  {csv_path}  ({n} medicines)")
    print(f"  {pk_path}  ({n_pk} panchakarma contraindications)")
    print(f"  {tok_path}  ({n_tok} contraindication tokens)")
    print(f"  {karma_path}  ({n_karma} Karma tags)")
    print(f"  {md_path}")
    print("\nGive these to a BAMS Vaidya, along with the diet packet built separately by")
    print("scripts/build_diet_review_packet.py. Filled CSV corrections fold straight back")
    print("into the KB — for diet, into scripts/diet_library/, which the KB is built from.")


if __name__ == "__main__":
    main()
