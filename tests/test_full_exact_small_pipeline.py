import csv
import json
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKE_ENV = {
    **os.environ,
    "CPLUS_INCLUDE_PATH": "/tmp/boost-headers/usr/include",
    "EXTRA_CPPFLAGS": "-I/tmp/boost-headers/usr/include",
    "PYTHONDONTWRITEBYTECODE": "1",
}


@contextmanager
def clean_worktree():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory() as tmpdir:
        worktree = Path(tmpdir) / "worktree"
        subprocess.run(["git", "worktree", "add", "--detach", str(worktree), head], cwd=ROOT, check=True)
        try:
            subprocess.run(
                ["rsync", "-a", "--delete", "--exclude=.git", f"{ROOT}/", str(worktree)],
                check=True,
                env=MAKE_ENV,
            )
            subprocess.run(["git", "config", "user.name", "Codex Test"], cwd=worktree, check=True)
            subprocess.run(["git", "config", "user.email", "codex@example.invalid"], cwd=worktree, check=True)
            subprocess.run(["git", "add", "-A"], cwd=worktree, check=True)
            subprocess.run(["git", "commit", "-m", "temp full exact snapshot"], cwd=worktree, check=True, env=MAKE_ENV)
            yield worktree
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, check=True)


def run(worktree: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*args],
        cwd=worktree,
        env=MAKE_ENV,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )


def file_sha256(path: Path) -> str:
    return subprocess.check_output(["sha256sum", str(path)], text=True).split()[0]


def expect_missing_zstandard_message(worktree: Path, artifact_root: Path, archive_root: Path) -> None:
    blocker_root = artifact_root.parent / "block-zstd"
    blocker_root.mkdir(parents=True, exist_ok=True)
    (blocker_root / "zstandard.py").write_text("raise ModuleNotFoundError('blocked by test')\n", encoding="utf-8")
    env = dict(MAKE_ENV)
    env["PYTHONPATH"] = str(blocker_root)
    failed = subprocess.run(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/archive_full_evidence.py",
            "--artifact-root",
            str(artifact_root),
            "--archive-root",
            str(archive_root),
        ],
        cwd=worktree,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert failed.returncode != 0
    assert "missing python dependency 'zstandard'" in (failed.stderr + failed.stdout).lower()


