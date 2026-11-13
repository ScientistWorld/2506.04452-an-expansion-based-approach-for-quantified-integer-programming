#!/usr/bin/env python3
"""Solve one QIP decision instance with EQuIPS (expansion-based CEGAR).

Usage (as called by the evaluators):
    python3 method/solve.py [--solver-seed S] [--mip-backend B] INSTANCE.qlp ANSWER.json

Reads the QLP instance, runs the solver and writes
``{"answer": "TRUE" | "FALSE" | "UNKNOWN"}``.  TRUE means the existential
player (outermost block) has a winning strategy.

The evaluator enforces the budget (counted instructions) by stopping the
process, so the solver does not time itself: it runs to completion, with the
evaluator's wall-clock watchdog (``QIP_WALL_LIMIT_S``) as its only internal
limit.  This keeps every run deterministic.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--solver-seed", type=int, default=None)
    parser.add_argument("--mip-backend", default=None, help="auto (default), highs or cp-sat")
    parser.add_argument("instance")
    parser.add_argument("answer")
    args = parser.parse_args()

    limit = float(os.environ.get("QIP_WALL_LIMIT_S", "600"))
    if args.mip_backend:
        os.environ["EQUIPS_MIP_BACKEND"] = args.mip_backend

    from data.qlp import parse_qlp
    import method.equips as equips

    if args.solver_seed is not None:
        equips.SOLVER_SEED = args.solver_seed

    problem = parse_qlp(args.instance)
    result = equips.solve_qip(problem, timeout_s=limit)
    answer = {"SAT": "TRUE", "UNSAT": "FALSE"}.get(result["status"], "UNKNOWN")
    Path(args.answer).write_text(json.dumps({"answer": answer}) + "\n")


if __name__ == "__main__":
    main()
