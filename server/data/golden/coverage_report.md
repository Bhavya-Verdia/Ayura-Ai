# Ayura AI — Data Quality & Condition Coverage Report

## Quantity & quality by feature

| Feature | Entries | Conditions w/ curated depth | Data-quality issues |
|---|---|---|---|
| Central disease→dosha map | 101 | 101 | ✓ none |
| Medicines | 82 | 146 | ✓ none |
| Yoga | 124 poses / 20 pranayama | 146 | 8/20 pranayama have contraindications |
| Gym | 893 | n/a (contraindication-filtered) | 18/893 exercises have NO contraindications listed |
| Diet | 150 foods | 39 | LLM-primary: unmapped conditions handled by AI reasoning |

## Cross-feature condition coverage

- Central disease→dosha map: **101** conditions (drives PK + disease-aware prompts)
- Medicines KB covers **146** conditions; **25** overlap the central map
- Yoga protocols cover **146** conditions
- Medicine conditions NOT in central map (medicine-only): ['abdominal_pain', 'acne', 'aging', 'allergic_skin', 'ama_accumulation', 'angina', 'anorexia', 'arrhythmia', 'back_pain', 'bleeding_disorders', 'blemishes', 'bloating', 'blood_purification', 'bronchitis', 'burning_sensation', 'calcium_deficiency', 'cardiac_weakness', 'childhood_cough', 'chronic_cough', 'chronic_diarrhea'] ...

## Rare / unmapped disease handling (the honest answer)

Every feature produces a SAFE plan for any condition; depth degrades gracefully:

| Feature | Mapped condition | Rare / unmapped condition |
|---|---|---|
| Panchakarma | Classical Pradhana Karma + Aushadha | Conservative Shamana + `vaidya_review_required` flag |
| Yoga | 1 of 146 curated protocols | LLM dynamic protocol (`yoga_condition_fallback`) |
| Diet | Curated Pathya-Apathya | LLM clinical reasoning (primary path) |
| Medicines | Condition-matched formulations | Dosha-based general meds + coverage flag |
| Gym | Contraindication-filtered | Dosha/goal-based; injuries still excluded |
