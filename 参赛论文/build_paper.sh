#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

tex="参赛论文_赛题三_稳稳接住.tex"
pdf="参赛论文_赛题三_稳稳接住.pdf"
command1="latexmk -xelatex -interaction=nonstopmode -halt-on-error ${tex}"
command2="latexmk -xelatex -interaction=nonstopmode -halt-on-error ${tex}"
start_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

latexmk -C "${tex}" >/tmp/paper_latexmk_clean.log
${command1}
${command2}

end_utc="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
tex_sha="$(sha256sum "${tex}" | awk '{print $1}')"
pdf_sha="$(sha256sum "${pdf}" | awk '{print $1}')"
xelatex_version="$(xelatex --version | head -n 1)"
latexmk_version="$(latexmk --version | head -n 1)"

python3 -X utf8 - <<PY
import json
from pathlib import Path

data = {
    "schema": "paper-build-info-v1",
    "tex": "${tex}",
    "pdf": "${pdf}",
    "tex_sha256": "${tex_sha}",
    "pdf_sha256": "${pdf_sha}",
    "build_commands": ["${command1}", "${command2}"],
    "build_start_utc": "${start_utc}",
    "build_end_utc": "${end_utc}",
    "xelatex_version": ${xelatex_version@Q},
    "latexmk_version": ${latexmk_version@Q},
}
Path("PAPER_BUILD_INFO.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\\n",
    encoding="utf-8",
)
PY

printf 'tex_sha256=%s\n' "${tex_sha}"
printf 'pdf_sha256=%s\n' "${pdf_sha}"
