from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from data.qrandomparity import generate_qrandomparity
from method.equips import solve_qip


def _load_existing_records(output_path: Path) -> tuple[list[dict], set[tuple[int, int]]]:
    if not output_path.exists():
        return [], set()
    with output_path.open() as handle:
        payload = json.load(handle)
    records = list(payload.get("results", []))
    seen = {(int(record["n"]), int(record["instance_id"])) for record in records}
    return records, seen


def _save_payload(
    output_path: Path,
    timeout: float,
    n_values: list[int],
    records: list[dict],
) -> None:
    payload = {
        "benchmark": "qrandomparity",
        "solver": "equips",
        "timeout_s": timeout,
        "n_values": list(n_values),
        "results": records,
    }
    tmp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tmp_path.open("w") as handle:
        json.dump(payload, handle, indent=2)
    tmp_path.replace(output_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-values", type=int, nargs="+", required=True)
    parser.add_argument("--num-instances", type=int, default=20)
    parser.add_argument("--instance-start", type=int, default=0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", required=True)
    parser.add_argument("--resume", action="store_true", help="Resume from an existing output file if present.")
    args = parser.parse_args()

    output_path = Path(args.output)
    if args.resume:
        records, seen = _load_existing_records(output_path)
    else:
        records, seen = [], set()

    for n in args.n_values:
        for instance_id in range(args.instance_start, args.instance_start + args.num_instances):
            if (n, instance_id) in seen:
                print(f"n={n} instance={instance_id} already recorded, skipping", flush=True)
                continue
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
            seen.add((n, instance_id))
            _save_payload(output_path, args.timeout, args.n_values, records)
            print(f"n={n} instance={instance_id} status={status} runtime={runtime_s:.4f}s", flush=True)

    _save_payload(output_path, args.timeout, args.n_values, records)


if __name__ == "__main__":
    main()
