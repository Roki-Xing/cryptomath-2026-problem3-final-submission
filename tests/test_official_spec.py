#!/usr/bin/env python3
"""Lint official-spec claim classification and evidence boundaries."""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/OFFICIAL_SPEC_INTERPRETATION.md"
VT_VE = ROOT / "docs/VT_VE_COMPLIANCE.md"
OFFICIAL_SOURCES = ROOT / "references/official/SOURCES.json"

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

    assert "Way 2 must have complexity strictly lower than way 1." in text
    assert "0x000ee0f0" in text and "0x08088880" in text
    assert "parsing-only" in text
    assert "does not assert that `0.5` is the true correlation" in text
    assert "`r=0` is an internal identity-map test only" in text
    assert (
        "Interface applicability for arbitrary `r` does not imply no-truncation, "
        "exact certification, acceptable accuracy, or lower measured cost for every `r`."
    ) in text
    assert "Source index: `references/official/SOURCES.json`." in text
    assert "Source file: official analysis PDF not checked into this repository." in text
    assert "Redistribution status: not included" in text
    assert "page 12" in text and "page 14" in text and "page 16/17" in text and "page 18" in text

    assert OFFICIAL_SOURCES.exists()
    sources = OFFICIAL_SOURCES.read_text(encoding="utf-8")
    assert "https://www.cmathc.org.cn/mcm/st/434.html" in sources
    assert '"redistribution": "not_included"' in sources
    for page in [12, 14, 16, 17, 18]:
        assert f'"page": {page}' in sources

    vt_text = VT_VE.read_text(encoding="utf-8")
    assert "`docs/OFFICIAL_SPEC_INTERPRETATION.md` is the canonical authority" in vt_text

    print("official specification lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
