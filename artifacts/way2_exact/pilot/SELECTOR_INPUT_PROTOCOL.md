# Exact Way-2 Selector Input Preparation

- schema: `exact-way2-pilot-selection-v2`
- source commit: `6261edd252d9cf21f2522e7045877e45665a7448`
- command: `python3 -X utf8 experiments/exact_way2/prepare_selector_inputs.py --final-ru experiments/frozen/final_ru.csv --audit experiments/submit_audit.csv --spotcheck-queries experiments/spotcheck/exact_spotcheck_queries.csv --out <ARTIFACT_ROOT>`
- final_ru input: `experiments/frozen/final_ru.csv`
- audit source: `experiments/submit_audit.csv`
- spotcheck query source: `experiments/spotcheck/exact_spotcheck_queries.csv`
- allowed fields in complexity input: `r,u,generated_transitions,expanded_states`
- allowed fields in spotcheck coordinates: `r,u,v`
- forbidden during selector preparation: `VE,VT,score,way-1 numerator,candidate rank/source`
