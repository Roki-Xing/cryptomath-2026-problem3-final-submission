import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with tempfile.TemporaryDirectory(dir=ROOT) as tmpdir:
        tmp = Path(tmpdir)
        out_a = tmp / "a"
        out_b = tmp / "b"
        base_cmd = [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/select_pilot.py",
            "--final-ru",
            "experiments/frozen/final_ru.csv",
            "--final-queries",
            "experiments/frozen/final_queries.csv",
        ]
        subprocess.run([*base_cmd, "--out", str(out_a)], cwd=ROOT, check=True)
        subprocess.run([*base_cmd, "--out", str(out_b)], cwd=ROOT, check=True)

        for name in (
            "PILOT_SELECTION.csv",
            "PILOT_SELECTION.json",
            "PROTOCOL.md",
            "SELECTOR_PROVENANCE.json",
            "COMPLEXITY_INPUT.csv",
            "SPOTCHECK_COORDINATES.csv",
        ):
            assert (out_a / name).read_bytes() == (out_b / name).read_bytes(), name

        payload = json.loads((out_a / "PILOT_SELECTION.json").read_text(encoding="utf-8"))
        assert payload["selected_columns"] == 344
        assert payload["round_distribution"] == {"r1": 120, "r2": 128, "r3": 96}
        assert payload["selection_payload_sha256"]
    print("exact selector tests passed")


if __name__ == "__main__":
    main()
