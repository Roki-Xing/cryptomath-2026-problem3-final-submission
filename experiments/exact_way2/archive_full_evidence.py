#!/usr/bin/env python3
"""Create deterministic raw-evidence archives and compact representative bundles."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import tarfile
from collections import defaultdict
from pathlib import Path

from common import current_source_commit, current_source_tree_sha, read_json, sha256_file, write_json

REPOSITORY = "Roki-Xing/cryptomath-2026-problem3-final-submission"
ARCHIVE_FORMAT = "tar.zst"


def require_zstandard():
    try:
        import zstandard  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "missing Python dependency 'zstandard'; install it with "
            "'python3 -m pip install -r requirements-dev.txt'"
        ) from exc
    return zstandard


def bundle_total_bytes(bundle_dir: Path) -> int:
    return sum(path.stat().st_size for path in bundle_dir.rglob("*") if path.is_file())


def representative_keys(root: Path) -> list[str]:
    compare = read_json(root / "COMPARE.json")
    if not isinstance(compare, dict):
        raise SystemExit("invalid COMPARE.json")
    chosen: list[str] = []
    with (root / "COMPARISONS.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        by_round: dict[int, list[tuple[str, str]]] = defaultdict(list)
        for row in reader:
            key = f"r{row['r']}_{row['u'].lower()}"
            by_round[int(row["r"])].append((key, row["u"].lower()))
    for r in (1, 2, 3):
        if by_round[r]:
            chosen.append(sorted(by_round[r])[0][0])
    return chosen


def create_archive(archive_path: Path, source_root: Path, bundle_dirs: list[Path]) -> dict[str, object]:
    zstandard = require_zstandard()
    if archive_path.exists():
        archive_path.unlink()
    with archive_path.open("wb") as raw_handle:
        compressor = zstandard.ZstdCompressor(level=19, write_checksum=True)
        with compressor.stream_writer(raw_handle) as compressed_handle:
            with tarfile.open(fileobj=compressed_handle, mode="w|") as tar:
                for bundle_dir in sorted(bundle_dirs):
                    for path in [bundle_dir, *sorted(bundle_dir.rglob("*"))]:
                        relative = str(path.relative_to(source_root)).replace("\\", "/")
                        info = tar.gettarinfo(str(path), arcname=relative)
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        info.mtime = 0
                        if path.is_file():
                            with path.open("rb") as handle:
                                tar.addfile(info, handle)
                        else:
                            tar.addfile(info)
    file_count = sum(1 for path in bundle_dirs for _ in path.rglob("*") if _.is_file())
    total_bytes = sum(bundle_total_bytes(path) for path in bundle_dirs)
    return {
        "archive_name": archive_path.name,
        "archive_group": archive_path.stem.replace(".tar", ""),
        "archive_format": ARCHIVE_FORMAT,
        "archive_sha256": sha256_file(archive_path),
        "file_count": file_count,
        "total_bytes": total_bytes,
        "bundle_count": len(bundle_dirs),
        "local_generation_diagnostics": {
            "archive_output_path": str(archive_path),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--archive-root", required=True)
    args = parser.parse_args()

    root = Path(args.artifact_root)
    archive_root = Path(args.archive_root)
    archive_root.mkdir(parents=True, exist_ok=True)
    completed_root = root / "completed"
    if not completed_root.exists():
        raise SystemExit("missing completed/ directory")

    manifest_entries = []
    grouped: dict[str, list[Path]] = defaultdict(list)
    for bundle_dir in sorted(path for path in completed_root.iterdir() if path.is_dir()):
        done = read_json(bundle_dir / "DONE.json")
        if not isinstance(done, dict):
            raise SystemExit(f"invalid DONE payload: {bundle_dir}")
        backend = str(done["backend"])
        group = f"r{done['r']}_{backend}"
        grouped[group].append(bundle_dir)
        manifest_entries.append(
            {
                "bundle": bundle_dir.name,
                "r": int(done["r"]),
                "u": str(done["u"]).lower(),
                "backend": backend,
                "column_sha256": sha256_file(bundle_dir / "column.json"),
                "endpoints_sha256": sha256_file(bundle_dir / "endpoints.csv"),
                "done_sha256": sha256_file(bundle_dir / "DONE.json"),
                "bundle_bytes": bundle_total_bytes(bundle_dir),
            }
        )

    raw_manifest = {
        "source_commit": current_source_commit(),
        "source_tree_sha": current_source_tree_sha(),
        "bundle_count": len(manifest_entries),
        "bundles": manifest_entries,
    }
    write_json(root / "RAW_EVIDENCE_MANIFEST.json", raw_manifest)
    raw_manifest_sha = sha256_file(root / "RAW_EVIDENCE_MANIFEST.json")

    archives = []
    for group, bundle_dirs in sorted(grouped.items()):
        archive_path = archive_root / f"{group}.tar.zst"
        archive_info = create_archive(archive_path, completed_root, bundle_dirs)
        archive_info["unpacked_manifest_sha256"] = raw_manifest_sha
        archive_info["source_commit"] = current_source_commit()
        archive_info["source_tree_sha"] = current_source_tree_sha()
        archive_info["release_asset_name"] = archive_info["archive_name"]
        archive_info["release_asset_uri_template"] = (
            f"https://github.com/{REPOSITORY}/releases/download/{{release_tag}}/{archive_info['archive_name']}"
        )
        archives.append(archive_info)

    representative_root = root / "representative_completed"
    if representative_root.exists():
        shutil.rmtree(representative_root)
    representative_root.mkdir(parents=True, exist_ok=True)
    chosen_prefixes = representative_keys(root)
    chosen_paths = []
    for prefix in chosen_prefixes:
        for backend in ("cpp_int", "int128_checked"):
            bundle_dir = completed_root / f"{prefix}_{backend}"
            if bundle_dir.exists():
                shutil.copytree(bundle_dir, representative_root / bundle_dir.name)
                chosen_paths.append(bundle_dir.name)

    write_json(
        root / "RAW_EVIDENCE_INDEX.json",
        {
            "source_commit": current_source_commit(),
            "source_tree_sha": current_source_tree_sha(),
            "bundle_count": len(manifest_entries),
            "archive_count": len(archives),
            "archives": archives,
            "representative_bundles": chosen_paths,
            "retention_policy": {
                "git_contains_compact_only": True,
                "full_raw_bundles_committed_as_loose_files": False,
                "release_assets_are_primary_long_term_carrier": True,
                "ci_artifacts_are_mirror_only": True,
                "competition_package_excludes_full_raw_archives": True,
            },
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
