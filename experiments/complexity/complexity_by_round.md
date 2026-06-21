# Complexity By Round

- source: `experiments/submit_audit.csv`
- grouping: unique `(r,u)`, then by `r`
- per-`(r,u)` rule: keep the max `generated_transitions`, `expanded_states`, and `final_beam_size` among rows sharing the same `(r,u)`.

| r | unique `(r,u)` | generated transitions total | max generated transitions per `(r,u)` | expanded states total | max expanded states per `(r,u)` | max final beam size per `(r,u)` |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 120 | 1056 | 10 | 120 | 1 | 10 |
| 2 | 4544 | 1650086776 | 7578152 | 725368 | 1001 | 25360 |
| 3 | 96 | 34708992 | 1140946 | 11106 | 199 | 46453 |
| total | 4760 | 1684796824 | 7578152 | 736594 | 1001 | 46453 |

This file supports the paper table that reports the by-round way-2 route-space expansion scale.
