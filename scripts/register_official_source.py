#!/usr/bin/env python3
"""Register a verified local official source artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def page_count(path: Path) -> int | None:
    if path.suffix.lower() != ".pdf":
        return None
    output = subprocess.check_output(["pdfinfo", str(path)], text=True)
    for line in output.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    raise SystemExit(f"could not determine page count for {path}")


def resolve_retrieved_at(explicit: str | None) -> str:
    if explicit:
        return explicit
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if not epoch:
        raise SystemExit("retrieved_at_utc must be provided or SOURCE_DATE_EPOCH must be set")
    return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--document-title", required=True)
    parser.add_argument("--source-type", required=True)
    parser.add_argument("--source-page-url", required=True)
    parser.add_argument("--direct-download-url")
    parser.add_argument("--local-path", required=True)
    parser.add_argument("--retrieved-at-utc")
    parser.add_argument("--redistribution", required=True)
    parser.add_argument("--verification-status", required=True)
    parser.add_argument("--verified-filename")
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    local_path = Path(args.local_path)
    if not local_path.exists() or not local_path.is_file():
        raise SystemExit(f"local verified source is missing: {local_path}")

    record = {
        "document_id": args.document_id,
        "document_title": args.document_title,
        "source_type": args.source_type,
        "source_page_url": args.source_page_url,
        "direct_download_url": args.direct_download_url,
        "verified_filename": args.verified_filename or local_path.name,
        "sha256": sha256_file(local_path),
        "page_count": page_count(local_path),
        "retrieved_at_utc": resolve_retrieved_at(args.retrieved_at_utc),
        "redistribution": args.redistribution,
        "verification_status": args.verification_status,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
