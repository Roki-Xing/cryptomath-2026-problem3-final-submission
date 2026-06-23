#!/usr/bin/env python3
"""Freeze deterministic query and value-snapshot artifacts from submit.txt."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


EXPECTED_SUBMIT_SHA256 = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
EXPECTED_QUERY_COUNT = 138338
EXPECTED_UNIQUE_RU = 4760
FROZEN_TOTAL_SCORE = "105843.622442471292742994"
FROZEN_MAX_GENERATED_TRANSITIONS_PER_RU = 7578152
FROZEN_CERTIFIED_ROWS = 138338
FROZEN_WAY2_MISMATCH = 0
FROZEN_WAY1_SPOTCHECK_COUNT = 18
FROZEN_WAY1_SPOTCHECK_MISMATCH = 0

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
SUBMIT_RE = re.compile(
    r"^@\(\s*(?P<r>\d+)\s*,\s*(?P<u>0x[0-9a-fA-F]+|\d+)\s*,\s*"
    r"(?P<v>0x[0-9a-fA-F]+|\d+)\s*,\s*(?P<vt>[^,]+?)\s*,\s*(?P<ve>[^)]+?)\s*\)$"
)


@dataclass(frozen=True)
class Query:
    r: int
    u: int
    v: int
    submitted_vt_field_snapshot: str
    frozen_way2_ve: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submit", default="submit.txt", help="Submission file used as the only source.")
    parser.add_argument("--submit-path-label", default="submit.txt", help="Stable repository-relative source label.")
    parser.add_argument("--out-dir", default="experiments/frozen", help="Directory for frozen artifacts.")
    parser.add_argument("--repository", required=True, help="Repository owner/name recorded in provenance.")
    parser.add_argument("--source-commit", required=True, help="40-hex commit containing the source submit file.")
    parser.add_argument("--freeze-tool-commit", required=True, help="40-hex commit containing this freeze tool.")
    parser.add_argument("--generated-at", required=True, help="Fixed UTC timestamp in YYYY-MM-DDTHH:MM:SSZ form.")
    parser.add_argument("--expected-submit-sha256", default=EXPECTED_SUBMIT_SHA256)
    parser.add_argument("--expected-query-count", type=int, default=EXPECTED_QUERY_COUNT)
    parser.add_argument("--expected-unique-ru", type=int, default=EXPECTED_UNIQUE_RU)
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    """Compute a file SHA-256 digest."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_blob_sha1(path: Path) -> str:
    """Compute the Git blob SHA-1 without reading repository metadata."""
    data = path.read_bytes()
    header = f"blob {len(data)}\0".encode()
    return hashlib.sha1(header + data).hexdigest()


def load_queries(path: Path) -> list[Query]:
    """Parse, validate, and deterministically order submit rows."""
    queries: list[Query] = []
    seen_ruv: set[tuple[int, int, int]] = set()
    seen_uv: set[tuple[int, int]] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = SUBMIT_RE.match(stripped)
        if not match:
            raise ValueError(f"bad submit line {line_number}: {stripped}")
        query = Query(
            r=int(match.group("r")),
            u=int(match.group("u"), 0),
            v=int(match.group("v"), 0),
            submitted_vt_field_snapshot=match.group("vt").strip(),
            frozen_way2_ve=match.group("ve").strip(),
        )
        if query.u == 0 or query.v == 0:
            raise ValueError(f"zero mask at submit line {line_number}")
        ruv = (query.r, query.u, query.v)
        uv = (query.u, query.v)
        if ruv in seen_ruv:
            raise ValueError(f"duplicate (r,u,v) at submit line {line_number}")
        if uv in seen_uv:
            raise ValueError(f"duplicate (u,v) at submit line {line_number}")
        seen_ruv.add(ruv)
        seen_uv.add(uv)
        queries.append(query)
    return sorted(queries, key=lambda query: (query.r, query.u, query.v))


def write_csv(path: Path, header: list[str], rows: list[tuple[object, ...]]) -> None:
    """Write a deterministic UTF-8 CSV with LF line endings."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def write_json(path: Path, payload: object) -> None:
    """Write stable, human-readable JSON."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_provenance_args(args: argparse.Namespace) -> None:
    """Reject ambiguous or non-deterministic provenance metadata."""
    if not args.repository.strip():
        raise SystemExit("--repository must not be empty")
    for name in ("source_commit", "freeze_tool_commit"):
        value = getattr(args, name)
        if not COMMIT_RE.fullmatch(value):
            raise SystemExit(f"--{name.replace('_', '-')} must be a lowercase 40-hex commit")
    if not UTC_RE.fullmatch(args.generated_at):
        raise SystemExit("--generated-at must use fixed UTC form YYYY-MM-DDTHH:MM:SSZ")


