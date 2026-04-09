from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from data.qrandomparity import generate_qrandomparity
from method.equips import solve_qip


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-values", type=int, nargs="+", required=True)
    parser.add_argument("--num-instances", type=int, default=20)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    records = []
    for n in args.n_values:
        for instance_id in range(args.num_instances):
            seed = args.seed + 1000 * n + instance_id
            problem = generate_qrandomparity(n=n, seed=seed)
            start = time.time()
            try:
                result = solve_qip(problem, timeout_s=args.timeout)
                status = result["status"]
            except Exception as exc:
                status = "ERROR"
                result = {"assignment": None, "error": str(exc)}
            runtime_s = time.time() - start
            records.append(
                {
                    "n": n,
                    "instance_id": instance_id,
                    "seed": seed,
                    "status": status,
                    "runtime_s": runtime_s,
                    "assignment_found": result.get("assignment") is not None,
                }
            )
            print(f"n={n} instance={instance_id} status={status} runtime={runtime_s:.4f}s")

    payload = {
        "benchmark": "qrandomparity",
        "solver": "equips",
        "timeout_s": args.timeout,
        "results": records,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as handle:
        json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    main()