def main() -> None:
    with clean_worktree() as worktree, tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        subprocess.run(["make", "recompute_frozen_exact"], cwd=worktree, check=True, env=MAKE_ENV)
        binary = tmp / "recompute_frozen_exact"
        shutil.copy2(worktree / "recompute_frozen_exact", binary)
        subprocess.run(["git", "clean", "-fdx"], cwd=worktree, check=True)

        selection_root = tmp / "selection"
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/select_full.py",
            "--final-ru",
            "experiments/frozen/final_ru.csv",
            "--final-queries",
            "experiments/frozen/final_queries.csv",
            "--out",
            str(selection_root),
        )
        with (selection_root / "FULL_SELECTION.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = [next(reader), next(reader)]
        tiny_csv = tmp / "FULL_SELECTION.csv"
        with tiny_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        full_json = json.loads((selection_root / "FULL_SELECTION.json").read_text(encoding="utf-8"))
        full_json["selected_columns"] = 2
        full_json["round_distribution"] = {
            "r1": sum(int(row["r"]) == 1 for row in rows),
            "r2": sum(int(row["r"]) == 2 for row in rows),
            "r3": sum(int(row["r"]) == 3 for row in rows),
        }
        full_json["selection"] = rows
        full_json["selection_payload_sha256"] = file_sha256(tiny_csv)
        (tmp / "FULL_SELECTION.json").write_text(json.dumps(full_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        artifact_root = tmp / "full"
        artifact_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tiny_csv, artifact_root / "FULL_SELECTION.csv")
        shutil.copy2(tmp / "FULL_SELECTION.json", artifact_root / "FULL_SELECTION.json")

        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=worktree, text=True).strip()
        tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=worktree, text=True).strip()
        auth = {
            "schema": "exact-way2-full-authorization-v1",
            "authorized": True,
            "authorized_by": "test",
            "authorized_at_utc": "2026-06-27T00:00:00Z",
            "source_commit": commit,
            "source_tree_sha": tree,
            "source_tree_dirty": False,
            "binary_sha256": file_sha256(binary),
            "build_command": "make recompute_frozen_exact",
            "compiler_path": "/usr/bin/g++",
            "compiler_version": "g++",
            "final_ru_sha256": file_sha256(worktree / "experiments/frozen/final_ru.csv"),
            "final_queries_sha256": file_sha256(worktree / "experiments/frozen/final_queries.csv"),
            "frozen_snapshot_sha256": file_sha256(worktree / "experiments/frozen/final_values_snapshot.csv"),
            "cpp_int_selection_sha256": file_sha256(tiny_csv),
            "int128_crosscheck_selection_sha256": file_sha256(tiny_csv),
            "full_selection_sha256": file_sha256(tiny_csv),
            "full_selection_row_count": 2,
            "unique_ru_count": 2,
            "round_distribution": {"1": 2, "2": 0, "3": 0},
            "jobs": 1,
            "per_round_timeout_seconds": {"r1": 120, "r2": 1200, "r3": 1800},
            "total_wall_limit_seconds": 7200,
            "cpu_limit_seconds": 7200,
            "rss_limit_bytes": 0,
            "disk_limit_bytes": 0,
            "submit_sha256": "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e",
            "full_4760_scope": True,
            "stage_b_authorized": False,
            "new_way1_run_started": False,
        }
        (artifact_root / "FULL_RUN_AUTHORIZATION.json").write_text(
            json.dumps(auth, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/run_frozen_exact.py",
            "--selection",
            str(tiny_csv),
            "--backend",
            "both",
            "--jobs",
            "1",
            "--resume",
            "--artifact-root",
            str(artifact_root),
            "--artifact-logical-root",
            "artifacts/way2_exact/full",
            "--binary",
            str(binary),
            "--binary-logical-path",
            "recompute_frozen_exact",
            "--queries",
            "experiments/frozen/final_queries.csv",
        )
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/compare_frozen_exact.py",
            "--artifact-root",
            str(artifact_root),
            "--snapshot",
            "experiments/frozen/final_values_snapshot.csv",
            "--selection",
            str(tiny_csv),
        )
        compare = json.loads((artifact_root / "COMPARE.json").read_text(encoding="utf-8"))
        assert compare["selected_columns"] == 2
        assert compare["selected_endpoint_rows"] == sum(1 for _ in csv.DictReader((artifact_root / "COMPARISONS.csv").open()))

        build_repro = {
            "schema": "exact-way2-build-reproducibility-v2",
            "implementation_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=worktree, text=True).strip(),
            "implementation_tree_sha": subprocess.check_output(
                ["git", "rev-parse", "HEAD^{tree}"], cwd=worktree, text=True
            ).strip(),
            "clean_git_status_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "clean_git_diff_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "first_clean_build": {
                "binary_sha256": file_sha256(binary),
                "compiler_path": "/usr/bin/g++",
                "compiler_version": "g++",
                "build_command": "make recompute_frozen_exact",
                "environment": {"CXXFLAGS": ""},
            },
            "second_clean_build": {
                "binary_sha256": file_sha256(binary),
            },
        }
        (artifact_root / "BUILD_REPRODUCIBILITY.json").write_text(
            json.dumps(build_repro, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (artifact_root / "PIPELINE.json").write_text(
            json.dumps(
                {
                    "selector_elapsed_wall": 0.0,
                    "orchestrator_elapsed_wall": 0.0,
                    "comparison_elapsed_wall": float(compare.get("comparison_elapsed_wall", 0.0)),
                    "summarizer_elapsed_wall": 0.0,
                    "total_full_elapsed_wall": 0.0,
                    "peak_process_rss": 0,
                    "peak_total_concurrent_rss": 0,
                    "jobs": 1,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/summarize_full_exact.py",
            "--artifact-root",
            str(artifact_root),
        )
        archive_root = tmp / "archives"
        expect_missing_zstandard_message(worktree, artifact_root, archive_root)
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/archive_full_evidence.py",
            "--artifact-root",
            str(artifact_root),
            "--archive-root",
            str(archive_root),
        )
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/attest_full_artifacts.py",
            "--artifact-root",
            str(artifact_root),
        )
        subprocess.run(
            ["sha256sum", "-c", str(artifact_root / "SHA256SUMS.txt")],
            cwd=artifact_root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        manifest = json.loads((artifact_root / "MANIFEST.json").read_text(encoding="utf-8"))
        raw_index = json.loads((artifact_root / "RAW_EVIDENCE_INDEX.json").read_text(encoding="utf-8"))
        manifest_paths = {entry["path"] for entry in manifest["files"]}
        assert "MANIFEST.json" not in manifest_paths
        assert "SHA256SUMS.txt" not in manifest_paths
        assert raw_index["archive_count"] == 2
        for archive in raw_index["archives"]:
            assert archive["archive_group"] in {"r1_cpp_int", "r1_int128_checked"}
            assert archive["archive_format"] == "tar.zst"
            assert archive["archive_name"].endswith(".tar.zst")
            assert archive["release_asset_name"] == archive["archive_name"]
            assert archive["release_asset_uri_template"].endswith(archive["archive_name"])
            assert "archive_path" not in archive
            authority_fields = [
                archive["archive_name"],
                archive["release_asset_name"],
                archive["release_asset_uri_template"],
            ]
            assert not any(
                field.startswith(("/tmp/", "/home/", "C:\\")) for field in authority_fields if isinstance(field, str)
            )
    print("full exact small pipeline tests passed")


if __name__ == "__main__":
    main()
