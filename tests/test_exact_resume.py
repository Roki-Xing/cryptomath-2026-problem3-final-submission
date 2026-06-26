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
            subprocess.run(["git", "commit", "-m", "temp test snapshot"], cwd=worktree, check=True, env=MAKE_ENV)
            yield worktree
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, check=True)


def run(worktree: Path, expect_success: bool, *args: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [*args],
        cwd=worktree,
        env=MAKE_ENV,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if expect_success and completed.returncode != 0:
        raise AssertionError(completed.stderr)
    if not expect_success and completed.returncode == 0:
        raise AssertionError("command should have failed")
    return completed


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
        selection_root = tmp / "selection"
        subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                "experiments/exact_way2/prepare_selector_inputs.py",
                "--final-ru",
                "experiments/frozen/final_ru.csv",
                "--out",
                str(selection_root),
            ],
            cwd=worktree,
            check=True,
            env=MAKE_ENV,
        )
        subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                "experiments/exact_way2/select_pilot.py",
                "--final-ru",
                "experiments/frozen/final_ru.csv",
                "--final-queries",
                "experiments/frozen/final_queries.csv",
                "--complexity-input",
                str(selection_root / "COMPLEXITY_INPUT.csv"),
                "--spotcheck-coordinates",
                str(selection_root / "SPOTCHECK_COORDINATES.csv"),
                "--out",
                str(selection_root),
            ],
            cwd=worktree,
            check=True,
            env=MAKE_ENV,
        )
        rows = []
        with (selection_root / "PILOT_SELECTION.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows.extend([next(reader), next(reader)])
        selection_csv = tmp / "PILOT_SELECTION.csv"
        with selection_csv.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        shutil.copy2(selection_root / "PILOT_SELECTION.json", tmp / "PILOT_SELECTION.json")

        artifact_root = tmp / "artifacts"
        artifact_root.mkdir(parents=True, exist_ok=True)
        shutil.copy2(selection_csv, artifact_root / "PILOT_SELECTION.csv")
        shutil.copy2(selection_root / "PILOT_SELECTION.json", artifact_root / "PILOT_SELECTION.json")
        cmd = [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/run_frozen_exact.py",
            "--selection",
            str(selection_csv),
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
        ]
        run(worktree, True, *cmd)
        run(worktree, True, *cmd)
        done = next((artifact_root / "completed").glob("*/DONE.json"))
        payload = json.loads(done.read_text(encoding="utf-8"))
        payload["selection_sha256"] = "0" * 64
        done.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        failed = run(worktree, False, *cmd)
        assert "resume metadata mismatch" in failed.stderr
    print("exact resume tests passed")


if __name__ == "__main__":
    main()
