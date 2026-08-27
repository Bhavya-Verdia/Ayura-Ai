# Ayura AI — Vaidya Validation Packet

_For a BAMS-qualified Ayurvedic practitioner. Estimated effort: ~2 days._

## Why this exists
Ayura AI's engine logic and data hygiene are independently tested. What only you can certify is **classical accuracy**: that the references are real, the dosages are correct, the formulations fit their indications, and the safety flags are right. Your sign-off is what lets the team say *“validated against N BAMS practitioners.”*

## Part 1 — Medicines (highest priority)
Open **`vaidya_medicine_review.csv`** (157 formulations). For each row, tick:

- **reference_ok** — is the AFI / classical-text reference real and correct for THIS formulation? (This is the #1 credibility risk — a single fabricated reference discredits the whole KB.)
- **dosage_ok** — is the dose + Anupana clinically correct?
- **indication_ok** — do the listed conditions match the classical use?
- **safety_ok** — are contraindications, pregnancy flag, and drug interactions correct?
- **vaidya_corrections** — free text for any fix.

Sort by `type` or `indications` to review related formulations together. Anything marked N with a correction is gold — it goes straight back into the KB.

## Part 2 — Panchakarma contraindications  (`vaidya_panchakarma_contraindications.csv`)
299 authored contraindications gating Vamana, Virechana, Basti, Nasya, Raktamokshana, the 23 supporting therapies, and the individual herbs in every Aushadha the plan prescribes. **None has been clinically reviewed** — `contraindications_reviewed` is false on the whole file. Part 1 carries the larger credibility risk; this part carries the larger safety risk, because these are the only procedures in the app that can injure a patient directly.

Each row states the *mechanism* by which the condition and the procedure conflict, so you can reject a single claim without discarding the file. Columns to fill:
- **severity_ok** — is `hard` (withhold + substitute) vs `soft` (proceed modified) right?
- **mechanism_ok** — is the stated reason correct?
- **should_be** — `hard`, `soft` or `remove` if the severity is wrong.

Rows with scope `herb` are per-constituent: a `hard` row withholds that herb from whichever formulation contains it and leaves the rest, so severity here decides between dropping one ingredient and dropping a whole preparation.

Missing entries matter as much as wrong ones: if a condition should bar a procedure and is not listed, add a row.

## Part 3 — Contraindication tokens  (`vaidya_contraindication_tokens.csv`)
164 tokens appear in the medicines and home-remedy contraindication lists. They were written as notes for a human and then used as a machine gate, which matched them against the patient's history as plain strings — so most of them never fired. Making them work required deciding what each one means: which recorded diagnoses `autoimmune_disease` covers, whether `uncontrolled_diabetes` must bar every diabetic when the app cannot know how controlled anyone is, whether `pitta_excess` may be read off a constitution when no Vikriti assessment exists. **Those decisions were made by a non-clinician**, and each one moves a formulation between prescribed and withheld. Tick `interpretation_ok`, or write what it should be.

## Part 4 — Panchakarma Karma tags  (`vaidya_panchakarma_karma_tags.csv`)
14 preparation and aftercare therapies, each tagged with the Pradhana Karma courses it belongs to. The engine scores its therapy pool with this tag, so it decides what a patient is actually prepared with: a Nasya plan now leads with Shirodhara (Murdha Taila) rather than internal ghee, and a Basti plan no longer opens on Snehapana. Measured across 9,720 Shodhana plans, 10.4% changed schedule.

The nine Pradhana rows are not here — that the Vamana row performs Vamana is an identity, not a claim. These 14 are claims, authored by a non-clinician from the references quoted in `stated_basis`, and `karma_reviewed` is false on all of them.

**Read `karma_excluded` as carefully as `karma_claimed`.** The exclusions are what move a plan. Snehapana tagged to Vamana and Virechana is unremarkable; Snehapana *withheld* from the Basti and Nasya courses is the actual assertion — that Basti's Purvakarma is Abhyanga plus Swedana and its internal sneha arrives as Anuvasana, and that neither Nasya nor Raktamokshana takes internal oleation. Likewise Samsarjana Krama is withheld from Nasya and Raktamokshana on the grounds that neither empties a Koshtha. If any of those exclusions is wrong, a patient is being prepared for the wrong procedure.

- **claim_ok** — is the set of courses right, inclusions and exclusions together?
- **should_be** — the corrected list, if not.

## Part 5 — Clinical case sign-off
Below are 30 synthetic patient cases run through the engines (deterministic, no AI). For each, confirm the core decisions are what you would prescribe, or note the correction. Full per-case detail with a grading grid is in **`golden_review.md`**.

| # | Case | Pradhana Karma | Shodhana/Shamana | Agni | Prescribe as-is? (Y/N) | Correction |
|---|---|---|---|---|---|---|
| 1 | Vata constitution, anxiety + insomnia, young adult | basti_matra | shamana | Vishama Agni |  |  |
| 2 | Pitta constitution, acid reflux + migraine, adult | virechana | shamana | Tikshna Agni |  |  |
| 3 | Kapha constitution, obesity + hypothyroid, midlife | nasya | shamana | Manda Agni |  |  |
| 4 | Vata-Pitta dual, hypertension, senior | virechana | shamana | Sama Agni |  |  |
| 5 | Kapha-Pitta dual, type-2 diabetes + fatty liver | virechana | shamana | Manda Agni |  |  |
| 6 | Pregnant Pitta woman (safety gating) | virechana | shamana | Sama Agni |  |  |
| 7 | Vata, ankylosing spondylitis (Asthi-Majja Vata) | basti_matra | shamana | Vishama Agni |  |  |
| 8 | Pitta with hypotension + cardiac history (medicine gating) | virechana | shamana | Sama Agni |  |  |
| 9 | Kapha, bronchial asthma (Tamaka Shwasa) | nasya | shamana | Manda Agni |  |  |
| 10 | Vata child (Balya Avastha), constipation | basti_matra | shamana | Vishama Agni |  |  |
| 11 | Pitta, psoriasis (Kushtha — Rakta-Pitta) | virechana | shamana | Tikshna Agni |  |  |
| 12 | Vata, sciatica (Gridhrasi) | basti_matra | shamana | Vishama Agni |  |  |
| 13 | Vata-Kapha, fibromyalgia | basti_matra | shamana | Manda Agni |  |  |
| 14 | Vata, osteoarthritis, senior (Sandhivata) | basti_matra | shamana | Vishama Agni |  |  |
| 15 | Pitta, essential hypertension | virechana | shamana | Tikshna Agni |  |  |
| 16 | Kapha, PCOS (Artava Dushti) | nasya | shamana | Manda Agni |  |  |
| 17 | Vata, IBS (Grahani) | basti_matra | shamana | Vishama Agni |  |  |
| 18 | Kapha, chronic sinusitis (Pratishyaya) | nasya | shamana | Manda Agni |  |  |
| 19 | Vata, Parkinson's (Kampavata), senior | basti_matra | shamana | Vishama Agni |  |  |
| 20 | Kapha, depression (Kaphaja Unmada / Vishada) | nasya | shamana | Manda Agni |  |  |
| 21 | Pitta, gout (Vatarakta) | virechana | shamana | Tikshna Agni |  |  |
| 22 | Vata, epilepsy (Apasmara) — pranayama safety | basti_matra | shamana | Vishama Agni |  |  |
| 23 | Pitta, glaucoma — pranayama safety (no inversions/forceful) | virechana | shamana | Tikshna Agni |  |  |
| 24 | Kapha, NAFLD fatty liver (Yakrit Vikara) | nasya | shamana | Manda Agni |  |  |
| 25 | Pregnant Vata woman (safety gating) | basti_matra | shamana | Vishama Agni |  |  |
| 26 | Vata-Pitta, anxiety + acidity, young professional | virechana | shamana | Vishama Agni |  |  |
| 27 | Kapha, high cholesterol (Medo Dushti) | nasya | shamana | Manda Agni |  |  |
| 28 | Pitta, hyperthyroidism (Atyagni / Bhasmaka) | virechana | shamana | Tikshna Agni |  |  |
| 29 | Vata, healthy active baseline (no conditions) | basti_matra | shamana | Sama Agni |  |  |
| 30 | Senior, multiple conditions (HTN + diabetes + arthritis) | basti_matra | shamana | Vishama Agni |  |  |

## Part 6 — Sign-off

- Reviewer (name, BAMS/MD reg. no.): ____________________
- Date: ____________  
- Overall: medicines reviewed ___/157 · PK contraindications reviewed ___/299 · contraindication tokens reviewed ___/164 · Karma tags reviewed ___/14 · cases reviewed ___/30
- Summary judgement (1–5) on classical accuracy of: Medicines __ · Panchakarma __ · Diet __ · Yoga __ · Routine __

> Return the filled CSV + this page; corrections are folded back into the knowledge base.
