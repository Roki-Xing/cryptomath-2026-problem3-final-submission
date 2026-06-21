# Submit Audit Summary

- submit: `submit.txt`
- audit: `experiments/submit_audit.csv`

## Row Counts

- submit_rows: 138338
- audit_rows: 138338

## Validity / Safety Checks

- valid_rows: 138338
- certified_no_truncation_rows: 138338
- certified_no_truncation_rows_valid: 138338
- ve_mismatch_rows: 0
- ve_mismatch_rows_valid: 0
- unique_uv: 138338
- duplicate_uv_rows: 0
- zero_u_rows: 0
- zero_v_rows: 0
- zero_vt_rows: 0
- zero_ve_rows: 0

## Complexity Certificate (Unique `(r,u)`)

- unique_ru: 4760
- max_generated_transitions_per_unique_ru: 7578152
- max_generated_transitions_ratio_to_2_32: 0.00176443
- max_expanded_states_per_unique_ru: 1001
- max_final_beam_size_per_unique_ru: 46453
- ru_generated_transitions_ge_2_32: 0
- ru_expanded_states_ge_2_32: 0

## Complexity Distribution (Unique `(r,u)`)

- generated_transitions_median_per_ru: 68420
- generated_transitions_p95_per_ru: 2648720
- expanded_states_median_per_ru: 101
- expanded_states_p95_per_ru: 401

## Worst `(r,u)` (by generated_transitions)

```json
[
  {
    "expanded_states": 1001,
    "final_beam_size": 13360,
    "generated_transitions": 7578152,
    "r": 2,
    "u": "0x800a7000"
  },
  {
    "expanded_states": 1001,
    "final_beam_size": 13360,
    "generated_transitions": 7094504,
    "r": 2,
    "u": "0xf000700a"
  },
  {
    "expanded_states": 1001,
    "final_beam_size": 13360,
    "generated_transitions": 7094504,
    "r": 2,
    "u": "0xf00a7000"
  },
  {
    "expanded_states": 1001,
    "final_beam_size": 10800,
    "generated_transitions": 6883304,
    "r": 2,
    "u": "0x80075000"
  },
  {
    "expanded_states": 1001,
    "final_beam_size": 9840,
    "generated_transitions": 6883304,
    "r": 2,
    "u": "0x80097000"
  },
  {
    "expanded_states": 1001,
    "final_beam_size": 10400,
    "generated_transitions": 6883304,
    "r": 2,
    "u": "0x800b5000"
  },
  {
    "expanded_states": 1001,
    "final_beam_size": 9520,
    "generated_transitions": 6883304,
    "r": 2,
    "u": "0x800c7000"
  },
  {
    "expanded_states": 1001,
    "final_beam_size": 13520,
    "generated_transitions": 6883304,
    "r": 2,
    "u": "0x800d5000"
  },
  {
    "expanded_states": 1001,
    "final_beam_size": 9600,
    "generated_transitions": 6883304,
    "r": 2,
    "u": "0x800e5000"
  },
  {
    "expanded_states": 1001,
    "final_beam_size": 19272,
    "generated_transitions": 6487304,
    "r": 2,
    "u": "0xf0007a00"
  }
]
```
