#!/usr/bin/env python3
"""Build submit.txt from reproducible way-2 source rows.

Args:
    See --help for CLI options.

Returns:
    Exit code 0 when the submit file is written.
"""

from __future__ import annotations

import argparse
import csv
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
class SubmitRow:
    r: int
    u: int
    v: int
    vt: str
    ve: str

    def line(self) -> str:
        return f"@({self.r}, 0x{self.u:08x}, 0x{self.v:08x}, {self.vt}, {self.ve})"

    def key(self) -> tuple[int, int]:
        return (self.u, self.v)

    def score(self) -> float:
        import math

        return 2.0 * self.r + math.log2(abs(float(self.ve)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build submit.txt from r=1 enumeration plus selected certified rows.")
    parser.add_argument("--r1", default="submit_r1_full.txt", help="Path for generated r=1 rows.")
    parser.add_argument("--source-submit", default="submit.txt", help="Existing submit file used as r=2 source.")
    parser.add_argument(
        "--candidate-csv",
        action="append",
        default=[
            "experiments/r2_active1_emit_all.csv",
            "experiments/r2_active2_batch_1000_0100.csv",
            "experiments/r2_active2_batch_1100_0100.csv",
            "experiments/r2_active2_batch_1200_0100.csv",
            "experiments/r2_active2_batch_1300_0100.csv",
            "experiments/r2_active2_batch_1400_0100.csv",
            "experiments/r2_active2_batch_1500_0100.csv",
            "experiments/r2_active2_batch_1600_0100.csv",
            "experiments/r2_active2_batch_1700_0100.csv",
            "experiments/r2_active2_batch_1800_0100.csv",
            "experiments/r2_active2_batch_1900_0100.csv",
            "experiments/r2_active2_batch_200_0100.csv",
            "experiments/r2_active2_batch_2100_0100.csv",
            "experiments/r2_active2_batch_2200_0100.csv",
            "experiments/r2_active2_batch_2300_0100.csv",
            "experiments/r2_active2_batch_2400_0100.csv",
            "experiments/r2_active2_batch_2500_0100.csv",
            "experiments/r2_active2_batch_2600_0100.csv",
            "experiments/r2_active2_batch_2700_0100.csv",
            "experiments/r2_active2_batch_2800_0100.csv",
            "experiments/r2_active2_batch_2900_0100.csv",
            "experiments/r2_active2_batch_3000_0100.csv",
            "experiments/r2_active2_batch_300_0100.csv",
            "experiments/r2_active2_batch_3100_0100.csv",
            "experiments/r2_active2_batch_3200_0100.csv",
            "experiments/r2_active2_batch_3300_0100.csv",
            "experiments/r2_active2_batch_3400_0100.csv",
            "experiments/r2_active2_batch_3500_0100.csv",
            "experiments/r2_active2_batch_3600_0100.csv",
            "experiments/r2_active2_batch_3700_0100.csv",
            "experiments/r2_active2_batch_3800_0100.csv",
            "experiments/r2_active2_batch_3900_0100.csv",
            "experiments/r2_active2_batch_4000_0100.csv",
            "experiments/r2_active2_batch_400_0100.csv",
            "experiments/r2_active2_batch_4100_0100.csv",
            "experiments/r2_active2_batch_4200_0100.csv",
            "experiments/r2_active2_batch_4300_0100.csv",
            "experiments/r2_active2_batch_4400_0100.csv",
            "experiments/r2_active2_batch_4500_0100.csv",
            "experiments/r2_active2_batch_4600_0100.csv",
            "experiments/r2_active2_batch_4700_0100.csv",
            "experiments/r2_active2_batch_4800_0100.csv",
            "experiments/r2_active2_batch_4900_0100.csv",
            "experiments/r2_active2_batch_5000_0100.csv",
            "experiments/r2_active2_batch_500_0100.csv",
            "experiments/r2_active2_batch_5100_0100.csv",
            "experiments/r2_active2_batch_5200_0100.csv",
            "experiments/r2_active2_batch_5300_0100.csv",
            "experiments/r2_active2_batch_5400_0100.csv",
            "experiments/r2_active2_batch_5500_0100.csv",
            "experiments/r2_active2_batch_5600_0100.csv",
            "experiments/r2_active2_batch_5700_0100.csv",
            "experiments/r2_active2_batch_5800_0100.csv",
            "experiments/r2_active2_batch_5900_0100.csv",
            "experiments/r2_active2_batch_6000_0100.csv",
            "experiments/r2_active2_batch_6100_0100.csv",
            "experiments/r2_active2_batch_6200_0100.csv",
            "experiments/r2_active2_batch_6300_0100.csv",
            "experiments/r2_active2_batch_700_0100.csv",
            "experiments/r2_active2_batch_800_0100.csv",
            "experiments/r2_active2_batch_900_0100.csv",
            "experiments/r2_active2_edge120.csv",
            "experiments/r2_active2_edge6400.csv",
            "experiments/r2_active3_a3_15020.csv",
            "experiments/r2_active3_a3_50020.csv",
            "experiments/r2_active3_a3_100020.csv",
            "experiments/r2_active3_a3_190020.csv",
            "experiments/r2_active3_near_100010_0020.csv",
            "experiments/r2_active3_near_100030_0020.csv",
            "experiments/r2_active3_near_100050_0020.csv",
            "experiments/r2_active3_near_100070_0020.csv",
            "experiments/r2_active3_near_100090_0020.csv",
            "experiments/r2_active3_near_100110_0020.csv",
            "experiments/r2_active3_near_100130_0020.csv",
            "experiments/r2_active3_near_100150_0020.csv",
            "experiments/r2_active3_near_100170_0020.csv",
            "experiments/r2_active3_near_100190_0020.csv",
            "experiments/r2_active3_near_100230_0020.csv",
            "experiments/r2_active3_near_100270_0020.csv",
            "experiments/r2_active3_near_100290_0020.csv",
            "experiments/r2_active3_near_14950_0020.csv",
            "experiments/r2_active3_near_14970_0020.csv",
            "experiments/r2_active3_near_15010_0020.csv",
            "experiments/r2_active3_near_15030_0020.csv",
            "experiments/r2_active3_near_15050_0020.csv",
            "experiments/r2_active3_near_15070_0020.csv",
            "experiments/r2_active3_near_15090_0020.csv",
            "experiments/r2_active3_near_189970_0020.csv",
            "experiments/r2_active3_near_189990_0020.csv",
            "experiments/r2_active3_near_190010_0020.csv",
            "experiments/r2_active3_near_190030_0020.csv",
            "experiments/r2_active3_near_190050_0020.csv",
            "experiments/r2_active3_near_190070_0020.csv",
            "experiments/r2_active3_near_190090_0020.csv",
            "experiments/r2_active3_near_190110_0020.csv",
            "experiments/r2_active3_near_190130_0020.csv",
            "experiments/r2_active3_near_190150_0020.csv",
            "experiments/r2_active3_near_190170_0020.csv",
            "experiments/r2_active3_near_190190_0020.csv",
            "experiments/r2_active3_near_190210_0020.csv",
            "experiments/r2_active3_near_190230_0020.csv",
            "experiments/r2_active3_near_190250_0020.csv",
            "experiments/r2_active3_near_190270_0020.csv",
            "experiments/r2_active3_near_190290_0020.csv",
            "experiments/r2_active3_near_190310_0020.csv",
            "experiments/r2_active3_near_190330_0020.csv",
            "experiments/r2_active3_near_49590_0020.csv",
            "experiments/r2_active3_near_49610_0020.csv",
            "experiments/r2_active3_near_49630_0020.csv",
            "experiments/r2_active3_near_49650_0020.csv",
            "experiments/r2_active3_near_49670_0020.csv",
            "experiments/r2_active3_near_49690_0020.csv",
            "experiments/r2_active3_near_49710_0020.csv",
            "experiments/r2_active3_near_49730_0020.csv",
            "experiments/r2_active3_near_49750_0020.csv",
            "experiments/r2_active3_near_49770_0020.csv",
            "experiments/r2_active3_near_49790_0020.csv",
            "experiments/r2_active3_near_49810_0020.csv",
            "experiments/r2_active3_near_49830_0020.csv",
            "experiments/r2_active3_near_49850_0020.csv",
            "experiments/r2_active3_near_49870_0020.csv",
            "experiments/r2_active3_near_49890_0020.csv",
            "experiments/r2_active3_near_49910_0020.csv",
            "experiments/r2_active3_near_49930_0020.csv",
            "experiments/r2_active3_near_49950_0020.csv",
            "experiments/r2_active3_near_49970_0020.csv",
            "experiments/r2_active3_near_49990_0020.csv",
            "experiments/r2_active3_near_50000_0020.csv",
            "experiments/r2_active3_near_50010_0020.csv",
            "experiments/r2_active3_near_50020_0020.csv",
            "experiments/r2_active3_near_50030_0020.csv",
            "experiments/r2_active3_near_50040_0020.csv",
            "experiments/r2_active3_near_50050_0020.csv",
            "experiments/r2_active3_near_50060_0020.csv",
            "experiments/r2_active3_near_50070_0020.csv",
            "experiments/r2_active3_near_50090_0020.csv",
            "experiments/r2_active3_near_50110_0020.csv",
            "experiments/r2_active3_near_50130_0020.csv",
            "experiments/r2_active3_near_50150_0020.csv",
            "experiments/r2_active3_near_50170_0020.csv",
            "experiments/r2_active3_near_50190_0020.csv",
            "experiments/r2_active3_near_50210_0020.csv",
            "experiments/r2_active3_near_50230_0020.csv",
            "experiments/r2_active3_near_50250_0020.csv",
            "experiments/r2_active3_near_50270_0020.csv",
            "experiments/r2_active3_near_50290_0020.csv",
            "experiments/r2_active3_near_50310_0020.csv",
            "experiments/r2_active3_near_50330_0020.csv",
            "experiments/r2_active3_near_50350_0020.csv",
            "experiments/r2_active3_near_50370_0020.csv",
            "experiments/r2_active3_near_50390_0020.csv",
            "experiments/r2_active3_near_50410_0020.csv",
            "experiments/r2_active3_near_50430_0020.csv",
            "experiments/r2_active3_near_50450_0020.csv",
            "experiments/r2_active3_near_50470_0020.csv",
            "experiments/r2_active3_near_50490_0020.csv",
            "experiments/r2_active3_near_50510_0020.csv",
            "experiments/r2_active3_near_50530_0020.csv",
            "experiments/r2_active3_near_50550_0020.csv",
            "experiments/r2_active3_near_50570_0020.csv",
            "experiments/r2_active3_near_50590_0020.csv",
            "experiments/r2_active3_near_50610_0020.csv",
            "experiments/r2_active3_near_50630_0020.csv",
            "experiments/r2_active3_near_50650_0020.csv",
            "experiments/r2_active3_near_50670_0020.csv",
            "experiments/r2_active3_near_50690_0020.csv",
            "experiments/r2_active3_near_50710_0020.csv",
            "experiments/r2_active3_near_50730_0020.csv",
            "experiments/r2_active3_near_50750_0020.csv",
            "experiments/r2_active3_near_50770_0020.csv",
            "experiments/r2_active3_near_50790_0020.csv",
            "experiments/r2_active3_near_50810_0020.csv",
            "experiments/r2_active3_near_99710_0020.csv",
            "experiments/r2_active3_near_99730_0020.csv",
            "experiments/r2_active3_near_99770_0020.csv",
            "experiments/r2_active3_near_99810_0020.csv",
            "experiments/r2_active3_near_99830_0020.csv",
            "experiments/r2_active3_near_99850_0020.csv",
            "experiments/r2_active3_near_99870_0020.csv",
            "experiments/r2_active3_near_99890_0020.csv",
            "experiments/r2_active3_near_99910_0020.csv",
            "experiments/r2_active3_near_99930_0020.csv",
            "experiments/r2_active3_near_99950_0020.csv",
            "experiments/r2_active3_near_99970_0020.csv",
            "experiments/r2_active3_near_99990_0020.csv",
            "experiments/r3_active1_emit_all.csv",
            "experiments/new_sweeps/r3_active2_lat/r3_active2_lat_cert_u2020shift_u4040shift_top64_beam200k_trans100k.csv",
            "experiments/new_sweeps/r3_active2_lat/r3_active2_lat_cert_u2020_u4040_top64_beam200k_trans100k.csv",
            "experiments/new_sweeps/r3_active2_lat/r3_active2_lat_cert_u60600000_u006060_top64_beam200k_trans100k.csv",
        ],
        help="Certified candidate_miner_approx CSV path. Repeatable.",
    )
    parser.add_argument(
        "--extra-csv",
        action="append",
        default=[],
        help=(
            "Extra certified candidate_miner_approx CSV path(s) to include in addition to the base set. "
            "This does not change the semantics of --candidate-csv overrides."
        ),
    )
    parser.add_argument("--out", default="submit.txt", help="Output submit file.")
    parser.add_argument("--enumerator", default="./enumerate_r1_positive", help="r=1 enumerator executable.")
    parser.add_argument("--score-bin", default="./score", help="Score checker executable.")
    parser.add_argument("--keep-r2", action="store_true", default=False, help="Also keep positive r=2 rows from source submit.")
    return parser.parse_args()


def parse_row(line: str) -> SubmitRow:
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


def load_rows(path: Path) -> list[SubmitRow]:
    rows: list[SubmitRow] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        rows.append(parse_row(stripped))
    return rows


def load_certified_candidates(path: Path) -> list[SubmitRow]:
    rows: list[SubmitRow] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["certified_no_truncation"] != "1":
                continue
            if float(row["proxy_score"]) <= 0.0:
                continue
            ve = row["VE"]
            rows.append(SubmitRow(r=int(row["r"]), u=int(row["u"], 0), v=int(row["v"], 0), vt=ve, ve=ve))
    return rows


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return completed.stdout


def extract_cli_values(argv: list[str], flag: str) -> list[str]:
    """Extract repeated `--flag value` / `--flag=value` occurrences from argv."""
    values: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == flag:
            if i + 1 >= len(argv):
                raise ValueError(f"missing value after {flag}")
            values.append(argv[i + 1])
            i += 2
            continue
        if arg.startswith(flag + "="):
            values.append(arg.split("=", 1)[1])
        i += 1
    return values


def main() -> int:
    args = parse_args()
    r1_path = Path(args.r1)
    run([args.enumerator, "--out", str(r1_path)])

    rows = load_rows(r1_path)
    # argparse with action='append' + default list will append onto the default.
    # For reproducibility scripts, it's convenient that specifying --candidate-csv
    # overrides the built-in default list rather than adding to it.
    cli_candidates = extract_cli_values(sys.argv[1:], "--candidate-csv")
    candidate_paths = cli_candidates if cli_candidates else args.candidate_csv
    candidate_paths = list(candidate_paths) + list(args.extra_csv)
    for candidate_path in candidate_paths:
        rows.extend(load_certified_candidates(Path(candidate_path)))
    if args.keep_r2:
        rows.extend(row for row in load_rows(Path(args.source_submit)) if row.r == 2 and row.score() > 0.0)

    best_by_uv: dict[tuple[int, int], SubmitRow] = {}
    for row in rows:
        key = row.key()
        previous = best_by_uv.get(key)
        if previous is None or row.score() > previous.score():
            best_by_uv[key] = row

    final_rows = sorted(best_by_uv.values(), key=lambda row: (row.r, row.u, row.v))
    out_path = Path(args.out)
    out_path.write_text("\n".join(row.line() for row in final_rows) + "\n", encoding="utf-8")

    score_output = run([args.score_bin, "--dedup", "uv", "--positive-only", str(out_path)])
    print(f"r1_rows={sum(1 for row in final_rows if row.r == 1)}")
    print(f"r2_rows={sum(1 for row in final_rows if row.r == 2)}")
    print(f"r3_rows={sum(1 for row in final_rows if row.r == 3)}")
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
