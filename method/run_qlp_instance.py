from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from data.qlp import parse_qlp
from method.equips import solve_qip, solve_qip_optimization


def _solve_instance(instance_path: Path, timeout_s: float) -> dict:
    problem = parse_qlp(instance_path)
    start = time.time()
    if problem.objective is None:
        result = solve_qip(problem, timeout_s=timeout_s)
    else:
        result = solve_qip_optimization(problem, timeout_s=timeout_s)
    runtime_s = time.time() - start
    return {
        "instance": str(instance_path),
        "instance_name": instance_path.name,
        "objective_sense": problem.objective_sense if problem.objective is not None else None,
        "status": result["status"],
        "runtime_s": runtime_s,
        "optimal_value": result.get("optimal_value"),
        "assignment_found": result.get("assignment") is not None,
        "stats": result.get("stats"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", action="append", required=True, help="Path to a QLP instance.")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    records = [_solve_instance(Path(path), args.timeout) for path in args.instance]
    payload = {
        "benchmark": "qlp_instance",
        "solver": "equips",
        "timeout_s": args.timeout,
        "results": records,
    }
    output_path.write_text(json.dumps(payload, indent=2))

    for record in records:
        print(
            f"{record['instance_name']}: status={record['status']} "
            f"runtime={record['runtime_s']:.4f}s optimal_value={record['optimal_value']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
