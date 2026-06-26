import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "way2_exact" / "pilot"


def main() -> None:
    if not ARTIFACT_ROOT.exists():
        print("committed exact pilot artifact test skipped")
        return

    summary = json.loads((ARTIFACT_ROOT / "SUMMARY.json").read_text(encoding="utf-8"))
    compare = json.loads((ARTIFACT_ROOT / "COMPARE.json").read_text(encoding="utf-8"))
    manifest = json.loads((ARTIFACT_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    provenance = json.loads((ARTIFACT_ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
    environment = json.loads((ARTIFACT_ROOT / "ENVIRONMENT.json").read_text(encoding="utf-8"))

    assert summary["selected_columns"] == 344
    assert summary["frozen_comparison"]["EXACT_EQUAL"] + summary["frozen_comparison"]["NOT_EQUAL"] + summary["frozen_comparison"]["PARSE_ERROR"] + summary["frozen_comparison"]["MISSING_ENDPOINT"] == summary["total_endpoint_count"]
    assert compare["selected_endpoint_rows"] == summary["total_endpoint_count"]
    assert manifest["status"] == summary["status"]
    assert provenance["source_tree_dirty"] is False
    assert environment["source_tree_dirty"] is False
    assert not str(provenance["artifact_root"]).startswith("/home/")
    assert not str(environment["artifact_root"]).startswith("/home/")

    subprocess.run(
        ["sha256sum", "-c", "SHA256SUMS.txt"],
        cwd=ARTIFACT_ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    print("committed exact pilot artifact tests passed")


if __name__ == "__main__":
    main()
