# Exact Way-2 Pilot Protocol

- schema: `exact-way2-pilot-selection-v2`
- selector source commit: `6261edd252d9cf21f2522e7045877e45665a7448`
- selector command: `python3 -X utf8 experiments/exact_way2/select_pilot.py --final-ru experiments/frozen/final_ru.csv --final-queries experiments/frozen/final_queries.csv --complexity-input <ARTIFACT_ROOT>/COMPLEXITY_INPUT.csv --spotcheck-coordinates <ARTIFACT_ROOT>/SPOTCHECK_COORDINATES.csv --out <ARTIFACT_ROOT>`
- final_ru input: `experiments/frozen/final_ru.csv`
- final_queries input: `experiments/frozen/final_queries.csv`
- complexity-only input: `COMPLEXITY_INPUT.csv`
- spotcheck-coordinates input: `SPOTCHECK_COORDINATES.csv`
- final_ru_sha256: `941879db58f4ad63b3fcc45b27a04713215f8c7920c77ad8a76015795ec78246`
- final_queries_sha256: `44cef0f572d0201aed2e2d42e21deb6a5b8259743bf0a29b0665a332fbfdd93e`
- complexity_input_sha256: `05359f7702df6f4b01ceff69bdd86baefa751eb741e3be1c5ff44b80b33ba310`
- spotcheck_coordinates_sha256: `54b9a81d397f9b8023eee0569c48e2f68e160c71845339574075530df1761ca4`
- selection_payload_sha256: `73b89eb62070546f87c8e9fa05b377d4de73468338d273abc40b1020cdab79ce`
- forbidden during selection/compute: frozen VE values, submit VT/VE, score, way-1 numerators, candidate ranking/source
- pilot size: `344` unique `(r,u)` columns
- target distribution: `r1=120`, `r2=128`, `r3=96`
- r2 mandatory anchors: `min`, `upper-median`, `nearest-rank P95`, `max`, and all unique `r=2` spotcheck inputs
- active-count × complexity-band allocation uses largest remainder with one guaranteed slot per non-empty stratum
