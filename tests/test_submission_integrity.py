#!/usr/bin/env python3
"""Test immutable submission and provenance integrity helpers."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "experiments"
sys.path.insert(0, str(EXPERIMENTS))
SPEC = importlib.util.spec_from_file_location("check_submission", EXPERIMENTS / "check_submission.py")
assert SPEC and SPEC.loader
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def expect_failure(action, message: str) -> None:
    try:
        action()
    except AssertionError:
        return
    raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        payload = tmp_path / "payload.txt"
        manifest = tmp_path / "SHA256SUMS.txt"
        payload.write_text("frozen\n", encoding="utf-8")
        digest = hashlib.sha256(payload.read_bytes()).hexdigest()
        manifest.write_text(f"{digest}  payload.txt\n", encoding="utf-8")
        CHECK.verify_sha256_manifest(tmp_path, manifest)
        payload.write_text("tampered\n", encoding="utf-8")
        expect_failure(
            lambda: CHECK.verify_sha256_manifest(tmp_path, manifest),
            "tampered SHA256 target was accepted",
        )

        audit_path = tmp_path / "audit.csv"
        row = {field: "" for field in CHECK.EXPECTED_AUDIT_FIELDS}
        row.update(
            {
                "r": "1",
                "u": "0x00000001",
                "v": "0x00000002",
                "way2_executed": "1",
                "way2_value_source": "estimator",
                "submitted_vt_field_source": "submit.txt",
                "exact_executed": "0",
                "exact_command": "",
                "exact_result_available": "0",
            }
        )
        with audit_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=CHECK.EXPECTED_AUDIT_FIELDS, lineterminator="\n")
            writer.writeheader()
            writer.writerow(row)

        original_count = CHECK.EXPECTED_VALID_COUNT
        CHECK.EXPECTED_VALID_COUNT = 1
        try:
            CHECK.verify_audit_provenance(audit_path, [(1, 1, 2)])
            row["exact_executed"] = "1"
            row["exact_command"] = "./exact_oracle"
            row["exact_result_available"] = "1"
            with audit_path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=CHECK.EXPECTED_AUDIT_FIELDS, lineterminator="\n")
                writer.writeheader()
                writer.writerow(row)
            expect_failure(
                lambda: CHECK.verify_audit_provenance(audit_path, [(1, 1, 2)]),
                "invented exact provenance was accepted",
            )
        finally:
            CHECK.EXPECTED_VALID_COUNT = original_count

    print("submission integrity tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
