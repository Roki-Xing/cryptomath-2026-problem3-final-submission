#!/usr/bin/env python3
"""Verify deterministic frozen-subset and synthetic-frozen-shaped query families."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "bench" / "way1" / "generate_query_family.py"
SOURCE = ROOT / "experiments" / "frozen" / "final_queries.csv"
RU_SOURCE = ROOT / "experiments" / "frozen" / "final_ru.csv"
REQUIRED_METADATA = {
    "family",
    "profile",
    "seed",
    "source_sha256",
    "generator_commit",
    "Q",
    "unique_u",
    "unique_v",
    "u_degree_histogram",
    "v_degree_histogram",
    "u_degree_max",
    "u_degree_median",
    "u_degree_p95",
    "v_degree_max",
    "v_degree_median",
    "v_degree_p95",
    "query_file_sha256",
    "semantic_query_sha256",
    "synthetic",
}


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args), cwd=ROOT, text=True, capture_output=True, check=False
    )


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    return list(csv.DictReader(path.open(encoding="utf-8", newline="")))


def generate(
    tmp: Path,
    *,
    family: str,
    profile: str,
    rounds: int,
    count: int,
    seed: str,
    name: str,
) -> tuple[Path, Path, subprocess.CompletedProcess[str]]:
    out = tmp / f"{name}.csv"
    metadata = tmp / f"{name}.json"
    completed = run(
        "python3",
        "-X",
        "utf8",
        str(GENERATOR),
        "--source",
        str(SOURCE),
        "--ru-source",
        str(RU_SOURCE),
        "--family",
        family,
        "--profile",
        profile,
        "--r",
        str(rounds),
        "--count",
        str(count),
        "--seed",
        seed,
        "--out",
        str(out),
        "--metadata-out",
        str(metadata),
    )
    return out, metadata, completed


def assert_metadata(path: Path, query_path: Path, *, synthetic: bool, count: int) -> dict:
    metadata = json.loads(path.read_text(encoding="utf-8"))
    assert REQUIRED_METADATA <= metadata.keys()
    assert metadata["Q"] == count
    assert metadata["synthetic"] is synthetic
    assert metadata["query_file_sha256"] == sha256_file(query_path)
    assert len(metadata["semantic_query_sha256"]) == 64
    assert len(metadata["source_sha256"]) == 64
    assert len(metadata["generator_commit"]) == 40
    assert metadata["u_degree_max"] >= metadata["u_degree_median"]
    assert metadata["v_degree_max"] >= metadata["v_degree_median"]
    return metadata


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        frozen, frozen_meta, completed = generate(
            tmp_path,
            family="frozen-subset",
            profile="uv_core",
            rounds=2,
            count=64,
            seed="stage-a0-v1",
            name="frozen",
        )
        assert completed.returncode == 0, completed.stderr
        frozen_rows = read_rows(frozen)
        assert len(frozen_rows) == 64
        assert len({(row["r"], row["u"], row["v"]) for row in frozen_rows}) == 64
        u_degrees = Counter(row["u"] for row in frozen_rows)
        v_degrees = Counter(row["v"] for row in frozen_rows)
        assert max(u_degrees.values()) > 1
        assert max(v_degrees.values()) > 1
        metadata = assert_metadata(frozen_meta, frozen, synthetic=False, count=64)
        assert metadata["family"] == "FROZEN_SUBSET"
        assert metadata["profile"] == "uv_core"

        frozen_again, frozen_again_meta, repeated = generate(
            tmp_path,
            family="frozen-subset",
            profile="uv_core",
            rounds=2,
            count=64,
            seed="stage-a0-v1",
            name="frozen-again",
        )
        assert repeated.returncode == 0, repeated.stderr
        assert frozen.read_bytes() == frozen_again.read_bytes()
        assert (
            json.loads(frozen_meta.read_text(encoding="utf-8"))["semantic_query_sha256"]
            == json.loads(frozen_again_meta.read_text(encoding="utf-8"))[
                "semantic_query_sha256"
            ]
        )

        unavailable, unavailable_meta, failed = generate(
            tmp_path,
            family="frozen-subset",
            profile="uv_core",
            rounds=1,
            count=512,
            seed="stage-a0-v1",
            name="unavailable",
        )
        assert failed.returncode != 0
        assert "available" in failed.stderr
        assert not unavailable.exists()
        assert not unavailable_meta.exists()

        synthetic, synthetic_meta, completed = generate(
            tmp_path,
            family="synthetic-frozen-shaped",
            profile="uv_core",
            rounds=3,
            count=512,
            seed="stage-a0-v1",
            name="synthetic",
        )
        assert completed.returncode == 0, completed.stderr
        synthetic_rows = read_rows(synthetic)
        assert len(synthetic_rows) == 512
        assert len({(row["r"], row["u"], row["v"]) for row in synthetic_rows}) == 512
        assert all(int(row["u"], 0) != 0 and int(row["v"], 0) != 0 for row in synthetic_rows)
        synthetic_metadata = assert_metadata(
            synthetic_meta, synthetic, synthetic=True, count=512
        )
        assert synthetic_metadata["family"] == "SYNTHETIC_FROZEN_SHAPED"
        assert synthetic_metadata["unique_u"] >= 8
        assert synthetic_metadata["unique_v"] >= 8
        assert synthetic_metadata["unique_u"] < 512
        assert synthetic_metadata["unique_v"] < 512

        uniform, uniform_meta, completed = generate(
            tmp_path,
            family="uniform",
            profile="sha-order",
            rounds=1,
            count=512,
            seed="stage-a0-v1",
            name="uniform",
        )
        assert completed.returncode == 0, completed.stderr
        uniform_metadata = assert_metadata(
            uniform_meta, uniform, synthetic=True, count=512
        )
        assert uniform_metadata["family"] == "UNIFORM_SYNTHETIC"
        assert uniform_metadata["unique_u"] == 512
        assert uniform_metadata["unique_v"] == 512

    print("way-1 query family tests passed")


if __name__ == "__main__":
    main()
