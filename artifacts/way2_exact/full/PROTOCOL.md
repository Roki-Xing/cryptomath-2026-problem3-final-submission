# Exact Way-2 Full Selection Protocol

- schema: `exact-way2-full-selection-v1`
- selector source commit: `0b3531edba16738dfb2afa85ac69ba9d7fa7c136`
- selector command: `python3 -X utf8 experiments/exact_way2/select_full.py --final-ru experiments/frozen/final_ru.csv --final-queries experiments/frozen/final_queries.csv --out <ARTIFACT_ROOT>`
- final_ru input: `experiments/frozen/final_ru.csv`
- final_queries input: `experiments/frozen/final_queries.csv`
- final_ru_sha256: `941879db58f4ad63b3fcc45b27a04713215f8c7920c77ad8a76015795ec78246`
- final_queries_sha256: `44cef0f572d0201aed2e2d42e21deb6a5b8259743bf0a29b0665a332fbfdd93e`
- selection_payload_sha256: `a4f3b8ec66a6757b0392c965b0a70c2fb6bba97dcb7ff05d1367ea0325631f5a`
- full_selection_row_count: `4760`
- unique_ru_count: `4760`
- round_distribution_by_r: `{'1': 120, '2': 4544, '3': 96}`
- selection scope: `all 4760 unique (r,u) columns from final_ru.csv`
- compute phase inputs remain limited to `row_id,r,u,v` from the frozen query file
