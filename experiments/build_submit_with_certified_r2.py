#!/usr/bin/env python3
"""Build a submit draft from full r=1 rows and certified r=2 way-2 candidates.

Args:
    See --help for CLI options.

Returns:
    Exit code 0 when the draft submit file is written and scored.
"""

from __future__ import annotations

import argparse
import csv
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


SUBMIT_RE = re.compile(
    r"^@\(\s*(?P<r>\d+)\s*,\s*(?P<u>0x[0-9a-fA-F]+|\d+)\s*,\s*"
    r"(?P<v>0x[0-9a-fA-F]+|\d+)\s*,\s*(?P<vt>[^,]+)\s*,\s*(?P<ve>[^)]+)\s*\)$"
)


@dataclass(frozen=True)
class SubmitRow:
    r: int
    u: int
    v: int
    vt: str
    ve: str

    def key(self) -> tuple[int, int]:
        return (self.u, self.v)

    def score(self) -> float:
        return 2.0 * self.r + math.log2(abs(float(self.ve)))

    def line(self) -> str:
        return f"@({self.r}, 0x{self.u:08x}, 0x{self.v:08x}, {self.vt}, {self.ve})"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a submit draft with certified r=2 sparse-DP candidates.")
    parser.add_argument("--base-submit", default="submit.txt", help="Base submit file containing r=1 rows.")
    parser.add_argument("--candidate-csv", action="append", required=True, help="candidate_miner_approx CSV path.")
    parser.add_argument("--out", default="experiments/certified_r2_submit.txt", help="Output draft submit file.")
    parser.add_argument("--score-bin", default="./score", help="Score checker executable.")
    return parser.parse_args()


def parse_submit_row(line: str) -> SubmitRow:
    match = SUBMIT_RE.match(line.strip())
    if not match:
        raise ValueError(f"bad submit row: {line}")
    return SubmitRow(
        r=int(match.group("r")),
        u=int(match.group("u"), 0),
        v=int(match.group("v"), 0),
        vt=match.group("vt").strip(),
        ve=match.group("ve").strip(),
    )


def load_submit(path: Path) -> list[SubmitRow]:
    rows: list[SubmitRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        rows.append(parse_submit_row(stripped))
    return rows


def load_certified_r2(path: Path) -> list[SubmitRow]:
    rows: list[SubmitRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["r"] != "2":
                continue
            if row["certified_no_truncation"] != "1":
                continue
            if float(row["proxy_score"]) <= 0.0:
                continue
            ve = row["VE"]
            rows.append(SubmitRow(r=2, u=int(row["u"], 0), v=int(row["v"], 0), vt=ve, ve=ve))
    return rows


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.stdout


def main() -> int:
    args = parse_args()
    rows = [row for row in load_submit(Path(args.base_submit)) if row.r == 1]
    for candidate_path in args.candidate_csv:
        rows.extend(load_certified_r2(Path(candidate_path)))

    best_by_uv: dict[tuple[int, int], SubmitRow] = {}
    for row in rows:
        old = best_by_uv.get(row.key())
        if old is None or row.score() > old.score():
            best_by_uv[row.key()] = row

    final_rows = sorted(best_by_uv.values(), key=lambda row: (row.r, row.u, row.v))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(row.line() for row in final_rows) + "\n", encoding="utf-8")

    score_output = run([args.score_bin, "--dedup", "uv", "--positive-only", str(out_path)])
    print(f"r1_rows={sum(1 for row in final_rows if row.r == 1)}")
    print(f"r2_rows={sum(1 for row in final_rows if row.r == 2)}")
    score_summary = {
        line.split("=", 1)[0]: line
        for line in score_output.splitlines()
        if line.startswith(("valid_count=", "total_score="))
    }
    print(score_summary["valid_count"])
    print(score_summary["total_score"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
