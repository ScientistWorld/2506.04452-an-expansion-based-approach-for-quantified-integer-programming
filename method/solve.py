#!/usr/bin/env python3
"""Solve one QIP decision instance with EQuIPS (expansion-based CEGAR).

Usage (as called by the evaluators):
    python3 method/solve.py [--solver-seed S] [--mip-backend B] INSTANCE.qlp ANSWER.json

Reads the QLP instance, runs the solver within the CPU budget given in the
environment variable ``QIP_CPU_BUDGET_S`` and writes
``{"answer": "TRUE" | "FALSE" | "UNKNOWN"}``.  TRUE means the existential
player (outermost block) has a winning strategy.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver-seed", type=int, default=None)
    parser.add_argument("--mip-backend", default=None, help="auto (default), highs or cp-sat")
    parser.add_argument("instance")
    parser.add_argument("answer")
    args = parser.parse_args()

    budget = float(os.environ.get("QIP_CPU_BUDGET_S", "10"))
    if args.mip_backend:
        os.environ["EQUIPS_MIP_BACKEND"] = args.mip_backend

    from data.qlp import parse_qlp
    import method.equips as equips

    if args.solver_seed is not None:
        equips.SOLVER_SEED = args.solver_seed

    problem = parse_qlp(args.instance)
    # Leave a safety margin for interpreter start-up (already in process_time)
    # and for writing the answer.
    remaining = 0.92 * budget - time.process_time() - 0.2
    result = equips.solve_qip(problem, timeout_s=max(0.2, remaining))
    answer = {"SAT": "TRUE", "UNSAT": "FALSE"}.get(result["status"], "UNKNOWN")
    Path(args.answer).write_text(json.dumps({"answer": answer}) + "\n")


if __name__ == "__main__":
    main()