def main() -> int:
    """Generate and validate frozen baseline artifacts."""
    args = parse_args()
    validate_provenance_args(args)
    submit_path = Path(args.submit)
    out_dir = Path(args.out_dir)
    submit_resolved = submit_path.resolve()
    out_resolved = out_dir.resolve()
    if submit_resolved == out_resolved:
        raise SystemExit("--out-dir must not be the submit file")
    if out_dir.exists() and not out_dir.is_dir():
        raise SystemExit("--out-dir must be a directory")

    output_names = {
        "BASELINE.json",
        "SHA256SUMS.txt",
        "final_queries.csv",
        "final_ru.csv",
        "final_values_snapshot.csv",
    }
    if submit_path.name in output_names and submit_resolved.parent == out_resolved:
        raise SystemExit("submit path conflicts with a frozen output path")

    submit_bytes_before = submit_path.read_bytes()
    submit_sha256 = hashlib.sha256(submit_bytes_before).hexdigest()
    if submit_sha256 != args.expected_submit_sha256:
        raise SystemExit(
            f"submit SHA-256 mismatch: expected {args.expected_submit_sha256}, got {submit_sha256}"
        )

    queries = load_queries(submit_path)
    unique_ru = sorted({(query.r, query.u) for query in queries})
    if len(queries) != args.expected_query_count:
        raise SystemExit(f"query count mismatch: expected {args.expected_query_count}, got {len(queries)}")
    if len(unique_ru) != args.expected_unique_ru:
        raise SystemExit(f"unique (r,u) mismatch: expected {args.expected_unique_ru}, got {len(unique_ru)}")

    out_dir.mkdir(parents=True, exist_ok=True)
    queries_path = out_dir / "final_queries.csv"
    ru_path = out_dir / "final_ru.csv"
    values_path = out_dir / "final_values_snapshot.csv"
    baseline_path = out_dir / "BASELINE.json"
    checksums_path = out_dir / "SHA256SUMS.txt"

    write_csv(
        queries_path,
        ["r", "u", "v"],
        [(query.r, f"0x{query.u:08x}", f"0x{query.v:08x}") for query in queries],
    )
    write_csv(ru_path, ["r", "u"], [(r, f"0x{u:08x}") for r, u in unique_ru])
    write_csv(
        values_path,
        [
            "row_id",
            "r",
            "u",
            "v",
            "submitted_vt_field_snapshot",
            "frozen_way2_ve",
            "future_way1_vt",
            "future_way1_numerator",
            "future_way1_status",
        ],
        [
            (
                f"FQ{index:06d}",
                query.r,
                f"0x{query.u:08x}",
                f"0x{query.v:08x}",
                query.submitted_vt_field_snapshot,
                query.frozen_way2_ve,
                "",
                "",
                "NOT_EXECUTED",
            )
            for index, query in enumerate(queries, start=1)
        ],
    )

    artifact_specs = {
        "final_queries.csv": (["r", "u", "v"], len(queries), queries_path),
        "final_ru.csv": (["r", "u"], len(unique_ru), ru_path),
        "final_values_snapshot.csv": (
            [
                "row_id",
                "r",
                "u",
                "v",
                "submitted_vt_field_snapshot",
                "frozen_way2_ve",
                "future_way1_vt",
                "future_way1_numerator",
                "future_way1_status",
            ],
            len(queries),
            values_path,
        ),
    }
    baseline = {
        "schema_version": 2,
        "source": {
            "repository": args.repository,
            "submit_path": args.submit_path_label,
            "submit_sha256": submit_sha256,
            "submit_blob_sha": git_blob_sha1(submit_path),
            "submit_source_commit": args.source_commit,
        },
        "frozen_numbers": {
            "certified_rows": FROZEN_CERTIFIED_ROWS,
            "frozen_self_score_valid_count": args.expected_query_count,
            "max_generated_transitions_per_ru": FROZEN_MAX_GENERATED_TRANSITIONS_PER_RU,
            "total_score": FROZEN_TOTAL_SCORE,
            "unique_ru": args.expected_unique_ru,
            "way1_full_domain_spotcheck_count": FROZEN_WAY1_SPOTCHECK_COUNT,
            "way1_full_domain_spotcheck_mismatch": FROZEN_WAY1_SPOTCHECK_MISMATCH,
            "way2_mismatch": FROZEN_WAY2_MISMATCH,
        },
        "artifacts": {
            name: {
                "columns": columns,
                "data_rows": data_rows,
                "sha256": file_sha256(path),
            }
            for name, (columns, data_rows, path) in artifact_specs.items()
        },
        "generation": {
            "freeze_tool_commit": args.freeze_tool_commit,
            "generated_at_utc": args.generated_at,
            "command": (
                "python3 -X utf8 experiments/freeze_baseline.py --submit submit.txt "
                "--submit-path-label submit.txt --out-dir experiments/frozen "
                f"--repository {args.repository} --source-commit {args.source_commit} "
                f"--freeze-tool-commit {args.freeze_tool_commit} --generated-at {args.generated_at}"
            ),
            "ordering": (
                "numeric ascending by (r,u,v); final_ru deduplicated then numeric ascending by (r,u); "
                "row_id assigned after query sorting"
            ),
        },
    }
    write_json(baseline_path, baseline)

    checksum_paths = [baseline_path, queries_path, ru_path, values_path]
    checksum_lines = [f"{file_sha256(path)}  {path.name}" for path in sorted(checksum_paths)]
    checksums_path.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    if submit_path.read_bytes() != submit_bytes_before:
        raise SystemExit("submit file changed during freeze")

    print(f"submit_sha256={submit_sha256}")
    print(f"final_queries_rows={len(queries)}")
    print(f"final_ru_rows={len(unique_ru)}")
    print(f"final_values_snapshot_rows={len(queries)}")
    print(f"frozen_dir={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
