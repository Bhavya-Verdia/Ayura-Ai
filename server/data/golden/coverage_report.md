# Ayura AI — Data Quality & Condition Coverage Report

## Quantity & quality by feature

| Feature | Entries | Conditions w/ curated depth | Data-quality issues |
|---|---|---|---|
| Central disease→dosha map | 101 | 101 | ✓ none |
| Medicines | 157 | 185 | ✓ none |
| Yoga | 124 poses / 20 pranayama | 146 | 119/124 poses have contraindications (rest are neutral restoratives); 12/20 pranayama have contraindications; 63 poses flagged pregnancy-unsafe |
| Gym | 893 | n/a (contraindication-filtered) | 3/893 exercises have NO contraindications (low-risk SMR/stretch — intentional); level mix: 46 beginner / 774 intermediate / 73 advanced (beginners get beginner+intermediate; advanced excluded) |
| Diet | 150 foods | 39 | LLM-primary: unmapped conditions handled by AI reasoning |

## Cross-feature condition coverage

- Central disease→dosha map: **101** conditions (drives PK + disease-aware prompts)
- Medicines KB covers **185** conditions; **30** overlap the central map
- Yoga protocols cover **146** conditions
- Medicine conditions NOT in central map (medicine-only): ['abdominal_pain', 'acne', 'aging', 'allergic_skin', 'ama_accumulation', 'angina', 'anorexia', 'arrhythmia', 'ascites', 'back_pain', 'benign_prostatic_hyperplasia', 'bleeding_disorders', 'blemishes', 'bloating', 'blood_purification', 'bronchitis', 'burning_sensation', 'calcium_deficiency', 'cardiac_disorders', 'cardiac_weakness'] ...

## Rare / unmapped disease handling (the honest answer)

Every feature produces a SAFE plan for any condition; depth degrades gracefully:

| Feature | Mapped condition | Rare / unmapped condition |
|---|---|---|
| Panchakarma | Classical Pradhana Karma + Aushadha | Conservative Shamana + `vaidya_review_required` flag |
| Yoga | 1 of 146 curated protocols | LLM dynamic protocol (`yoga_condition_fallback`) |
| Diet | Curated Pathya-Apathya | LLM clinical reasoning (primary path) |
| Medicines | Condition-matched formulations | Dosha-based general meds + coverage flag |
| Gym | Contraindication-filtered | Dosha/goal-based; injuries still excluded |
