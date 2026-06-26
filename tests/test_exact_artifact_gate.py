import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAKE_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}


@contextmanager
def clean_worktree():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    with tempfile.TemporaryDirectory() as tmpdir:
        worktree = Path(tmpdir) / "worktree"
        subprocess.run(["git", "worktree", "add", "--detach", str(worktree), head], cwd=ROOT, check=True)
        try:
            yield worktree
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, check=True)


def main() -> None:
    with clean_worktree() as worktree, tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        selection_root = tmp / "selection"
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
                "--out",
                str(selection_root),
            ],
            cwd=worktree,
            check=True,
            env=MAKE_ENV,
        )
        artifact_root = tmp / "artifacts"
        (artifact_root / ".staging" / "bad.partial").mkdir(parents=True)
        completed = subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                "experiments/exact_way2/run_frozen_exact.py",
                "--selection",
                str(selection_root / "PILOT_SELECTION.csv"),
                "--backend",
                "cpp_int",
                "--jobs",
                "1",
                "--resume",
                "--artifact-root",
                str(artifact_root),
            ],
            cwd=worktree,
            env=MAKE_ENV,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert completed.returncode != 0
        assert "partial or staging artifacts present" in completed.stderr
    print("exact artifact gate tests passed")


if __name__ == "__main__":
    main()
