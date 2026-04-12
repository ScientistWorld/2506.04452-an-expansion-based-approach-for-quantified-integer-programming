"""
Evaluate solver result files and write scoring/scores.json.

This module is intentionally method-agnostic: it reads result files produced by
any solver and computes benchmark metrics without importing from method/.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_results(path: Path) -> dict:
    with path.open() as handle:
        return json.load(handle)


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
        solved = [item for item in items if item["status"] in {"SAT", "UNSAT"} and float(item["runtime_s"]) <= timeout_s]
        runtimes = sorted(float(item["runtime_s"]) for item in solved)
        median = None
        if runtimes:
            middle = len(runtimes) // 2
            if len(runtimes) % 2 == 1:
                median = runtimes[middle]
            else:
                median = (runtimes[middle - 1] + runtimes[middle]) / 2.0
        metrics[n] = {
            "instances_solved": len(solved),
            "total_instances": len(items),
            "median_runtime_s": round(median, 6) if median is not None else timeout_s,
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
