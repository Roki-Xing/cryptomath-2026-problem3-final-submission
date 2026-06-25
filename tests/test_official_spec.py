#!/usr/bin/env python3
"""Lint official-spec claim classification and evidence boundaries."""

from __future__ import annotations

import re
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/OFFICIAL_SPEC_INTERPRETATION.md"
VT_VE = ROOT / "docs/VT_VE_COMPLIANCE.md"
OFFICIAL_SOURCES = ROOT / "references/official/SOURCES.json"
PAGE_MAP = ROOT / "references/official/PAGE_MAP.json"

HEADINGS = [
    "OFFICIAL_EXPLICIT",
    "CONSERVATIVE_INTERPRETATION",
    "UNRESOLVED",
]

REQUIRED_IDS = {
    "OFFICIAL_EXPLICIT-FIVE-FIELDS",
    "OFFICIAL_EXPLICIT-NEGATIVE-INTERVAL",
    "OFFICIAL_EXPLICIT-HEX-MASKS",
    "OFFICIAL_EXPLICIT-COMPLEXITY",
    "OFFICIAL_EXPLICIT-APPROXIMATE-THEN-VERIFY",
    "CONSERVATIVE_INTERPRETATION-DECIMAL-MASKS",
    "CONSERVATIVE_INTERPRETATION-UNIQUENESS-REPORTING",
    "CONSERVATIVE_INTERPRETATION-GENERIC-ROUNDS",
    "UNRESOLVED-VT-PROVENANCE",
    "UNRESOLVED-DEDUP-KEY",
    "UNRESOLVED-COMPLEXITY-UNIT",
}


def classified_sections(text: str) -> dict[str, str]:
    """Extract the three machine-readable claim sections."""
    sections: dict[str, str] = {}
    for index, heading in enumerate(HEADINGS):
        start_marker = f"## {heading}\n"
        assert text.count(start_marker) == 1
        start = text.index(start_marker) + len(start_marker)
        if index + 1 < len(HEADINGS):
            end = text.index(f"## {HEADINGS[index + 1]}\n", start)
        else:
            end = len(text)
        sections[heading] = text[start:end]
    return sections


def main() -> int:
    text = SPEC.read_text(encoding="utf-8")
    assert "## Officially Confirmed" not in text
    assert "## Conservative Repository Interpretations" not in text
    assert "## Not Yet Established by the Official Material" not in text

    sections = classified_sections(text)
    claim_ids: list[str] = []
    for heading, section in sections.items():
        bullet_lines = [line for line in section.splitlines() if line.startswith("- ")]
        assert bullet_lines
        for line in bullet_lines:
            match = re.match(r"- \*\*`([A-Z0-9_-]+)`\*\*:", line)
            assert match, f"unclassified claim bullet under {heading}: {line}"
            claim_id = match.group(1)
            assert claim_id.startswith(f"{heading}-")
            claim_ids.append(claim_id)

    assert len(claim_ids) == len(set(claim_ids))
    assert REQUIRED_IDS.issubset(claim_ids)

    assert "complexity must be strictly lower than way-1" in text
    assert "`r=0` is an internal identity-map test only" in text
    assert "does not imply no-truncation, exact certification" in text
    assert "Structured source registry: `references/official/SOURCES.json`." in text
    assert "Structured page map: `references/official/PAGE_MAP.json`." in text
    assert "`public_announcement_or_mirror`" in text
    assert "an exact certified way-2 value can replace an actually executed way-1 `VT`" in text

    assert OFFICIAL_SOURCES.exists()
    sources = json.loads(OFFICIAL_SOURCES.read_text(encoding="utf-8"))
    assert sources["schema"] == "official-reference-sources-v2"
    source_ids = {entry["document_id"] for entry in sources["sources"]}
    assert {
        "official-homepage",
        "official-download-page",
        "challenge-public-announcement",
        "challenge-zip",
        "challenge-pdf",
        "official-computecor",
        "analysis-pdf",
    }.issubset(source_ids)
    analysis = next(entry for entry in sources["sources"] if entry["document_id"] == "analysis-pdf")
    assert analysis["redistribution"] == "not_included"
    assert analysis["page_count"] == 19
    assert analysis["sha256"] == "0077a138c2288d75c8384f937d92b1ca2ebb4cd860d86852a64317db14653016"

    assert PAGE_MAP.exists()
    page_map = json.loads(PAGE_MAP.read_text(encoding="utf-8"))
    assert page_map["schema"] == "official-page-map-v1"
    pages = {entry["page"] for entry in page_map["pages"]}
    assert {12, 13, 14, 16, 17, 18} == pages

    vt_text = VT_VE.read_text(encoding="utf-8")
    assert "`docs/OFFICIAL_SPEC_INTERPRETATION.md` is the canonical authority" in vt_text
    assert "numerical fact" in vt_text
    assert "Strategy B remains the formal low-risk target" in vt_text

    print("official specification lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
