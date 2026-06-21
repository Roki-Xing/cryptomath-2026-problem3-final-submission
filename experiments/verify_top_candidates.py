#!/usr/bin/env python3
"""Verify top proxy candidates and write a score-checked submit file.

Args:
    See --help for CLI options.

Returns:
    Exit code 0 when the output submit file passes the score checker.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SUBMIT_RE = re.compile(
    r"^@\(\s*(?P<r>\d+)\s*,\s*(?P<u>0x[0-9a-fA-F]+|\d+)\s*,\s*"
    r"(?P<v>0x[0-9a-fA-F]+|\d+)\s*,\s*(?P<vt>[^,]+)\s*,\s*(?P<ve>[^)]+)\s*\)$"
)


@dataclass(frozen=True)
class Candidate:
    r: int
    u: str
    v: str
    ve: float
    proxy_score: float
    csv_vt: float | None
    csv_status: str


@dataclass(frozen=True)
class Verified:
    candidate: Candidate
    vt: float
    exact_status: str
    source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify top candidates from search_candidates CSV and emit submit.txt rows."
    )
    parser.add_argument("--input", required=True, help="CSV produced by search_candidates.")
    parser.add_argument("--top", type=int, default=50, help="Number of proxy-ranked candidates to verify.")
    parser.add_argument("--start-rank", type=int, default=0, help="Skip this many proxy-ranked candidates first.")
    parser.add_argument("--out", default="submit.txt", help="Output submit file.")
    parser.add_argument("--base-submit", default="submit.txt", help="Existing submit rows to preserve.")
    parser.add_argument("--audit-out", default="experiments/verified_candidates.csv", help="Audit CSV path.")
    parser.add_argument("--exact-bin", default="./exact_oracle", help="Path to exact_oracle.")
    parser.add_argument("--score-bin", default="./score", help="Path to score checker.")
    parser.add_argument("--exact-limit", type=int, help="Debug-only truncated oracle limit.")
    parser.add_argument("--timeout", type=float, default=0.0, help="Per-candidate exact timeout in seconds; 0 disables.")
    parser.add_argument(
        "--use-csv-vt",
        action="store_true",
        help="Use VT already present in CSV rows instead of calling exact_oracle.",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=None,
        help="Fail if final total_score is below this value.",
    )
    parser.add_argument(
        "--require-improvement",
        action="store_true",
        help="Fail unless final total_score is strictly greater than --min-score.",
    )
    parser.add_argument(
        "--dedup",
        choices=("none", "ruv", "uv"),
        default="uv",
        help="Submit deduplication key; uv is the conservative contest-safe default.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Do not exact-verify candidates whose dedup key already exists in the base submit file.",
    )
    return parser.parse_args()


def norm_mask(value: str) -> str:
    return f"0x{int(value, 0):08x}"


def parse_float(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    return float(value)


def load_candidates(path: Path) -> list[Candidate]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    candidates: list[Candidate] = []
    for row in rows:
        u = norm_mask(row["u"])
        v = norm_mask(row["v"])
        ve = float(row["VE"])
        if int(u, 0) == 0 or int(v, 0) == 0 or ve == 0.0:
            continue
        candidates.append(
            Candidate(
                r=int(row["r"]),
                u=u,
                v=v,
                ve=ve,
                proxy_score=float(row.get("proxy_score") or 0.0),
                csv_vt=parse_float(row.get("VT", "")),
                csv_status=row.get("status", ""),
            )
        )
    candidates.sort(key=lambda item: (item.proxy_score, abs(item.ve)), reverse=True)
    return candidates


@dataclass(frozen=True)
class SubmitRow:
    r: int
    u: str
    v: str
    vt: float
    ve: float
    line: str


def load_base_rows(path: Path) -> list[SubmitRow]:
    rows: list[SubmitRow] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = SUBMIT_RE.match(stripped)
        if not match:
            continue
        rows.append(
            SubmitRow(
                r=int(match.group("r")),
                u=norm_mask(match.group("u")),
                v=norm_mask(match.group("v")),
                vt=float(match.group("vt")),
                ve=float(match.group("ve")),
                line=stripped,
            )
        )
    return rows


def valid_interval(vt: float, ve: float) -> bool:
    if vt == 0.0 or ve == 0.0 or not math.isfinite(vt) or not math.isfinite(ve):
        return False
    return abs(ve - vt) <= abs(vt) * 0.25 + 1e-30


def score_value(r: int, ve: float) -> float:
    return 2.0 * r + math.log2(abs(ve))


def positive_score(r: int, ve: float) -> bool:
    return score_value(r, ve) > 0.0


def run_exact(candidate: Candidate, args: argparse.Namespace) -> Verified | None:
    if args.use_csv_vt:
        if candidate.csv_vt is None:
            return None
        return Verified(candidate, candidate.csv_vt, candidate.csv_status or "csv_vt", "csv")

    cmd = [args.exact_bin, "--r", str(candidate.r), "--u", candidate.u, "--v", candidate.v]
    if args.exact_limit is not None:
        cmd.extend(["--limit", str(args.exact_limit)])
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=args.timeout or None,
        )
    except subprocess.TimeoutExpired:
        return None
    except subprocess.CalledProcessError as exc:
        print(exc.stderr, file=sys.stderr, end="")
        return None

    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return None
    row = next(csv.DictReader(lines))
    if row["status"] != "exact":
        return None
    return Verified(candidate, float(row["VT"]), row["status"], "exact_oracle")


def submit_line(item: Verified) -> str:
    c = item.candidate
    return f"@({c.r}, {c.u}, {c.v}, {item.vt:.24g}, {c.ve:.24g})"


def dedup_key(r: int, u: str, v: str, mode: str) -> tuple[int, str, str] | tuple[str, str] | tuple[int, int, str, str]:
    if mode == "ruv":
        return (r, u, v)
    if mode == "uv":
        return (u, v)
    return (id((r, u, v)), r, u, v)


def add_submit_row(
    rows: dict[tuple[object, ...], tuple[float, str]],
    key: tuple[object, ...],
    score: float,
    line: str,
) -> None:
    previous = rows.get(key)
    if previous is None or score > previous[0]:
        rows[key] = (score, line)


def run_score(score_bin: str, submit_path: Path, dedup: str) -> tuple[float, str]:
    completed = subprocess.run(
        [score_bin, "--dedup", dedup, "--positive-only", str(submit_path)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    output = completed.stdout
    total = None
    for line in output.splitlines():
        if line.startswith("total_score="):
            total = float(line.split("=", 1)[1])
    if total is None:
        raise RuntimeError("score output did not include total_score")
    return total, output


def write_audit(path: Path, verified: list[Verified]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["r", "u", "v", "VE", "proxy_score", "VT", "valid", "score_positive", "status", "source"])
        for item in verified:
            c = item.candidate
            writer.writerow(
                [
                    c.r,
                    c.u,
                    c.v,
                    f"{c.ve:.24g}",
                    f"{c.proxy_score:.24g}",
                    f"{item.vt:.24g}",
                    int(valid_interval(item.vt, c.ve)),
                    int(positive_score(c.r, c.ve)),
                    item.exact_status,
                    item.source,
                ]
            )


def main() -> int:
    args = parse_args()
    input_path = Path(args.input)
    out_path = Path(args.out)
    base_path = Path(args.base_submit)
    audit_path = Path(args.audit_out)

    verified_rows: dict[tuple[object, ...], tuple[float, str]] = {}
    for row in load_base_rows(base_path):
        if valid_interval(row.vt, row.ve) and positive_score(row.r, row.ve):
            key = dedup_key(row.r, row.u, row.v, args.dedup)
            add_submit_row(verified_rows, key, score_value(row.r, row.ve), row.line)
    audited: list[Verified] = []

    selected = load_candidates(input_path)[args.start_rank :]
    attempted = 0
    skipped_existing = 0
    for candidate in selected:
        if attempted >= args.top:
            break
        key = dedup_key(candidate.r, candidate.u, candidate.v, args.dedup)
        if args.skip_existing and key in verified_rows:
            skipped_existing += 1
            continue
        attempted += 1
        item = run_exact(candidate, args)
        if item is None:
            continue
        audited.append(item)
        if valid_interval(item.vt, candidate.ve) and positive_score(candidate.r, candidate.ve):
            add_submit_row(verified_rows, key, score_value(candidate.r, candidate.ve), submit_line(item))

    out_path.write_text("\n".join(line for _, line in verified_rows.values()) + "\n", encoding="utf-8")
    write_audit(audit_path, audited)
    total_score, score_output = run_score(args.score_bin, out_path, args.dedup)
    print(score_output, end="")
    print(f"verified_candidates={len(audited)}")
    print(f"attempted_candidates={attempted}")
    print(f"skipped_existing={skipped_existing}")
    print(f"submit_rows={len(verified_rows)}")

    if args.min_score is not None:
        if args.require_improvement and total_score <= args.min_score:
            print(f"total_score did not improve beyond {args.min_score}: {total_score}", file=sys.stderr)
            return 1
        if not args.require_improvement and total_score < args.min_score:
            print(f"total_score is below {args.min_score}: {total_score}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
