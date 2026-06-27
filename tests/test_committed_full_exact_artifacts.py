import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_ROOT = ROOT / "artifacts" / "way2_exact" / "full"
EXPECTED_ARCHIVE_SHA = {
    "r1_cpp_int": "68b88b06204dfee4cba9440ea1fc109b0a24c9c17f99388f4448393d583c1b2a",
    "r1_int128_checked": "61f0575cf9099daa1058069d3858e19df8767c53835b2b529e46a670ef7c07a1",
    "r2_cpp_int": "56a8ce9511609f250df0dfcd1ab153ff07d846eb92d296d21bf1dacb70a2a078",
    "r2_int128_checked": "3ca8cdedd344b7156b1f188b8cf0d72692478a38cd66425a67db568c230154db",
    "r3_cpp_int": "1b2296fb5cd9b7e4060e6a9038e3dfb322ad9fd471a5d27630c4c8387d4f8232",
    "r3_int128_checked": "745b7c7a7b07e6f211a272045bdb5316f39beced6c9ff7e2945c88c63ac3c620",
}


def main() -> None:
    required = [
        ARTIFACT_ROOT / "SUMMARY.json",
        ARTIFACT_ROOT / "COMPARE.json",
        ARTIFACT_ROOT / "MANIFEST.json",
        ARTIFACT_ROOT / "PROVENANCE.json",
        ARTIFACT_ROOT / "FULL_SELECTION.json",
        ARTIFACT_ROOT / "FULL_RUN_AUTHORIZATION.json",
        ARTIFACT_ROOT / "RAW_EVIDENCE_INDEX.json",
    ]
    if not ARTIFACT_ROOT.exists() or not all(path.exists() for path in required):
        print("committed full exact artifact test skipped")
        return

    summary = json.loads((ARTIFACT_ROOT / "SUMMARY.json").read_text(encoding="utf-8"))
    compare = json.loads((ARTIFACT_ROOT / "COMPARE.json").read_text(encoding="utf-8"))
    selection = json.loads((ARTIFACT_ROOT / "FULL_SELECTION.json").read_text(encoding="utf-8"))
    auth = json.loads((ARTIFACT_ROOT / "FULL_RUN_AUTHORIZATION.json").read_text(encoding="utf-8"))
    raw_index = json.loads((ARTIFACT_ROOT / "RAW_EVIDENCE_INDEX.json").read_text(encoding="utf-8"))
    manifest = json.loads((ARTIFACT_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))

    assert summary["selected_columns"] == 4760
    assert summary["cpp_int_completed_columns"] == 4760
    assert summary["int128_completed_columns"] == 4760
    assert summary["frozen_comparison"] == {
        "EXACT_EQUAL": 138338,
        "NOT_EQUAL": 0,
        "PARSE_ERROR": 0,
        "MISSING_ENDPOINT": 0,
    }
    assert compare["cross_backend_canonical_column_digest_mismatch"] == 0
    assert compare["cross_backend_endpoint_numerator_mismatch"] == 0
    assert compare["way1_spotcheck_rows"] == 18
    assert compare["way1_spotcheck_mismatch"] == 0

    assert selection["selected_columns"] == 4760
    assert selection["unique_ru_count"] == 4760
    assert selection["round_distribution"] == {"r1": 120, "r2": 4544, "r3": 96}
    assert selection["round_distribution_by_r"] == {"1": 120, "2": 4544, "3": 96}

    assert auth["full_4760_scope"] is True
    assert auth["full_selection_row_count"] == 4760
    assert auth["unique_ru_count"] == 4760
    assert auth["round_distribution"] == {"1": 120, "2": 4544, "3": 96}
    assert auth["full_selection_sha256"] == auth["cpp_int_selection_sha256"]
    assert auth["full_selection_sha256"] == selection["selection_payload_sha256"]

    manifest_counts: dict[str, int] = {}
    for entry in manifest["files"]:
        manifest_counts[entry["category"]] = manifest_counts.get(entry["category"], 0) + 1
        artifact_path = ARTIFACT_ROOT / entry["path"]
        assert artifact_path.exists()
        assert entry["sha256"] == subprocess.check_output(["sha256sum", str(artifact_path)], text=True).split()[0]
        assert entry["size"] == artifact_path.stat().st_size
    assert manifest["category_counts"] == manifest_counts

    assert raw_index["archive_count"] == 6
    assert raw_index["bundle_count"] == 9520
    for archive in raw_index["archives"]:
        assert archive["archive_group"] in EXPECTED_ARCHIVE_SHA
        assert archive["archive_sha256"] == EXPECTED_ARCHIVE_SHA[archive["archive_group"]]
        assert archive["archive_format"] == "tar.zst"
        assert archive["archive_name"] == f"{archive['archive_group']}.tar.zst"
        assert archive["release_asset_name"] == archive["archive_name"]
        assert archive["release_asset_uri_template"].endswith(archive["archive_name"])
        assert "archive_path" not in archive
        assert not archive["archive_name"].startswith(("/tmp/", "/home/", "C:\\"))
        assert not archive["release_asset_name"].startswith(("/tmp/", "/home/", "C:\\"))
        assert not archive["release_asset_uri_template"].startswith(("/tmp/", "/home/", "C:\\"))
        diagnostics = archive.get("local_generation_diagnostics", {})
        assert isinstance(diagnostics, dict)

    sha_lines = (ARTIFACT_ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines()
    assert sha_lines
    assert all("  artifacts/way2_exact/full/" in line for line in sha_lines)
    assert all("  ./" not in line for line in sha_lines)

    subprocess.run(
        ["sha256sum", "-c", str(ARTIFACT_ROOT / "SHA256SUMS.txt")],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    print("committed full exact artifact tests passed")


if __name__ == "__main__":
    main()
