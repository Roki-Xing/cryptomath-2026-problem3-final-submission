#!/usr/bin/env python3
"""Generate strict release-staging package source metadata."""

from __future__ import annotations

import argparse
import os
import re
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = "package-source-metadata-v1"
CURRENT_REPOSITORY = "Roki-Xing/cryptomath-2026-problem3-final-submission"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def require_commit(value: str, field: str) -> str:
    lowered = value.strip().lower()
    if not COMMIT_RE.fullmatch(lowered):
        raise SystemExit(f"{field} must be a 40- or 64-hex commit/hash")
    return lowered


def require_sha256(value: str, field: str) -> str:
    lowered = value.strip().lower()
    if not SHA256_RE.fullmatch(lowered):
        raise SystemExit(f"{field} must be a 64-hex SHA-256 digest")
    return lowered


def require_rfc3339_utc(value: str, field: str) -> str:
    value = value.strip()
    if not RFC3339_UTC_RE.fullmatch(value):
        raise SystemExit(f"{field} must be RFC3339 UTC like 2026-06-25T00:00:00Z")
    return value


def resolve_generated_at(explicit: str | None) -> str:
    if explicit:
        return require_rfc3339_utc(explicit, "package_generated_at_utc")
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if not epoch:
        raise SystemExit("package_generated_at_utc must be provided or SOURCE_DATE_EPOCH must be set")
    try:
        timestamp = int(epoch)
    except ValueError as exc:
        raise SystemExit("SOURCE_DATE_EPOCH must be an integer") from exc
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--release-ref", required=True)
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--package-generated-at-utc")
    parser.add_argument("--submit-source-commit", required=True)
    parser.add_argument("--submit-sha256", required=True)
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repository = args.repository.strip()
    if repository != CURRENT_REPOSITORY:
        raise SystemExit(f"repository must be exactly {CURRENT_REPOSITORY}")

    release_ref = args.release_ref.strip()
    if not release_ref:
        raise SystemExit("release_ref must be non-empty")

    release_commit = require_commit(args.release_commit, "release_commit")
    generated_at = resolve_generated_at(args.package_generated_at_utc)
    submit_source_commit = require_commit(args.submit_source_commit, "submit_source_commit")
    submit_sha256 = require_sha256(args.submit_sha256, "submit_sha256")

    output = "\n".join(
        [
            f"schema: {SCHEMA}",
            f"repository: {repository}",
            f"release_ref: {release_ref}",
            f"release_commit: {release_commit}",
            f"package_generated_at_utc: {generated_at}",
            f"submit_source_commit: {submit_source_commit}",
            f"submit_sha256: {submit_sha256}",
            "",
        ]
    )
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()
