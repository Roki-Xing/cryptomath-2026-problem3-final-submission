#!/usr/bin/env python3
"""Regression checks for final package hardening boundaries."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = ROOT / "submission_final"
PACKAGE_SOURCE = PACKAGE_ROOT / "source"
PACKAGE_EXPERIMENTS = PACKAGE_SOURCE / "experiments"
ROOT_CHECKER = ROOT / "experiments" / "check_submission_package.py"
TEXT_FIELDS = [
    "certified_no_truncation",
    "round_stats",
    "branch_truncated_states",
    "tuple_truncated_states",
    "beam_pruned",
]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def root_sha_entries() -> set[str]:
    entries: set[str] = set()
    for line in (ROOT / "SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        _, path = line.split("  ", 1)
        entries.add(path)
    return entries


def load_checker_module():
    spec = importlib.util.spec_from_file_location("check_submission_package", ROOT_CHECKER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def build_fixture(tmp_path: Path) -> tuple[Path, Path]:
    package_root = tmp_path / "submission_final"
    source_root = package_root / "source"
    experiments_root = source_root / "experiments"
    include_root = source_root / "include"
    src_root = source_root / "src"
    apps_root = source_root / "apps"
    for directory in [experiments_root, include_root, src_root, apps_root]:
        directory.mkdir(parents=True, exist_ok=True)

    submit_path = package_root / "submit.txt"
    submit_payload = "@(1, 0x00000001, 0x00000010, 0.5, 0.5)\n"
    submit_path.write_text(submit_payload, encoding="utf-8")

    rows_path = experiments_root / "r2_fixture.csv"
    rows_path.write_text("u,v,vt,ve\n0x00000001,0x00000010,0.5,0.5\n", encoding="utf-8")
    rows_sha = hashlib.sha256(rows_path.read_bytes()).hexdigest()

    manifest_path = experiments_root / "SOURCE_MANIFEST.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "path",
                "round",
                "active_nibbles",
                "generation_command",
                "beam",
                "trans",
                "branch",
                "certified_only",
                "row_count",
                "sha256",
                "used_in_final_submit",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "path": "experiments/r2_fixture.csv",
                "round": "2",
                "active_nibbles": "1",
                "generation_command": "saved_certified_source_csv",
                "beam": "",
                "trans": "",
                "branch": "",
                "certified_only": "1",
                "row_count": "1",
                "sha256": rows_sha,
                "used_in_final_submit": "1",
            }
        )

    build_script = experiments_root / "build_submit_from_sources.py"
    write_executable(
        build_script,
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            import argparse
            from pathlib import Path

            parser = argparse.ArgumentParser()
            parser.add_argument("--source-submit", required=True)
            parser.add_argument("--out", required=True)
            args = parser.parse_args()
            Path(args.out).write_bytes(Path(args.source_submit).read_bytes())
            """
        ),
    )

    score_script = source_root / "score"
    write_executable(
        score_script,
        textwrap.dedent(
            """\
            #!/usr/bin/env python3
            print("valid_count=138338")
            print("total_score=105843.622442471292742994")
            """
        ),
    )

    for rel in [
        "Makefile",
        "include/sbox_corr.hpp",
        "include/beam_search.hpp",
        "include/exact.hpp",
        "include/exact_dyadic.hpp",
        "src/sbox_corr.cpp",
        "src/beam_search.cpp",
        "src/exact.cpp",
        "src/exact_cartesian.cpp",
        "src/exact_dyadic.cpp",
        "src/linear_layer.cpp",
        "apps/estimator.cpp",
        "apps/estimator_exact.cpp",
        "apps/enumerate_r1_positive.cpp",
        "apps/exact_batch_current.cpp",
        "apps/exact_batch_grouped_u.cpp",
        "apps/exact_batch_grouped_uv.cpp",
        "apps/exact_batch_mt.cpp",
        "apps/exact_batch_variant_app.hpp",
        "apps/exact_oracle.cpp",
        "apps/recompute_frozen_exact.cpp",
        "apps/reduce_exact_parts.cpp",
        "apps/score.cpp",
    ]:
        target = source_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("// fixture\n", encoding="utf-8")

    return package_root, source_root


