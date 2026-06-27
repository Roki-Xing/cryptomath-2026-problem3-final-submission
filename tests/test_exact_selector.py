import csv
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SELECTION_SHA = "73b89eb62070546f87c8e9fa05b377d4de73468338d273abc40b1020cdab79ce"


def run_selector(out_dir: Path) -> None:
    subprocess.run(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/prepare_selector_inputs.py",
            "--final-ru",
            "experiments/frozen/final_ru.csv",
            "--out",
            str(out_dir),
        ],
        cwd=ROOT,
        check=True,
    )
    subprocess.run(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/select_pilot.py",
            "--final-ru",
            "experiments/frozen/final_ru.csv",
            "--final-queries",
            "experiments/frozen/final_queries.csv",
            "--complexity-input",
            str(out_dir / "COMPLEXITY_INPUT.csv"),
            "--spotcheck-coordinates",
            str(out_dir / "SPOTCHECK_COORDINATES.csv"),
            "--out",
            str(out_dir),
        ],
        cwd=ROOT,
        check=True,
    )


def main() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as tmpdir:
        tmp = Path(tmpdir)
        out_a = tmp / "a"
        out_b = tmp / "b"
        run_selector(out_a)
        run_selector(out_b)

        for name in (
            "COMPLEXITY_INPUT.csv",
            "SPOTCHECK_COORDINATES.csv",
            "SELECTOR_INPUT_PREPARATION.json",
            "SELECTOR_INPUT_PROTOCOL.md",
            "PILOT_SELECTION.csv",
            "PILOT_SELECTION.json",
            "PROTOCOL.md",
            "SELECTOR_PROVENANCE.json",
        ):
            assert (out_a / name).read_bytes() == (out_b / name).read_bytes(), name

        payload = json.loads((out_a / "PILOT_SELECTION.json").read_text(encoding="utf-8"))
        assert payload["selected_columns"] == 344
        assert payload["round_distribution"] == {"r1": 120, "r2": 128, "r3": 96}
        assert payload["selection_payload_sha256"] == EXPECTED_SELECTION_SHA
        assert hashlib.sha256((out_a / "PILOT_SELECTION.csv").read_bytes()).hexdigest() == EXPECTED_SELECTION_SHA

        source = (ROOT / "experiments/exact_way2/select_pilot.py").read_text(encoding="utf-8")
        assert "submit_audit.csv" not in source
        assert "exact_spotcheck.csv" not in source
        for forbidden in ("frozen_way2_ve", "submitted_vt_field_snapshot", "future_way1_numerator"):
            assert forbidden not in source

        bad_audit = tmp / "bad_submit_audit.csv"
        with (ROOT / "experiments/submit_audit.csv").open(newline="", encoding="utf-8") as src, bad_audit.open(
            "w", newline="", encoding="utf-8"
        ) as dst:
            rows = list(csv.DictReader(src))
            fieldnames = list(rows[0].keys())
            rows[0]["generated_transitions"] = str(int(rows[0]["generated_transitions"]) + 1)
            writer = csv.DictWriter(dst, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        failed = subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                "experiments/exact_way2/prepare_selector_inputs.py",
                "--final-ru",
                "experiments/frozen/final_ru.csv",
                "--audit",
                str(bad_audit),
                "--out",
                str(tmp / "bad"),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert failed.returncode != 0
        assert "inconsistent" in failed.stderr or "inconsistent" in failed.stdout
    print("exact selector tests passed")


if __name__ == "__main__":
    main()
