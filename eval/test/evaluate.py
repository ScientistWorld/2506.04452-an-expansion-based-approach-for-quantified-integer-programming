"""
Held-out test-slice evaluator for QRandomParity solver result files.

This module is intentionally self-contained and method-agnostic. It reads the
same raw result JSON files as scripts/evaluate.sh, filters to the held-out test
instance IDs for the existing reference experiments, and writes
scoring/scores_test.json.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


SLICE_INSTANCE_IDS = {
    100: {
        0, 1, 3, 5, 6, 7, 8, 13, 14, 22,
        25, 26, 28, 29, 31, 34, 35, 36, 39, 40,
        41, 42, 43, 45, 46, 50, 52, 53, 54, 56,
        57, 58, 59, 62, 67, 68, 70, 71, 72, 74,
        76, 80, 81, 82, 83, 85, 87, 95, 98, 99,
    },
    200: {
        0, 1, 3, 5, 6, 7, 8, 13, 14, 22,
        25, 26, 28, 29, 31, 34, 35, 36, 39, 40,
        41, 42, 43, 45, 46, 50, 52, 53, 54, 56,
        57, 58, 59, 62, 67, 68, 70, 71, 72, 74,
        76, 80, 81, 82, 83, 85, 87, 95, 98, 99,
    },
}

SOLVED_STATUSES = {"SAT", "UNSAT"}


def load_results(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


def median(values: list[float], fallback: float) -> float:
    if not values:
        return fallback
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def nearest_rank_percentile(values: list[float], percentile: float, fallback: float) -> float:
    if not values:
        return fallback
    ordered = sorted(values)
    rank = max(1, int(len(ordered) * percentile + 0.999999))
    return ordered[min(rank - 1, len(ordered) - 1)]


def slice_metrics(records: list[dict], n: int, timeout_s: float) -> dict:
    wanted = SLICE_INSTANCE_IDS[n]
    by_id: dict[int, dict] = {}
    for record in records:
        if int(record["n"]) != n:
            continue
        instance_id = int(record["instance_id"])
        if instance_id not in wanted:
            continue
        if instance_id in by_id:
            raise ValueError(f"Duplicate result for n={n}, instance_id={instance_id}.")
        by_id[instance_id] = record

    missing = sorted(wanted - set(by_id))
    if missing:
        preview = ", ".join(str(item) for item in missing[:10])
        suffix = "..." if len(missing) > 10 else ""
        raise ValueError(f"Missing {len(missing)} test records for n={n}: {preview}{suffix}")

    items = list(by_id.values())
    solved = [
        item for item in items
        if item["status"] in SOLVED_STATUSES and float(item["runtime_s"]) <= timeout_s
    ]
    solved_runtimes = [float(item["runtime_s"]) for item in solved]
    capped_runtimes = [
        min(float(item.get("runtime_s", timeout_s)), timeout_s)
        if item["status"] in SOLVED_STATUSES else timeout_s
        for item in items
    ]
    mean_runtime = sum(solved_runtimes) / len(solved_runtimes) if solved_runtimes else timeout_s
    return {
        "median_runtime_s": round(median(solved_runtimes, timeout_s), 6),
        "instances_solved": len(solved),
        "mean_runtime_s": round(mean_runtime, 6),
        "p90_runtime_s": round(nearest_rank_percentile(capped_runtimes, 0.90, timeout_s), 6),
    }


def build_scores(result_blobs: list[dict]) -> dict:
    scores = {"experiments": {}}
    seen_experiments: set[str] = set()

    for blob in result_blobs:
        solver_name = blob["solver"]
        timeout_s = float(blob["timeout_s"])
        records = list(blob["results"])
        available_n = {int(record["n"]) for record in records}
        for n in sorted(set(SLICE_INSTANCE_IDS) & available_n):
            experiment = f"qrandomparity_n{n}"
            metrics = slice_metrics(records, n=n, timeout_s=timeout_s)
            scores["experiments"].setdefault(experiment, {"results": {}})
            scores["experiments"][experiment]["results"][solver_name] = metrics
            seen_experiments.add(experiment)

    expected = {f"qrandomparity_n{n}" for n in SLICE_INSTANCE_IDS}
    missing_experiments = sorted(expected - seen_experiments)
    if missing_experiments:
        raise ValueError(
            "No test-slice records were found for required experiments: "
            + ", ".join(missing_experiments)
        )
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-file", action="append", required=True, help="Path to a solver results JSON file.")
    parser.add_argument("--scores-output", default="/home/user/scoring/scores_test.json")
    args = parser.parse_args()

    blobs = [load_results(Path(path)) for path in args.results_file]
    scores = build_scores(blobs)

    output_path = Path(args.scores_output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as handle:
        json.dump(scores, handle, indent=2)

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