def test_package_checker_fixture() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        package_root, source_root = build_fixture(Path(tmp))
        submit_sha = hashlib.sha256((package_root / "submit.txt").read_bytes()).hexdigest()
        subprocess.run(
            [
                sys.executable,
                str(ROOT_CHECKER),
                "--submit",
                str(package_root / "submit.txt"),
                "--expected-submit-sha256",
                submit_sha,
                "--expected-valid-count",
                "138338",
                "--expected-total-score",
                "105843.622442471292742994",
            ],
            cwd=source_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        manifest_path = source_root / "experiments" / "SOURCE_MANIFEST.csv"
        text = manifest_path.read_text(encoding="utf-8")
        manifest_path.write_text(
            text.replace(rows_sha := hashlib.sha256((source_root / "experiments" / "r2_fixture.csv").read_bytes()).hexdigest(), "0" * 64, 1),
            encoding="utf-8",
        )
        broken = subprocess.run(
            [
                sys.executable,
                str(ROOT_CHECKER),
                "--submit",
                str(package_root / "submit.txt"),
                "--expected-submit-sha256",
                submit_sha,
                "--expected-valid-count",
                "138338",
                "--expected-total-score",
                "105843.622442471292742994",
            ],
            cwd=source_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        require(broken.returncode != 0, "package checker accepted a tampered manifest")


def test_committed_package_boundary() -> None:
    require(ROOT_CHECKER.is_file(), "root package-safe checker is missing")
    require(
        (PACKAGE_EXPERIMENTS / "check_submission_package.py").is_file(),
        "package-safe checker is missing from submission_final/source",
    )
    require(
        not (PACKAGE_EXPERIMENTS / "check_submission.py").exists(),
        "broken repository-level checker is still shipped in the final package",
    )
    for path in [
        ROOT / "PACKAGE_MANIFEST.md",
        ROOT / "SUBMISSION_MANIFEST.md",
        ROOT / "docs" / "REPRODUCIBILITY.md",
        PACKAGE_ROOT / "README_FIRST.md",
        PACKAGE_ROOT / "docs" / "SUBMISSION_MANIFEST.md",
    ]:
        text = path.read_text(encoding="utf-8")
        require("check_submission_package.py" in text, f"package-safe checker command missing in {path}")
    boundary_text = (ROOT / "SUBMISSION_MANIFEST.md").read_text(encoding="utf-8")
    require("历史候选发现标签" in boundary_text, "SOURCE_MANIFEST boundary note missing from submission manifest")


def test_paper_field_mapping_moved_to_appendix() -> None:
    tex = (ROOT / "参赛论文" / "参赛论文_赛题三_稳稳接住.tex").read_text(encoding="utf-8")
    tex_main, _, tex_appendix = tex.partition("\\section*{附录 I\\quad 评测实例与输出格式}")
    require(tex_appendix, "TeX appendix boundary not found")
    for field in TEXT_FIELDS:
        require(field not in tex_main, f"engineering field leaked into TeX main body: {field}")
        tex_field = field.replace("_", "\\_")
        require(tex_field in tex_appendix, f"engineering field mapping missing from TeX appendix: {field}")

    report = (ROOT / "REPORT.md").read_text(encoding="utf-8")
    report_main, _, report_appendix = report.partition("## 附录 A. 评测实例与输出格式")
    require(report_appendix, "REPORT appendix boundary not found")
    for field in TEXT_FIELDS:
        require(field not in report_main, f"engineering field leaked into REPORT main body: {field}")
        require(field in report_appendix, f"engineering field mapping missing from REPORT appendix: {field}")


def test_root_sha_manifest_covers_tracked_files() -> None:
    tracked = subprocess.check_output(
        ["git", "-c", "core.quotePath=false", "ls-files", "-z"],
        cwd=ROOT,
        text=True,
    ).split("\0")
    expected = {
        path
        for path in tracked
        if path and path != "SHA256SUMS.txt" and (ROOT / path).is_file()
    }
    entries = root_sha_entries()
    require(
        entries == expected,
        "root SHA256SUMS.txt does not exactly cover tracked files",
    )
    require(
        "submission_final/source/experiments/check_submission_package.py" in entries,
        "root SHA256SUMS.txt is missing the package-safe checker",
    )


def main() -> int:
    test_package_checker_fixture()
    test_committed_package_boundary()
    test_paper_field_mapping_moved_to_appendix()
    test_root_sha_manifest_covers_tracked_files()
    print("final package hardening tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
