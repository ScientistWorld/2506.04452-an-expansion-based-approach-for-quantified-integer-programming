"""
Evaluate solver result files and write scoring/scores.json.

This module is intentionally method-agnostic: it reads result files produced by
any solver and computes benchmark metrics without importing from method/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


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


def group_metrics(records: list[dict], expected_count: int | None, timeout_s: float) -> dict[int, dict]:
    grouped: dict[int, list[dict]] = {}
    for record in records:
        grouped.setdefault(int(record["n"]), []).append(record)

    metrics: dict[int, dict] = {}
    for n, items in grouped.items():
        if expected_count is not None and len(items) != expected_count:
            raise ValueError(
                f"Expected {expected_count} instances for n={n}, but found {len(items)} in the results file."
            )
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
        metrics[n] = {
            "instances_solved": len(solved),
            "total_instances": len(items),
            "median_runtime_s": round(median(solved_runtimes, timeout_s), 6),
            "mean_runtime_s": round(mean_runtime, 6),
            "p90_runtime_s": round(nearest_rank_percentile(capped_runtimes, 0.90, timeout_s), 6),
        }
    return metrics


def build_scores(result_blobs: list[dict]) -> dict:
    scores = {"experiments": {}}

    for blob in result_blobs:
        solver_name = blob["solver"]
        timeout_s = float(blob["timeout_s"])
        expected_count = blob.get("num_instances")
        metrics = group_metrics(blob["results"], expected_count=expected_count, timeout_s=timeout_s)
        for n, n_metrics in metrics.items():
            experiment = f"qrandomparity_n{n}"
            scores["experiments"].setdefault(experiment, {"results": {}})
            scores["experiments"][experiment]["results"][solver_name] = {
                "median_runtime_s": n_metrics["median_runtime_s"],
                "instances_solved": n_metrics["instances_solved"],
                "mean_runtime_s": n_metrics["mean_runtime_s"],
                "p90_runtime_s": n_metrics["p90_runtime_s"],
            }
    return scores


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-file", action="append", required=True, help="Path to a solver results JSON file.")
    parser.add_argument("--scores-output", default="/home/user/scoring/scores.json")
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
