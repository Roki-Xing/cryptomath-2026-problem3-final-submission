import csv
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_selector(out_dir: Path) -> None:
    subprocess.run(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/select_full.py",
            "--final-ru",
            "experiments/frozen/final_ru.csv",
            "--final-queries",
            "experiments/frozen/final_queries.csv",
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

        for name in ("FULL_SELECTION.csv", "FULL_SELECTION.json", "PROTOCOL.md", "SELECTION_PROVENANCE.json"):
            assert (out_a / name).read_bytes() == (out_b / name).read_bytes(), name

        payload = json.loads((out_a / "FULL_SELECTION.json").read_text(encoding="utf-8"))
        assert payload["selected_columns"] == 4760
        assert payload["unique_ru_count"] == 4760
        assert payload["round_distribution"] == {"r1": 120, "r2": 4544, "r3": 96}
        assert payload["round_distribution_by_r"] == {"1": 120, "2": 4544, "3": 96}
        assert payload["selection_payload_sha256"] == hashlib.sha256(
            (out_a / "FULL_SELECTION.csv").read_bytes()
        ).hexdigest()
        rows = [tuple(entry[key] for key in ("r", "u")) for entry in payload["selection"]]
        assert rows == sorted(rows)

        final_ru_rows = sorted(
            [
                (int(row["r"]), row["u"].lower())
                for row in csv.DictReader(
                    (ROOT / "experiments" / "frozen" / "final_ru.csv").open(newline="", encoding="utf-8")
                )
            ]
        )
        assert final_ru_rows == rows
    print("full exact selection tests passed")


if __name__ == "__main__":
    main()
