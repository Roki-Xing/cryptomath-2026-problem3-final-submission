#!/usr/bin/env python3
"""Validate the Stage-A compact package builder."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_stage_a_compact_package.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_stage_a_compact_package", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hash_tree(root: Path) -> dict[str, str]:
    items: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        items[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return items


def count_raw_files() -> dict[str, int]:
    counts: dict[str, int] = {}
    for relative in (
        "bench/way1/stage_a0",
        "bench/way1/stage_a1",
        "bench/way1/stage_a2",
        "bench/way1/stage_toolchain",
    ):
        counts[relative] = sum(1 for path in (ROOT / relative).rglob("*") if path.is_file())
    return counts


def main() -> None:
    module = load_module()
    assert module.ALLOWLIST_VERSION == "stage-a-compact-allowlist-v1"
    assert set(module.REQUIRED_SUMMARY).issubset(set(module.ALLOWLIST))
    assert set(module.REQUIRED_MANIFEST).issubset(set(module.ALLOWLIST))

    raw_before = count_raw_files()
    with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
        out1 = Path(tmp1) / "compact1"
        out2 = Path(tmp2) / "compact2"

        module.build_package(out1)
        raw_after_first = count_raw_files()
        assert raw_after_first == raw_before

        for relative in module.REQUIRED_SUMMARY:
            assert (out1 / relative).is_file(), relative
        for relative in module.REQUIRED_MANIFEST:
            assert (out1 / relative).is_file(), relative

        forbidden_names = ("results.csv", "forecast.json")
        for name in forbidden_names:
            assert not any(path.name == name for path in out1.rglob(name))
        assert not any("__pycache__" in path.parts for path in out1.rglob("*"))
        assert not any(path.suffix == ".time" for path in out1.rglob("*"))
        assert not any(path.name.endswith(".stderr") for path in out1.rglob("*"))
        assert not any("compile" in path.parts for path in out1.rglob("*"))

        sha_check = subprocess.run(
            ["sha256sum", "-c", "STAGE_A_COMPACT_SHA256SUMS.txt"],
            cwd=out1,
            check=False,
            capture_output=True,
            text=True,
        )
        assert sha_check.returncode == 0, sha_check.stderr + sha_check.stdout

        manifest = json.loads((out1 / module.GENERATED_MANIFEST).read_text(encoding="utf-8"))
        assert manifest["file_count"] == len(module.ALLOWLIST)
        assert len(manifest["files"]) == len(module.ALLOWLIST)
        actual_payload = sorted(
            path.relative_to(out1).as_posix()
            for path in out1.rglob("*")
            if path.is_file()
            and path.name not in {module.GENERATED_MANIFEST, module.GENERATED_SHA}
        )
        manifest_payload = sorted(item["path"] for item in manifest["files"])
        assert actual_payload == manifest_payload

        nonempty = Path(tmp1) / "nonempty"
        nonempty.mkdir()
        (nonempty / "placeholder.txt").write_text("x", encoding="utf-8")
        try:
            module.build_package(nonempty)
        except RuntimeError:
            pass
        else:
            raise AssertionError("non-empty target directory should fail")

        module.build_package(out2)
        raw_after_second = count_raw_files()
        assert raw_after_second == raw_before

        assert hash_tree(out1) == hash_tree(out2)

    print("stage-a compact package tests passed")


if __name__ == "__main__":
    main()
