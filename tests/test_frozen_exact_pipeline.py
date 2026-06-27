import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUBMIT_SHA = "7b0f638ba8678462ee8d6c12bc0c5b89d7354b4a095b31330f3ba495acfe2e2e"
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
            subprocess.run(["git", "commit", "-m", "temp test snapshot"], cwd=worktree, check=True, env=MAKE_ENV)
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
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_external_binary(worktree: Path, scratch: Path) -> Path:
    subprocess.run(["make", "recompute_frozen_exact"], cwd=worktree, check=True, env=MAKE_ENV)
    binary = scratch / "recompute_frozen_exact"
    shutil.copy2(worktree / "recompute_frozen_exact", binary)
    subprocess.run(["git", "clean", "-fdx"], cwd=worktree, check=True)
    return binary


def main() -> None:
    with clean_worktree() as worktree, tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        binary = build_external_binary(worktree, tmp)
        pilot_dir = tmp / "pilot"
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/prepare_selector_inputs.py",
            "--final-ru",
            "experiments/frozen/final_ru.csv",
            "--out",
            str(pilot_dir),
        )
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/select_pilot.py",
            "--final-ru",
            "experiments/frozen/final_ru.csv",
            "--final-queries",
            "experiments/frozen/final_queries.csv",
            "--complexity-input",
            str(pilot_dir / "COMPLEXITY_INPUT.csv"),
            "--spotcheck-coordinates",
            str(pilot_dir / "SPOTCHECK_COORDINATES.csv"),
            "--out",
            str(pilot_dir),
        )
        selection = json.loads((pilot_dir / "PILOT_SELECTION.json").read_text(encoding="utf-8"))
        assert selection["selected_columns"] == 344
        assert selection["round_distribution"] == {"r1": 120, "r2": 128, "r3": 96}

        tiny_csv = tmp / "PILOT_SELECTION.csv"
        with (pilot_dir / "PILOT_SELECTION.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = [next(reader), next(reader)]
        with tiny_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        shutil.copy2(pilot_dir / "PILOT_SELECTION.json", tmp / "PILOT_SELECTION.json")
        artifact_root = tmp / "artifacts"
        artifact_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(tiny_csv, artifact_root / "PILOT_SELECTION.csv")
        shutil.copy2(pilot_dir / "PILOT_SELECTION.json", artifact_root / "PILOT_SELECTION.json")
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
            "artifacts/test-pilot",
            "--binary",
            str(binary),
            "--binary-logical-path",
            "recompute_frozen_exact",
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
        )
        compare = json.loads((artifact_root / "COMPARE.json").read_text(encoding="utf-8"))
        assert compare["cpp_int_columns"] == 2
        assert compare["int128_columns"] == 2
        (artifact_root / "REPEAT_SUBSET.json").write_text(
            json.dumps(
                {
                    "cpp_int": {
                        "runs": [1.0, 1.0, 1.0],
                        "cv": 0.0,
                        "bundle_output_sha256_is_diagnostic": True,
                        "bundle_output_sha256_note": "diagnostic",
                        "bundle_output_sha256_per_run": ["a", "b", "c"],
                        "canonical_column_digest_per_run": ["d", "d", "d"],
                        "canonical_column_digest_equal": True,
                        "endpoint_payload_sha256_per_run": ["e", "e", "e"],
                        "endpoint_payload_equal": True,
                    },
                    "int128_checked": {
                        "runs": [1.0, 1.0, 1.0],
                        "cv": 0.0,
                        "bundle_output_sha256_is_diagnostic": True,
                        "bundle_output_sha256_note": "diagnostic",
                        "bundle_output_sha256_per_run": ["f", "g", "h"],
                        "canonical_column_digest_per_run": ["i", "i", "i"],
                        "canonical_column_digest_equal": True,
                        "endpoint_payload_sha256_per_run": ["j", "j", "j"],
                        "endpoint_payload_equal": True,
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (artifact_root / "REPEAT_SUBSET.md").write_text("# repeat\n", encoding="utf-8")
        (artifact_root / "PIPELINE.json").write_text(
            json.dumps(
                {
                    "selector_elapsed_wall": 0.1,
                    "orchestrator_elapsed_wall": 0.2,
                    "comparison_elapsed_wall": 0.3,
                    "summarizer_elapsed_wall": 0.0,
                    "total_pilot_elapsed_wall": 0.6,
                    "peak_process_rss": 1,
                    "peak_total_concurrent_rss": 1,
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
            "experiments/exact_way2/summarize_exact.py",
            "--artifact-root",
            str(artifact_root),
        )
        build_repro = {
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
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/attest_pilot_artifacts.py",
            "--artifact-root",
            str(artifact_root),
            "--artifact-committed-in-commit",
            "1234567890abcdef1234567890abcdef12345678",
        )
        manifest_bytes = (artifact_root / "MANIFEST.json").read_bytes()
        sha_bytes = (artifact_root / "SHA256SUMS.txt").read_bytes()
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/attest_pilot_artifacts.py",
            "--artifact-root",
            str(artifact_root),
            "--artifact-committed-in-commit",
            "1234567890abcdef1234567890abcdef12345678",
        )
        assert manifest_bytes == (artifact_root / "MANIFEST.json").read_bytes()
        assert sha_bytes == (artifact_root / "SHA256SUMS.txt").read_bytes()
        manifest = json.loads((artifact_root / "MANIFEST.json").read_text(encoding="utf-8"))
        assert all(entry["path"] not in {"MANIFEST.json", "SHA256SUMS.txt"} for entry in manifest["files"])
        subprocess.run(
            ["sha256sum", "-c", str(artifact_root / "SHA256SUMS.txt")],
            cwd=artifact_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        comparison_rows = list(
            csv.DictReader((artifact_root / "COMPARISONS.csv").open(newline="", encoding="utf-8"))
        )
        target_row_id = comparison_rows[0]["row_id"]
        bundles_before = {
            path.relative_to(artifact_root): file_sha256(path)
            for path in artifact_root.rglob("*")
            if path.is_file() and "completed" in path.parts
        }
        poisoned = tmp / "poisoned_snapshot.csv"
        with (worktree / "experiments/frozen/final_values_snapshot.csv").open(
            newline="", encoding="utf-8"
        ) as src, poisoned.open("w", newline="", encoding="utf-8") as dst:
            reader = csv.DictReader(src)
            fieldnames = list(reader.fieldnames or [])
            writer = csv.DictWriter(dst, fieldnames=fieldnames)
            writer.writeheader()
            patched = False
            for row in reader:
                if row["row_id"] == target_row_id:
                    row["frozen_way2_ve"] = "999.0"
                    patched = True
                writer.writerow(row)
        assert patched
        run(
            worktree,
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/compare_frozen_exact.py",
            "--artifact-root",
            str(artifact_root),
            "--snapshot",
            str(poisoned),
        )
        bundles_after = {
            path.relative_to(artifact_root): file_sha256(path)
            for path in artifact_root.rglob("*")
            if path.is_file() and "completed" in path.parts
        }
        assert bundles_before == bundles_after
        mismatches = list(csv.DictReader((artifact_root / "MISMATCHES.csv").open(newline="", encoding="utf-8")))
        assert any(row["comparison_status"] == "NOT_EQUAL" for row in mismatches)

        submit_sha = subprocess.check_output(["sha256sum", "submit.txt"], cwd=worktree, text=True).split()[0]
        assert submit_sha == SUBMIT_SHA
    print("frozen exact pipeline tests passed")


if __name__ == "__main__":
    main()
