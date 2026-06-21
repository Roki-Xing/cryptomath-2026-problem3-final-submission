# Ablation Summary

These runs use `candidate_miner_approx` only. They measure way-2 search behavior, not exact VT validation.

| config | mode | beam | trans | max_active | rows | certified | generated_transitions | best `(r,u,v)` | best VE | proxy score |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| aggregate_beam100_trans100_active1 | aggregate | 100 | 100 | 1 | 32 | 0 | 19936 | `(2,0x00000002,0x07008008)` | -0.25 | 2 |
| aggregate_beam1000_trans1000_active1 | aggregate | 1000 | 1000 | 1 | 32 | 32 | 19936 | `(2,0x00000002,0x07008008)` | -0.25 | 2 |
| routes_beam1000_trans1000_active1 | routes | 1000 | 1000 | 1 | 32 | 32 | 19936 | `(2,0x00000001,0x0400e00e)` | 0.125 | 1 |
| aggregate_beam1000_trans1000_active2 | aggregate | 1000 | 1000 | 2 | 61 | 45 | 118076 | `(2,0x00002000,0x08880000)` | 1 | 4 |

Reproduce:

```bash
python3 experiments/run_ablation.py
```
