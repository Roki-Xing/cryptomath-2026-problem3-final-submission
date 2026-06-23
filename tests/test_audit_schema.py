#!/usr/bin/env python3
"""Test way-2 audit provenance schema and way-1 separation."""

from __future__ import annotations

import csv
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments/audit_submit.py"
SPOTCHECK = ROOT / "experiments/spotcheck/exact_spotcheck.csv"

EXPECTED_PROVENANCE_FIELDS = [
    "way2_executed",
    "way2_value_source",
    "submitted_vt_field_source",
    "exact_executed",
    "exact_command",
    "exact_result_available",
]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        submit_path = tmp_path / "submit.txt"
        audit_path = tmp_path / "way2_audit.csv"
        estimator_path = tmp_path / "fake_estimator.py"

        submit_path.write_text("@(1, 0x00000001, 0x00000002, 0.5, 0.5)\n", encoding="utf-8")
        estimator_path.write_text(
            """#!/usr/bin/env python3
print("0x00000002 VE=0.5 proxy_score=1")
print("round=1 input_beam=1 raw_next_terms=1 aggregated_masks=1 output_beam=1 "
      "branch_truncated_states=0 tuple_truncated_states=0 beam_pruned=no")
print("final_beam_size=1")
print("expanded_states=1")
print("generated_transitions=1")
print("certified_no_truncation=yes")
""",
            encoding="utf-8",
        )
        estimator_path.chmod(estimator_path.stat().st_mode | stat.S_IXUSR)

        subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--submit",
                str(submit_path),
                "--out",
                str(audit_path),
                "--estimator-bin",
                str(estimator_path),
            ],
            cwd=ROOT,
            check=True,
        )

        with audit_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            row = next(reader)
            assert next(reader, None) is None
            fields = reader.fieldnames or []

        for field in EXPECTED_PROVENANCE_FIELDS:
            assert field in fields
        assert "vt_source" not in fields
        assert row["way2_executed"] == "1"
        assert row["way2_value_source"] == "estimator"
        assert row["submitted_vt_field_source"] == str(submit_path)
        assert row["exact_executed"] == "0"
        assert row["exact_command"] == ""
        assert row["exact_result_available"] == "0"
        assert "exact_oracle" not in ",".join(row.values())

        with SPOTCHECK.open(encoding="utf-8", newline="") as handle:
            spotcheck_fields = next(csv.reader(handle))
        assert fields != spotcheck_fields
        assert not set(EXPECTED_PROVENANCE_FIELDS).intersection(spotcheck_fields)

    print("audit schema tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
