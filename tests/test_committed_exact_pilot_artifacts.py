import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "way2_exact" / "pilot"
EXPECTED_BINARY_SHA = "649f60b87db680588d306bfe8db2df6da887a43d5844d41e0f7b8013b1f9d7c6"


def main() -> None:
    required = [
        ARTIFACT_ROOT / "SUMMARY.json",
        ARTIFACT_ROOT / "COMPARE.json",
        ARTIFACT_ROOT / "MANIFEST.json",
        ARTIFACT_ROOT / "PROVENANCE.json",
        ARTIFACT_ROOT / "ENVIRONMENT.json",
        ARTIFACT_ROOT / "BUILD_REPRODUCIBILITY.json",
    ]
    if not ARTIFACT_ROOT.exists() or not all(path.exists() for path in required):
        print("committed exact pilot artifact test skipped")
        return

    summary = json.loads((ARTIFACT_ROOT / "SUMMARY.json").read_text(encoding="utf-8"))
    compare = json.loads((ARTIFACT_ROOT / "COMPARE.json").read_text(encoding="utf-8"))
    manifest = json.loads((ARTIFACT_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    provenance = json.loads((ARTIFACT_ROOT / "PROVENANCE.json").read_text(encoding="utf-8"))
    environment = json.loads((ARTIFACT_ROOT / "ENVIRONMENT.json").read_text(encoding="utf-8"))
    build_repro = json.loads((ARTIFACT_ROOT / "BUILD_REPRODUCIBILITY.json").read_text(encoding="utf-8"))

    assert summary["selected_columns"] == 344
    assert summary["frozen_comparison"]["EXACT_EQUAL"] + summary["frozen_comparison"]["NOT_EQUAL"] + summary["frozen_comparison"]["PARSE_ERROR"] + summary["frozen_comparison"]["MISSING_ENDPOINT"] == summary["total_endpoint_count"]
    assert compare["selected_endpoint_rows"] == summary["total_endpoint_count"]
    assert manifest["status"] == summary["status"]
    assert provenance["source_tree_dirty"] is False
    assert environment["source_tree_dirty"] is False
    assert not str(provenance["artifact_root"]).startswith("/home/")
    assert not str(environment["artifact_root"]).startswith("/home/")
    assert not str(provenance["binary_path"]).startswith("/")
    assert not str(environment["binary_path"]).startswith("/")
    assert not str(environment["selection_path"]).startswith("/")
    assert not str(environment["queries_path"]).startswith("/")
    assert provenance["artifact_committed_in_commit"]
    assert build_repro["binary_sha256_match"] is True
    assert build_repro["first_clean_build"]["binary_sha256"] == EXPECTED_BINARY_SHA
    assert build_repro["second_clean_build"]["binary_sha256"] == EXPECTED_BINARY_SHA
    assert build_repro["first_clean_build"]["objects"]
    assert build_repro["second_clean_build"]["objects"]
    assert build_repro["first_clean_build"]["link_command"]
    assert build_repro["second_clean_build"]["link_command"]
    assert manifest["category_counts"]["PILOT_RAW_EVIDENCE"] > 0
    assert all(entry["path"] not in {"MANIFEST.json", "SHA256SUMS.txt"} for entry in manifest["files"])
    assert all("size" in entry and int(entry["size"]) >= 0 for entry in manifest["files"])
    category_counts: dict[str, int] = {}
    for entry in manifest["files"]:
        path = ARTIFACT_ROOT / entry["path"]
        assert path.exists()
        assert path.stat().st_size == int(entry["size"])
        category_counts[entry["category"]] = category_counts.get(entry["category"], 0) + 1
    assert category_counts == manifest["category_counts"]
    assert compare["cross_backend_canonical_column_digest_mismatch"] == 0
    assert compare["cross_backend_endpoint_numerator_mismatch"] == 0
    repeat_cpp = summary["repeat_subset"]["cpp_int"]
    repeat_int = summary["repeat_subset"]["int128_checked"]
    assert repeat_cpp["canonical_column_digest_equal"] is True
    assert repeat_cpp["endpoint_payload_equal"] is True
    assert repeat_int["canonical_column_digest_equal"] is True
    assert repeat_int["endpoint_payload_equal"] is True
    assert repeat_cpp["bundle_output_sha256_is_diagnostic"] is True
    assert repeat_int["bundle_output_sha256_is_diagnostic"] is True
    sha_lines = (ARTIFACT_ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    assert any(line.endswith("  ./artifacts/way2_exact/pilot/MANIFEST.json") for line in sha_lines)

    subprocess.run(
        ["sha256sum", "-c", str(ARTIFACT_ROOT / "SHA256SUMS.txt")],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    print("committed exact pilot artifact tests passed")


if __name__ == "__main__":
    main()
