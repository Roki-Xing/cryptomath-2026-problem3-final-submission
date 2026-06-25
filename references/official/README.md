# Official Source Boundary

This directory stores structured provenance for the official public materials
referenced by `docs/OFFICIAL_SPEC_INTERPRETATION.md`.

Included in the repository:

- `SOURCES.json`: structured source registry with URLs, verified local
  filenames, SHA-256 digests, page counts, retrieval timestamps, and
  redistribution status.
- `PAGE_MAP.json`: the repository's verified page-to-claim mapping.

Not included in the repository by default:

- official PDF files whose redistribution basis has not been established;
- local mirrors or downloaded ZIP files.

Current policy:

- official challenge and analysis PDFs are recorded as
  `redistribution = "not_included"`;
- `computecor.cpp` is referenced through the official challenge ZIP metadata;
- `cmathc.org.cn` is treated as `public_announcement_or_mirror`;
- `cmsecc.com` is treated as the official challenge host because the public
  announcement page explicitly points to `www.cmsecc.com` as the official site.

To refresh metadata, use verified local files and regenerate `SOURCES.json`
with `scripts/register_official_source.py`. Do not invent SHA-256 values,
page counts, or retrieval timestamps.
