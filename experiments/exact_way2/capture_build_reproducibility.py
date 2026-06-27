#!/usr/bin/env python3
"""Capture a clean-worktree reproducible build record for recompute_frozen_exact."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

from common import (
    BUILD_REPRODUCIBILITY_SCHEMA,
    EMPTY_SHA256,
    current_source_commit,
    current_source_tree_sha,
    now_utc_microseconds,
    sha256_file,
    sha256_path_list,
    write_json,
)


OBJECT_RE = re.compile(r"(?:^|\s)-o\s+(build/[^\s]+\.o)(?:\s|$)")
LINK_RE = re.compile(r"(?:^|\s)-o\s+recompute_frozen_exact(?:\s|$)")


def read_first_line(args: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(args, cwd=cwd, text=True).splitlines()[0].strip()


def env_subset() -> dict[str, str]:
    keys = ["PATH", "CPATH", "CPLUS_INCLUDE_PATH", "CPPFLAGS", "CXXFLAGS", "CXX"]
    return {key: os.environ.get(key, "") for key in keys}


def locate_boost_root() -> Path | None:
    include_path = os.environ.get("CPLUS_INCLUDE_PATH", "")
    for entry in include_path.split(":"):
        if not entry:
            continue
        candidate = Path(entry)
        version_hpp = candidate / "boost" / "version.hpp"
        if version_hpp.exists():
            return candidate
    for candidate in (Path("/usr/include"), Path("/usr/local/include")):
        version_hpp = candidate / "boost" / "version.hpp"
        if version_hpp.exists():
            return candidate
    return None


def boost_inventory(boost_root: Path | None) -> dict[str, object]:
    if boost_root is None:
        return {
            "boost_root": "",
            "boost_version_header_sha256": "",
            "boost_inventory_sha256": "",
            "boost_version_macro": "",
        }
    version_hpp = boost_root / "boost" / "version.hpp"
    version_line = ""
    for line in version_hpp.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("#define BOOST_LIB_VERSION "):
            version_line = line.split()[-1].strip('"')
            break
    headers = sorted((boost_root / "boost").rglob("*.hpp"))
    return {
        "boost_root": str(boost_root),
        "boost_version_header_sha256": sha256_file(version_hpp),
        "boost_inventory_sha256": sha256_path_list(headers) if headers else "",
        "boost_version_macro": version_line,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    root = Path.cwd()
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=root, text=True
    )
    if status:
        raise SystemExit("capture_build_reproducibility.py requires a clean committed worktree")
    build_start = now_utc_microseconds()
    compiler = shutil.which(os.environ.get("CXX", "g++"))
    if compiler is None:
        raise SystemExit("cannot resolve compiler")
    compiler_path = str(Path(compiler).resolve())
    compiler_version = read_first_line([compiler_path, "--version"], cwd=root)
    source_commit = current_source_commit(cwd=root)
    source_tree_sha = current_source_tree_sha(cwd=root)
    subprocess.run(["make", "clean"], cwd=root, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    planned = subprocess.run(
        ["make", "-n", "recompute_frozen_exact"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    build = subprocess.run(
        ["make", "recompute_frozen_exact"],
        cwd=root,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    build_end = now_utc_microseconds()
    commands = [line for line in planned.stdout.splitlines() if line.strip()]
    object_records = []
    link_command = ""
    for line in commands:
        match = OBJECT_RE.search(line)
        if match:
            object_path = root / match.group(1)
            object_records.append(
                {
                    "path": match.group(1),
                    "sha256": sha256_file(object_path),
                    "command": line.strip(),
                }
            )
        if LINK_RE.search(line):
            link_command = line.strip()
    if not object_records:
        raise SystemExit("failed to capture object build commands from make -n recompute_frozen_exact")
    if not link_command:
        raise SystemExit("failed to capture link command from make -n recompute_frozen_exact")
    binary_path = root / "recompute_frozen_exact"
    payload = {
        "schema": BUILD_REPRODUCIBILITY_SCHEMA,
        "source_checkout_commit": source_commit,
        "source_tree_sha": source_tree_sha,
        "git_status_porcelain_sha256": EMPTY_SHA256,
        "source_tree_diff_sha256": EMPTY_SHA256,
        "compiler_path": compiler_path,
        "compiler_version": compiler_version,
        "environment": env_subset(),
        **boost_inventory(locate_boost_root()),
        "make_clean_command": "make clean",
        "build_command": "make recompute_frozen_exact",
        "build_started_at_utc": build_start,
        "build_finished_at_utc": build_end,
        "objects": object_records,
        "link_command": link_command,
        "binary_sha256": sha256_file(binary_path),
    }
    write_json(Path(args.out), payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
