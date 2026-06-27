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
            subprocess.run(["git", "commit", "-m", "temp full auth snapshot"], cwd=worktree, check=True, env=MAKE_ENV)
            yield worktree
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], cwd=ROOT, check=True)


def sha256(path: Path) -> str:
    return subprocess.check_output(["sha256sum", str(path)], text=True).split()[0]


def build_authorization(worktree: Path, tmp: Path) -> tuple[Path, Path, Path]:
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
    selection_csv = selection_dir / "FULL_SELECTION.csv"
    selection_json = json.loads((selection_dir / "FULL_SELECTION.json").read_text(encoding="utf-8"))
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
        "cpp_int_selection_sha256": sha256(selection_csv),
        "int128_crosscheck_selection_sha256": sha256(selection_csv),
        "full_selection_sha256": sha256(selection_csv),
        "full_selection_row_count": selection_json["selected_columns"],
        "unique_ru_count": selection_json["unique_ru_count"],
        "round_distribution": selection_json["round_distribution_by_r"],
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
    return binary, auth_path, selection_dir


def run_verifier(worktree: Path, auth_path: Path, binary: Path, selection_csv: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
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
            str(selection_csv),
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
        check=False,
        env=MAKE_ENV,
    )


def write_selection_variant(selection_dir: Path, rows: list[dict[str, str]], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    selection_csv = out_dir / "FULL_SELECTION.csv"
    with selection_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    selection_json = json.loads((selection_dir / "FULL_SELECTION.json").read_text(encoding="utf-8"))
    selection_json["selected_columns"] = len(rows)
    selection_json["unique_ru_count"] = len({(int(row["r"]), row["u"].lower()) for row in rows})
    distribution = {"1": 0, "2": 0, "3": 0}
    for row in rows:
        distribution[row["r"]] += 1
    selection_json["round_distribution"] = {f"r{k}": v for k, v in distribution.items()}
    selection_json["round_distribution_by_r"] = distribution
    selection_json["selection"] = [
        {
            "r": int(row["r"]),
            "u": row["u"].lower(),
            "selection_reason": row["selection_reason"],
            "active_count": int(row["active_count"]),
            "query_count": int(row["query_count"]),
            "deterministic_hash": row["deterministic_hash"],
        }
        for row in rows
    ]
    selection_json["selection_payload_sha256"] = sha256(selection_csv)
    (out_dir / "FULL_SELECTION.json").write_text(json.dumps(selection_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return selection_csv


def write_auth_variant(base_auth_path: Path, selection_csv: Path, out_path: Path, **overrides: object) -> Path:
    auth = json.loads(base_auth_path.read_text(encoding="utf-8"))
    auth.update(
        {
            "cpp_int_selection_sha256": sha256(selection_csv),
            "int128_crosscheck_selection_sha256": sha256(selection_csv),
            "full_selection_sha256": sha256(selection_csv),
        }
    )
    auth.update(overrides)
    out_path.write_text(json.dumps(auth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    with clean_worktree() as worktree, tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        binary, auth_path, selection_dir = build_authorization(worktree, tmp)
        selection_csv = selection_dir / "FULL_SELECTION.csv"
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
                str(selection_csv),
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
        failed = run_verifier(worktree, bad_path, binary, selection_csv)
        assert failed.returncode != 0
        assert "authorization mismatch" in (failed.stderr + failed.stdout).lower()

        full_rows = list(csv.DictReader(selection_csv.open(newline="", encoding="utf-8")))

        tiny_csv = write_selection_variant(selection_dir, full_rows[:2], tmp / "tiny")
        tiny_auth = write_auth_variant(
            auth_path,
            tiny_csv,
            tmp / "tiny-auth.json",
            full_selection_row_count=2,
            unique_ru_count=2,
            round_distribution={"1": 2, "2": 0, "3": 0},
            full_4760_scope=True,
        )
        tiny_failed = run_verifier(worktree, tiny_auth, binary, tiny_csv)
        assert tiny_failed.returncode != 0
        assert "exactly 4760 rows" in (tiny_failed.stderr + tiny_failed.stdout).lower()

        minus_one_csv = write_selection_variant(selection_dir, full_rows[:-1], tmp / "minus-one")
        minus_one_auth = write_auth_variant(
            auth_path,
            minus_one_csv,
            tmp / "minus-one-auth.json",
            full_selection_row_count=4759,
            unique_ru_count=4759,
            round_distribution={"1": 120, "2": 4544, "3": 95},
        )
        minus_one_failed = run_verifier(worktree, minus_one_auth, binary, minus_one_csv)
        assert minus_one_failed.returncode != 0
        assert "exactly 4760 rows" in (minus_one_failed.stderr + minus_one_failed.stdout).lower()

        extra_rows = full_rows + [dict(full_rows[-1], u="0xffffffff", deterministic_hash="extra")]
        plus_one_csv = write_selection_variant(selection_dir, extra_rows, tmp / "plus-one")
        plus_one_auth = write_auth_variant(
            auth_path,
            plus_one_csv,
            tmp / "plus-one-auth.json",
            full_selection_row_count=4761,
            unique_ru_count=4761,
            round_distribution={"1": 120, "2": 4544, "3": 97},
        )
        plus_one_failed = run_verifier(worktree, plus_one_auth, binary, plus_one_csv)
        assert plus_one_failed.returncode != 0
        assert "exactly 4760 rows" in (plus_one_failed.stderr + plus_one_failed.stdout).lower()

        duplicate_rows = [dict(full_rows[0]), dict(full_rows[0]), *full_rows[2:]]
        duplicate_csv = write_selection_variant(selection_dir, duplicate_rows, tmp / "duplicate")
        duplicate_auth = write_auth_variant(
            auth_path,
            duplicate_csv,
            tmp / "duplicate-auth.json",
            full_selection_row_count=4760,
            unique_ru_count=4759,
            round_distribution={"1": 121, "2": 4543, "3": 96},
        )
        duplicate_failed = run_verifier(worktree, duplicate_auth, binary, duplicate_csv)
        assert duplicate_failed.returncode != 0
        assert "duplicate (r,u)" in (duplicate_failed.stderr + duplicate_failed.stdout).lower()

        wrong_dist_csv = write_selection_variant(selection_dir, full_rows, tmp / "wrong-dist")
        wrong_dist_auth = write_auth_variant(
            auth_path,
            wrong_dist_csv,
            tmp / "wrong-dist-auth.json",
            full_selection_row_count=4760,
            unique_ru_count=4760,
            round_distribution={"1": 121, "2": 4543, "3": 96},
        )
        wrong_dist_failed = run_verifier(worktree, wrong_dist_auth, binary, wrong_dist_csv)
        assert wrong_dist_failed.returncode != 0
        assert "authorization mismatch for round_distribution" in (
            wrong_dist_failed.stderr + wrong_dist_failed.stdout
        ).lower()

        mismatch_final_ru_auth = write_auth_variant(
            auth_path,
            selection_csv,
            tmp / "mismatch-final-ru.json",
            final_ru_sha256="0" * 64,
        )
        mismatch_final_ru_failed = run_verifier(worktree, mismatch_final_ru_auth, binary, selection_csv)
        assert mismatch_final_ru_failed.returncode != 0
        assert "authorization mismatch for final_ru_sha256" in (
            mismatch_final_ru_failed.stderr + mismatch_final_ru_failed.stdout
        ).lower()

        replaced_rows = [dict(row) for row in full_rows]
        replaced_rows[-1] = dict(replaced_rows[-1], u="0xffffffff", deterministic_hash="replacement")
        replaced_csv = write_selection_variant(selection_dir, replaced_rows, tmp / "replaced")
        replaced_auth = write_auth_variant(
            auth_path,
            replaced_csv,
            tmp / "replaced-auth.json",
            full_selection_row_count=4760,
            unique_ru_count=4760,
            round_distribution={"1": 120, "2": 4544, "3": 96},
        )
        replaced_failed = run_verifier(worktree, replaced_auth, binary, replaced_csv)
        assert replaced_failed.returncode != 0
        replaced_output = (replaced_failed.stderr + replaced_failed.stdout).lower()
        assert "final_ru" in replaced_output or "missing final_ru rows" in replaced_output or "extra rows not in final_ru" in replaced_output
    print("full exact authorization tests passed")


if __name__ == "__main__":
    main()
