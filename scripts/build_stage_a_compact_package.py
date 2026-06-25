#!/usr/bin/env python3
"""Build a compact Stage-A closeout package from an explicit allowlist."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_PR = (
    "https://github.com/Roki-Xing/cryptomath-2026-problem3-final-submission/pull/4"
)
ALLOWLIST_VERSION = "stage-a-compact-allowlist-v1"
ALLOWLIST = (
    "bench/way1/STAGE_A_SUMMARY.json",
    "bench/way1/SUMMARY.md",
    "bench/way1/PROTOCOL.md",
    "bench/way1/benchmark_schema.json",
    "bench/way1/MANIFEST.json",
    "bench/way1/CI_EVIDENCE.json",
    "bench/way1/ARTIFACT_INDEX.json",
    "bench/way1/ARTIFACT_RETENTION_PLAN.md",
    "bench/way1/SHA256SUMS.txt",
    "bench/way1/stage_a0/SUMMARY.json",
    "bench/way1/stage_a0/MANIFEST.json",
    "bench/way1/stage_a0/SHA256SUMS.txt",
    "bench/way1/stage_a1/SUMMARY.json",
    "bench/way1/stage_a1/MANIFEST.json",
    "bench/way1/stage_a1/SHA256SUMS.txt",
    "bench/way1/stage_a2/SUMMARY.json",
    "bench/way1/stage_a2/MANIFEST.json",
    "bench/way1/stage_a2/SHA256SUMS.txt",
    "bench/way1/stage_toolchain/SUMMARY.json",
    "bench/way1/stage_toolchain/MANIFEST.json",
    "bench/way1/stage_toolchain/SHA256SUMS.txt",
)
REQUIRED_SUMMARY = (
    "bench/way1/STAGE_A_SUMMARY.json",
    "bench/way1/SUMMARY.md",
    "bench/way1/PROTOCOL.md",
    "bench/way1/benchmark_schema.json",
    "bench/way1/stage_a0/SUMMARY.json",
    "bench/way1/stage_a1/SUMMARY.json",
    "bench/way1/stage_a2/SUMMARY.json",
    "bench/way1/stage_toolchain/SUMMARY.json",
)
REQUIRED_MANIFEST = tuple(path for path in ALLOWLIST if path not in REQUIRED_SUMMARY)
GENERATED_MANIFEST = "STAGE_A_COMPACT_MANIFEST.json"
GENERATED_SHA = "STAGE_A_COMPACT_SHA256SUMS.txt"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def ensure_allowlist_exists() -> None:
    missing = [path for path in ALLOWLIST if not (ROOT / path).is_file()]
    if missing:
        raise FileNotFoundError(f"missing allowlisted files: {missing}")


def ensure_target_empty(out_dir: Path) -> None:
    if out_dir.exists():
        if not out_dir.is_dir():
            raise RuntimeError(f"target exists and is not a directory: {out_dir}")
        if any(out_dir.iterdir()):
            raise RuntimeError(f"target directory is not empty: {out_dir}")
    else:
        out_dir.mkdir(parents=True)


def copy_allowlisted_files(out_dir: Path) -> list[dict[str, object]]:
    copied: list[dict[str, object]] = []
    for relative in ALLOWLIST:
        source = ROOT / relative
        destination = out_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        copied.append(
            {
                "path": relative,
                "sha256": sha256_file(destination),
                "size_bytes": destination.stat().st_size,
            }
        )
    return copied


def write_compact_manifest(
    out_dir: Path,
    copied_files: list[dict[str, object]],
    source_pr: str,
) -> Path:
    manifest_path = out_dir / GENERATED_MANIFEST
    manifest = {
        "schema": "way1-stage-a-compact-manifest-v1",
        "source_pr": source_pr,
        "source_head": git_output("rev-parse", "HEAD"),
        "builder_commit": git_output("rev-parse", "HEAD"),
        "allowlist_version": ALLOWLIST_VERSION,
        "generated_at_utc": git_output("show", "-s", "--format=%cI", "HEAD"),
        "file_count": len(copied_files),
        "total_bytes": sum(int(item["size_bytes"]) for item in copied_files),
        "required_summary": list(REQUIRED_SUMMARY),
        "required_manifest": list(REQUIRED_MANIFEST),
        "generated_files": [GENERATED_MANIFEST, GENERATED_SHA],
        "files": copied_files,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def write_compact_sha256sums(out_dir: Path) -> Path:
    sha_path = out_dir / GENERATED_SHA
    files_to_hash = sorted(
        path
        for path in out_dir.rglob("*")
        if path.is_file() and path.name != GENERATED_SHA
    )
    lines = []
    for path in files_to_hash:
        relative = path.relative_to(out_dir).as_posix()
        lines.append(f"{sha256_file(path)}  {relative}")
    sha_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return sha_path


def build_package(out_dir: Path, source_pr: str = DEFAULT_SOURCE_PR) -> dict[str, object]:
    ensure_allowlist_exists()
    ensure_target_empty(out_dir)
    copied_files = copy_allowlisted_files(out_dir)
    manifest_path = write_compact_manifest(out_dir, copied_files, source_pr)
    sha_path = write_compact_sha256sums(out_dir)
    return {
        "manifest": manifest_path,
        "sha256sums": sha_path,
        "file_count": len(copied_files),
        "total_bytes": sum(int(item["size_bytes"]) for item in copied_files),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="empty output directory")
    parser.add_argument(
        "--source-pr",
        default=DEFAULT_SOURCE_PR,
        help="source pull request URL recorded in the compact manifest",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = build_package(Path(args.out), source_pr=args.source_pr)
    print(
        json.dumps(
            {
                "status": "ok",
                "manifest": str(result["manifest"]),
                "sha256sums": str(result["sha256sums"]),
                "file_count": result["file_count"],
                "total_bytes": result["total_bytes"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - CLI failure path
        print(f"error: {exc}", file=sys.stderr)
        raise
