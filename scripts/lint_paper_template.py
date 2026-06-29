#!/usr/bin/env python3
"""Lint paper/template compliance text without touching numerical artifacts.

Args:
    paths: Files or directories to scan.

Returns:
    Exit code 0 when no blocking issue is found; 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


TEXT_SUFFIXES = {".md", ".tex", ".txt", ".json", ".csv"}

BLOCKING_PATTERNS = [
    ("placeholder", re.compile(r"待补充|提交前填写|提交前可替换")),
    ("bad-citation-token", re.compile(r"contentReference|oaicite")),
    ("unsafe-vt-ve", re.compile(r"can safely set VT=VE|setting VT=VE|set VT=VE|直接令\s*VT=VE")),
    ("bad-latex-rule", re.compile(r"===========|#\s*\\sum|\(\(r,u\)\)|\(\(r,u,v\)\)")),
    ("bad-display-open", re.compile(r"^\[$", re.MULTILINE)),
    ("bad-display-close", re.compile(r"^\]$", re.MULTILINE)),
    ("false-way1-closed", re.compile(r"全量 way-1 VT provenance 已闭合|当前 VT 字段已由 way-1 全量生成")),
    ("false-strategy-b", re.compile(r"Strategy-B final file 已生成|Stage-B 已启动|full 2\^32 已完成")),
    ("false-official", re.compile(r"官方已明确允许 exact-way2 替代 way-1 VT")),
]

OLD_NUMBER = re.compile(r"137954|105236|4754")
SAFE_OLD_CONTEXT = re.compile(r"historical|superseded|pre-E06|历史|已取代|旧")
FULLWIDTH_PUNCT = re.compile(r"[，。；：！？（）【】《》]")
FENCED_CODE = re.compile(r"```.*?```", re.DOTALL)


def iter_files(paths: list[Path]) -> list[Path]:
    """Return deterministic text files under the requested paths."""

    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and child.suffix in TEXT_SUFFIXES:
                    found.append(child)
        elif path.is_file():
            found.append(path)
        else:
            print(f"ERROR missing path: {path}", file=sys.stderr)
            raise SystemExit(1)
    return sorted(set(found), key=lambda p: p.as_posix())


def line_for_offset(text: str, offset: int) -> int:
    """Convert byte-independent character offset to one-based line number."""

    return text.count("\n", 0, offset) + 1


def lint_file(path: Path) -> tuple[list[str], list[str]]:
    """Lint a single UTF-8 text file."""

    text = path.read_text(encoding="utf-8")
    text_without_fences = FENCED_CODE.sub(
        lambda match: "\n" * match.group(0).count("\n"),
        text,
    )
    errors: list[str] = []
    warnings: list[str] = []

    for label, pattern in BLOCKING_PATTERNS:
        scan_text = text_without_fences if label in {"bad-display-open", "bad-display-close"} else text
        for match in pattern.finditer(scan_text):
            errors.append(f"{path}:{line_for_offset(text, match.start())}: {label}: {match.group(0)}")

    for match in OLD_NUMBER.finditer(text):
        start = max(0, match.start() - 80)
        end = min(len(text), match.end() + 80)
        context = text[start:end]
        if not SAFE_OLD_CONTEXT.search(context):
            errors.append(f"{path}:{line_for_offset(text, match.start())}: stale-current-number: {match.group(0)}")

    punct_hits = list(FULLWIDTH_PUNCT.finditer(text))
    if punct_hits:
        samples = ", ".join(
            f"{m.group(0)}@{line_for_offset(text, m.start())}" for m in punct_hits[:8]
        )
        warnings.append(
            f"{path}: fullwidth punctuation warning ({len(punct_hits)} hits; samples: {samples})"
        )

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    for path in iter_files(args.paths):
        file_errors, file_warnings = lint_file(path)
        errors.extend(file_errors)
        warnings.extend(file_warnings)

    for warning in warnings:
        print(f"WARNING {warning}")
    for error in errors:
        print(f"ERROR {error}")

    if errors:
        print(f"paper template lint failed: errors={len(errors)} warnings={len(warnings)}")
        return 1
    print(f"paper template lint passed: warnings={len(warnings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
