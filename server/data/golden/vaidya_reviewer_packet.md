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
445 authored contraindications gating Vamana, Virechana, Basti, Nasya, Raktamokshana, the 23 supporting therapies, and the individual herbs in every Aushadha the plan prescribes. **None has been clinically reviewed** — `contraindications_reviewed` is false on the whole file. Part 1 carries the larger credibility risk; this part carries the larger safety risk, because these are the only procedures in the app that can injure a patient directly.

Each row states the *mechanism* by which the condition and the procedure conflict, so you can reject a single claim without discarding the file. Columns to fill:
- **severity_ok** — is `hard` (withhold + substitute) vs `soft` (proceed modified) right?
- **mechanism_ok** — is the stated reason correct?
- **should_be** — `hard`, `soft` or `remove` if the severity is wrong.

Rows with scope `herb` are per-constituent: a `hard` row withholds that herb from whichever formulation contains it and leaves the rest, so severity here decides between dropping one ingredient and dropping a whole preparation.

Missing entries matter as much as wrong ones: if a condition should bar a procedure and is not listed, add a row.

### Open questions where the authored rule and the classics disagree
These were deliberately **not** settled by the author. Each needs a ruling.

1. **Anaemia (Pandu) bars every Shodhana.** The engine treats `anemia` as an absolute bar and gives Shamana only. Charaka Chikitsa 16 prescribes the opposite for Pandu: oleate with ghee, then purify by both routes. The bar was kept because the app cannot know the haemoglobin, and severe anaemia is a modern contraindication to any depleting procedure. Should mild anaemia restrict to Mridu Virechana instead of barring?
2. **A barred Snehapana bars the Karma it prepares.** Gallstones and acute pancreatitis bar Snehapana (a 60–120 ml fat load provokes biliary colic), so they now withdraw Vamana and Virechana and substitute Basti or Nasya. Is a Ruksha or short (Sadyo) Snehana the better answer than substitution?
3. **Snehapana peak by Agni.** Manda Agni is held to 60 ml and Vishama to 90 ml (after Charaka Sutrasthana 13's Matra grading); Sama and Tikshna take the ladder in the KB. Are these caps right?
4. **Pratimarsha Nasya is the default substitute.** Low Ojas, age over 70 and the Vamana age bar all substitute to Nasya, and a Kapha patient at home is given Nasya. Across 3,000 sampled profiles it is the Karma of 43% of plans. Is it the right default, or should a Pitta substitution go to Matra Basti?
5. **Allergies are flagged, never substituted.** A dairy-allergic patient is told the ghee and milk-processed oils need a Vaidya's preparation; the engine does not choose a Taila Snehapana for them. Should it?

## Part 3 — Contraindication tokens  (`vaidya_contraindication_tokens.csv`)
164 tokens appear in the medicines and home-remedy contraindication lists. They were written as notes for a human and then used as a machine gate, which matched them against the patient's history as plain strings — so most of them never fired. Making them work required deciding what each one means: which recorded diagnoses `autoimmune_disease` covers, whether `uncontrolled_diabetes` must bar every diabetic when the app cannot know how controlled anyone is, whether `pitta_excess` may be read off a constitution when no Vikriti assessment exists. **Those decisions were made by a non-clinician**, and each one moves a formulation between prescribed and withheld. Tick `interpretation_ok`, or write what it should be.

## Part 3b — Condition → formulary map  (`vaidya_condition_formulary_map.csv`)
37 onboarding conditions whose route to the formulary was authored rather than matched by name. Thirty of seventy conditions onboarding offers used to reach no formulation at all, so an osteoarthritis patient was given Triphala and a cough powder. Fifteen are now bridged to the formulary terms whose formulations are indicated (osteoarthritis → arthritis, joint_pain). The rest are **left uncovered on purpose** — Type 1 diabetes, hyperthyroidism, atrial fibrillation, lupus and others — so the plan tells the patient a Vaidya must prescribe rather than serving a near match. Tick `mapping_ok`, or say what it should reach.

## Part 3c — Herb x medicine and formulation rules  (`vaidya_herb_drug_interactions.csv`)
27 rules the medicines and home-remedy plans withhold (`major`) or caution (`moderate`) by. Before them, interactions were matched by category word, so a patient on lithium was given Punarnava, one on digoxin Yashtimadhu, one on tacrolimus a Trikatu compound, and one on metronidazole an Arishta. The formulation rules withhold mercury, copper, lead and arsenic preparations from self-service altogether, alcohol-based Arishtas under 18 and in liver disease, and sugar-based Avalehas in diabetes. **Contested:** Kumaryasava and Arogyavardhini are classical liver medicines and are withheld in liver disease here — rule on them. Arogyavardhini is listed in the formulary without its classical Parada and Tamra; the composition itself needs checking.

## Part 3d — Formulary data corrections  (`vaidya_medicine_data_corrections.csv`)
All 157 formulations were read against classical composition by a non-clinician, and every change is recorded here with its previous value. Corrected: composition (Pathyadi Kadha, Navaka Guggulu, Rajapravartini Vati — listed with opium — and Sukumar Kashayam), indications that contradicted the herb table (Avipattikar, Vidangadi and Hingwashtak for IBD; Shilajit for kidney disease; Saraswatarishta for epilepsy), thyroid contraindications that pointed the wrong way (Brahmi), missing bars (Loha Bhasma in haemochromatosis), a male-only Parkinson's herb (Kapikachu), and five alcohol-based Asavas marked pregnancy-safe. **Three self-served formulations contain Visha dravya — Kanakasava (datura), Agnitundi Vati (classically mercury, aconite and nux vomica, missing from its list) and Dhanwanthari Gulika (aconite) — and are now prescribed in person only.** Rows with field `(entry)` are questions, not changes. Fourteen formulations carry `pregnancy_safe: "consult"` — the engine read that as safe; it now withholds them in pregnancy until you rule. **53 compound formulations cite the Ayurvedic Pharmacopoeia (API), which covers single drugs; their references should point to the AFI** — page numbers were not verified. Approve or reverse each row.

## Part 4 — Panchakarma Karma tags  (`vaidya_panchakarma_karma_tags.csv`)
14 preparation and aftercare therapies, each tagged with the Pradhana Karma courses it belongs to. The engine scores its therapy pool with this tag, so it decides what a patient is actually prepared with: a Nasya plan now leads with Shirodhara (Murdha Taila) rather than internal ghee, and a Basti plan no longer opens on Snehapana. Measured across 9,720 Shodhana plans, 10.4% changed schedule.

The nine Pradhana rows are not here — that the Vamana row performs Vamana is an identity, not a claim. These 14 are claims, authored by a non-clinician from the references quoted in `stated_basis`, and `karma_reviewed` is false on all of them.

**Read `karma_excluded` as carefully as `karma_claimed`.** The exclusions are what move a plan. Snehapana tagged to Vamana and Virechana is unremarkable; Snehapana *withheld* from the Basti and Nasya courses is the actual assertion — that Basti's Purvakarma is Abhyanga plus Swedana and its internal sneha arrives as Anuvasana, and that neither Nasya nor Raktamokshana takes internal oleation. Likewise Samsarjana Krama is withheld from Nasya and Raktamokshana on the grounds that neither empties a Koshtha. If any of those exclusions is wrong, a patient is being prepared for the wrong procedure.

- **claim_ok** — is the set of courses right, inclusions and exclusions together?
- **should_be** — the corrected list, if not.

## Part 5 — Diet food library  (separate packet)
The 150-food library is large enough to need its own document and its own ordering, so it ships as **`vaidya_diet_packet.md`** with six CSVs beside it. It holds 708 clinical claims — this food is Pathya in that condition, that food is Apathya in this one — across 20 conditions, and `reviewed` is false on every one of the 150 rows.

Start with `vaidya_diet_screened_claims.csv` (12 rows). Those are the claims that disagree with the food carrying them, and most of them are the same question: a modern indication entered into a classical field. Olive oil is Pathya in high cholesterol while being guru, snigdha and Kapha-raising. Answering that once settles a whole condition at a time.

## Part 5b — Authored 2026-10-19 from the live sweep (unreviewed)
Three changes made by a non-clinician to remove contradictions the app was showing patients. Each is a judgement a Vaidya should confirm or overturn.

- **Acid reflux yoga protocol** (`acid_reflux_protocol` in `condition_protocols.json`). GERD, heartburn and acidity used to share the IBS / Grahani protocol, which practised after a meal with abdominal compression first. The new protocol cites Madhava Nidana 51 and Kashyapa Khila 16. It is upright and cooling, and it **hard-excludes** inversions, head-below-heart folds (including Downward Dog, which also withholds Surya Namaskar), belly-compressing poses, Bhastrika, Kapalabhati, Agnisara and Kumbhaka. *Is the avoid list right, and is withholding Surya Namaskar from every reflux patient too strict?*
- **Agni Samana in place of Agni Deepana** (`diet_plan_arc._pitta_safe`). For Tikshna Agni, or any Amlapitta / ulcer patient, the "warming spices" kindling week becomes regulation: sweet, bitter and astringent, with coriander, fennel and cumin. Pachana for Ama uses Tikta herbs, not ginger, pepper or hing. *Is Tikta Pachana the right substitute when Ama and Amlapitta coexist?*
- **Medicine dose without its vehicle** (`remedy_engine._dose_without_vehicle`). The catalogue dose named a vehicle on 141 of 157 rows. It is now removed, so the selected Anupana is the only one stated. A child's dose used to carry its own vehicle (often honey), different from the adult Anupana the engine selects. A child now sees the adult Anupana. *Should paediatric Anupana be selected separately?*

Still not changed: hypothyroid stays in `_SANTARPANA_JANYA` (Langhana arc). Its withheld note now says this is a modern extrapolation rather than citing Prameha, Medoroga and Kushtha. Whether it belongs on that arc at all is the open question.

## Part 6 — Clinical case sign-off
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

## Part 7 — Prakriti instrument validation  (a study to commission, not a checklist)
Prakriti is the root input to every engine in this app. Diet, yoga, gym, routine and Panchakarma all branch on it, so an instrument that leans one way propagates that lean into every plan and shows up in none of them.

What is already machine-verified: the quiz collects 21 constitutional traits plus one consistency probe, the scorer weights every one of them (0.7-2.0, differentiated by how diagnostic each trait is held to be), and `test_dosha_instrument.py` fails if the two ever drift apart. Results carry `dosha_scoring_version` (currently 2) so a cohort can be tied to the scorer that produced it. A self-report ceiling caps the dominant dosha at 55% because people answer questionnaires about themselves more decisively than their constitution warrants.

What none of that establishes is whether the result is **correct**. That is not a gap a dataset can close, and we checked: the public Prakriti datasets label their records with their own rule-based scoring rather than a practitioner's assessment. The largest of them says so plainly — its scoring "may differ from clinical evaluations made by expert practitioners using methods such as pulse diagnosis" and "represents a questionnaire-based view of Prakriti rather than a complete clinical assessment". Comparing our scorer against theirs would compare two rule engines over two different questionnaires, and neither agreement nor disagreement would mean anything.

So it needs a Vaidya. The protocol we are asking for:

1. **Participants.** 40 is a useful minimum and 100 is comfortable. Spread across age and build deliberately — the constitutions that go wrong are the ones at the edges, and a cohort of healthy young adults will hide exactly those. Include dual-dosha and Vata-dominant elderly participants on purpose.
2. **Blind assessment.** The practitioner assesses Prakriti by traditional means — Darshana, Sparshana, Prashna, Nadi Pareeksha as they normally would — **without seeing the app's output or the participant's answers**. If the app's answer is visible first, the study measures agreement with a suggestion rather than agreement with an assessment, and it cannot be re-run.
3. **Record both.** Practitioner verdict (dominant dosha, and secondary where Dvidoshaja), app verdict, the app's confidence, and `dosha_scoring_version`.
4. **Report three things, not one.** Agreement on the dominant dosha; agreement on the full constitution including the secondary; and **which traits the disagreements cluster on**. The third is the only one that tells us what to change: if the misses concentrate on, say, `nadi_rhythm` or `mutra_pattern`, those are traits a patient cannot self-report reliably and the weight or the wording is wrong.

A disagreement rate is not a failure. An unmeasured instrument is.

| | |
|---|---|
| Participants assessed | ____ |
| Dominant dosha agreement | ____ / ____ |
| Full constitution agreement (incl. secondary) | ____ / ____ |
| Traits the disagreements concentrated on | ____________________ |
| Scoring version under test | ____ |

## Part 8 — Sign-off

- Reviewer (name, BAMS/MD reg. no.): ____________________
- Date: ____________  
- Overall: medicines reviewed ___/157 · PK contraindications reviewed ___/445 · contraindication tokens reviewed ___/164 · Karma tags reviewed ___/14 · cases reviewed ___/30
- Summary judgement (1–5) on classical accuracy of: Medicines __ · Panchakarma __ · Diet __ · Yoga __ · Routine __
- Prakriti instrument study (Part 7): commissioned ☐ · scheduled ☐ · completed ☐ — participants ____

> Return the filled CSV + this page; corrections are folded back into the knowledge base.
