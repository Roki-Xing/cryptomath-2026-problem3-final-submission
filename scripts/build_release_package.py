#!/usr/bin/env python3
"""Build a release-staging package with strict source metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "package-source-metadata-v1"
CURRENT_REPOSITORY = "Roki-Xing/cryptomath-2026-problem3-final-submission"
QUERY = [
    "--r",
    "1",
    "--u",
    "0x00000001",
    "--v",
    "0x70070000",
    "--backend",
    "cpp_int",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=cwd or ROOT, env=env, check=True)


def parse_metadata(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        key, value = line.split(":", 1)
        rows[key.strip()] = value.strip()
    return rows


def verify_staged_binary(staging_dir: Path, release_commit: str) -> None:
    artifact = staging_dir / "artifact.json"
    subprocess.run(
        [str(staging_dir / "estimator_exact"), *QUERY, "--out", str(artifact)],
        cwd=staging_dir,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    if payload["source_commit"] != release_commit:
        raise SystemExit("binary source_commit does not match release_commit")
    metadata = parse_metadata(staging_dir / "PACKAGE_SOURCE_COMMIT.txt")
    if metadata["schema"] != SCHEMA:
        raise SystemExit("unexpected package metadata schema")
    if metadata["release_commit"] != release_commit:
        raise SystemExit("PACKAGE_SOURCE_COMMIT release_commit does not match release checkout SHA")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--package-generated-at-utc")
    parser.add_argument("--submit-source-commit", required=True)
    parser.add_argument("--submit-sha256", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    if out_dir.exists():
        if not out_dir.is_dir():
            raise SystemExit("out-dir exists and is not a directory")
        if any(out_dir.iterdir()):
            raise SystemExit("out-dir must be empty")
    else:
        out_dir.mkdir(parents=True)

    if args.repository != CURRENT_REPOSITORY:
        raise SystemExit(f"repository must be {CURRENT_REPOSITORY}")

    env = os.environ.copy()
    env["EXTRA_CPPFLAGS"] = f"-DHS_SOURCE_COMMIT=\\\"{args.release_commit}\\\""
    run(["make", "clean"], env=env)
    run(["make", "estimator_exact"], env=env)

    shutil.copy2(ROOT / "estimator_exact", out_dir / "estimator_exact")
    shutil.copy2(ROOT / "submit.txt", out_dir / "submit.txt")
    run(
        [
            "python3",
            "-X",
            "utf8",
            str(ROOT / "scripts" / "generate_package_source_commit.py"),
            "--repository",
            args.repository,
            "--release-ref",
            args.release_ref,
            "--release-commit",
            args.release_commit,
            "--submit-source-commit",
            args.submit_source_commit,
            "--submit-sha256",
            args.submit_sha256,
            "--out",
            str(out_dir / "PACKAGE_SOURCE_COMMIT.txt"),
            *(
                ["--package-generated-at-utc", args.package_generated_at_utc]
                if args.package_generated_at_utc
                else []
            ),
        ],
        env=env,
    )
    shutil.copy2(ROOT / "PACKAGE_SOURCE_COMMIT.template", out_dir / "PACKAGE_SOURCE_COMMIT.template")

    verify_staged_binary(out_dir, args.release_commit)

    manifest = {
        "schema": "release-package-staging-v1",
        "repository": args.repository,
        "release_ref": args.release_ref,
        "release_commit": args.release_commit,
        "package_generated_at_utc": parse_metadata(out_dir / "PACKAGE_SOURCE_COMMIT.txt")[
            "package_generated_at_utc"
        ],
        "submit_source_commit": args.submit_source_commit,
        "submit_sha256": args.submit_sha256,
        "files": {
            "estimator_exact": sha256_file(out_dir / "estimator_exact"),
            "submit.txt": sha256_file(out_dir / "submit.txt"),
            "PACKAGE_SOURCE_COMMIT.template": sha256_file(out_dir / "PACKAGE_SOURCE_COMMIT.template"),
            "PACKAGE_SOURCE_COMMIT.txt": sha256_file(out_dir / "PACKAGE_SOURCE_COMMIT.txt"),
        },
    }
    (out_dir / "RELEASE_STAGING_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
