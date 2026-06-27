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

## Part 2 — Clinical case sign-off
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

## Part 3 — Sign-off

- Reviewer (name, BAMS/MD reg. no.): ____________________
- Date: ____________  
- Overall: medicines reviewed ___/157 · cases reviewed ___/30
- Summary judgement (1–5) on classical accuracy of: Medicines __ · Panchakarma __ · Diet __ · Yoga __ · Routine __

> Return the filled CSV + this page; corrections are folded back into the knowledge base.
