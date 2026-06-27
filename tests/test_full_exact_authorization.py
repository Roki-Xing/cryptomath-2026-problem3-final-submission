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
            subprocess.run(["git", "commit", "-m", "temp full auth snapshot"], cwd=worktree, check=True, env=MAKE_ENV)
            yield worktree
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, check=True)


def sha256(path: Path) -> str:
    return subprocess.check_output(["sha256sum", str(path)], text=True).split()[0]


def build_authorization(worktree: Path, tmp: Path) -> tuple[Path, Path]:
    subprocess.run(["make", "recompute_frozen_exact"], cwd=worktree, check=True, env=MAKE_ENV)
    binary = tmp / "recompute_frozen_exact"
    shutil.copy2(worktree / "recompute_frozen_exact", binary)
    subprocess.run(["git", "clean", "-fdx"], cwd=worktree, check=True)

    selection_dir = tmp / "selection"
    subprocess.run(
        [
            "python3",
            "-X",
            "utf8",
            "experiments/exact_way2/select_full.py",
            "--final-ru",
            "experiments/frozen/final_ru.csv",
            "--final-queries",
            "experiments/frozen/final_queries.csv",
            "--out",
            str(selection_dir),
        ],
        cwd=worktree,
        check=True,
        env=MAKE_ENV,
    )
    auth_path = tmp / "FULL_RUN_AUTHORIZATION.json"
    auth = {
        "schema": "exact-way2-full-authorization-v1",
        "authorized": True,
        "authorized_by": "test",
        "authorized_at_utc": "2026-06-27T00:00:00Z",
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=worktree, text=True).strip(),
        "source_tree_sha": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=worktree, text=True).strip(),
        "source_tree_dirty": False,
        "binary_sha256": sha256(binary),
        "build_command": "make recompute_frozen_exact",
        "compiler_path": "/usr/bin/g++",
        "compiler_version": "g++",
        "final_ru_sha256": sha256(worktree / "experiments/frozen/final_ru.csv"),
        "final_queries_sha256": sha256(worktree / "experiments/frozen/final_queries.csv"),
        "frozen_snapshot_sha256": sha256(worktree / "experiments/frozen/final_values_snapshot.csv"),
        "cpp_int_selection_sha256": sha256(selection_dir / "FULL_SELECTION.csv"),
        "int128_crosscheck_selection_sha256": sha256(selection_dir / "FULL_SELECTION.csv"),
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
    auth_path.write_text(json.dumps(auth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return binary, auth_path


def main() -> None:
    with clean_worktree() as worktree, tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        binary, auth_path = build_authorization(worktree, tmp)
        subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                "experiments/exact_way2/verify_full_authorization.py",
                "--authorization",
                str(auth_path),
                "--binary",
                str(binary),
                "--selection",
                str(tmp / "selection" / "FULL_SELECTION.csv"),
                "--queries",
                "experiments/frozen/final_queries.csv",
                "--snapshot",
                "experiments/frozen/final_values_snapshot.csv",
                "--jobs",
                "1",
            ],
            cwd=worktree,
            check=True,
            env=MAKE_ENV,
        )

        bad = json.loads(auth_path.read_text(encoding="utf-8"))
        bad["source_commit"] = "0" * 40
        bad_path = tmp / "bad.json"
        bad_path.write_text(json.dumps(bad, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        failed = subprocess.run(
            [
                "python3",
                "-X",
                "utf8",
                "experiments/exact_way2/verify_full_authorization.py",
                "--authorization",
                str(bad_path),
                "--binary",
                str(binary),
                "--selection",
                str(tmp / "selection" / "FULL_SELECTION.csv"),
                "--queries",
                "experiments/frozen/final_queries.csv",
                "--snapshot",
                "experiments/frozen/final_values_snapshot.csv",
                "--jobs",
                "1",
            ],
            cwd=worktree,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=MAKE_ENV,
        )
        assert failed.returncode != 0
        assert "authorization mismatch" in (failed.stderr + failed.stdout).lower()
    print("full exact authorization tests passed")


if __name__ == "__main__":
    main()
