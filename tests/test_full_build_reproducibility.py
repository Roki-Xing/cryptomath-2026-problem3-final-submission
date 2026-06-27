import json
import os
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
            yield worktree
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, check=True)


def main() -> None:
    with clean_worktree() as worktree, tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        first = tmp / "first.json"
        second = tmp / "second.json"
        merged = tmp / "merged.json"
        for output in (first, second):
            subprocess.run(
                [
                    "python3",
                    "-X",
                    "utf8",
                    "experiments/exact_way2/capture_build_reproducibility.py",
                    "--out",
                    str(output),
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
                "experiments/exact_way2/merge_build_reproducibility.py",
                "--first",
                str(first),
                "--second",
                str(second),
                "--out",
                str(merged),
            ],
            cwd=worktree,
            check=True,
            env=MAKE_ENV,
        )
        payload = json.loads(merged.read_text(encoding="utf-8"))
        assert payload["binary_sha256_match"] is True
        assert payload["first_clean_build"]["binary_sha256"] == payload["second_clean_build"]["binary_sha256"]
        assert payload["first_clean_build"]["objects"]
        assert payload["first_clean_build"]["link_command"]
    print("full build reproducibility tests passed")


if __name__ == "__main__":
    main()
