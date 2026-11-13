#!/usr/bin/env python3
"""Exact ground truth for one MCN graph (hidden; used by build_instances.py).

Usage:
  python3 eval/test/gt_mcn.py bitmask SIZE SEED
      exact optimum by the bitmask minimax over full-budget choices
  python3 eval/test/gt_mcn.py cegar SIZE SEED DECISION_CAP_S GRAPH_CAP_S
      exact optimum by binary search over the threshold K, each decision
      "can the defender save >= K nodes?" decided by an expansion-based CEGAR
      solver (hidden copy, CP-SAT backend) run to completion
  python3 eval/test/gt_mcn.py verify SIZE SEED OPT DECISION_CAP_S
      CEGAR decisions at K = OPT (must be TRUE) and K = OPT + 1 (must be FALSE)

Prints one JSON line.  Both methods are exact; a decision that does not finish
within its cap leaves the graph uncertified.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
sys.path.insert(0, str(HERE))

import qip_hidden_gen as gen  # noqa: E402


def _cegar():
    os.environ["EQUIPS_MIP_BACKEND"] = "cp-sat"
    sys.path.insert(0, str(WORKSPACE))
    sys.path.insert(0, str(HERE / "audit"))
    import equips_copy as eq  # noqa: E402
    from data.qlp import parse_qlp  # noqa: E402

    eq._solve_ip_feasible = eq._solve_cp_sat_feasible
    return eq, parse_qlp


def decide(eq, parse, size: int, seed: int, threshold: int, cap: float):
    text = gen.mcn_instance(size, seed, threshold)
    with tempfile.NamedTemporaryFile("w", suffix=".qlp", delete=False) as fh:
        fh.write(text)
        path = fh.name
    try:
        problem = parse(path)
    finally:
        os.unlink(path)
    t0 = time.process_time()
    result = eq.solve_qip(problem, timeout_s=max(1.0, cap))
    return {"SAT": True, "UNSAT": False}.get(result["status"]), time.process_time() - t0


def main() -> None:
    mode, size, seed = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    params = gen.mcn_params(size, seed)
    if mode == "bitmask":
        t0 = time.process_time()
        opt = gen.mcn_optimum(params)
        print(json.dumps({"opt": opt, "cpu": time.process_time() - t0}))
        return
    eq, parse = _cegar()
    if mode == "verify":
        opt, cap = int(sys.argv[4]), float(sys.argv[5])
        t_true = decide(eq, parse, size, seed, opt, cap)
        t_false = decide(eq, parse, size, seed, opt + 1, cap)
        print(json.dumps({"at_opt": t_true[0], "above_opt": t_false[0], "cpu": [t_true[1], t_false[1]]}))
        return
    if mode != "cegar":
        raise SystemExit(f"unknown mode {mode}")
    decision_cap, graph_cap = float(sys.argv[4]), float(sys.argv[5])
    # K = 0 is TRUE; K = n - attack + 1 is FALSE (the attacker can always
    # infect `attack` unvaccinated nodes).
    lo, hi = 0, size - params["attack"] + 1
    times: dict = {}
    spent = 0.0
    while hi - lo > 1:
        mid = (lo + hi) // 2
        cap = min(decision_cap, graph_cap - spent)
        if cap < 1.0:
            print(json.dumps({"failed": True, "spent": spent}))
            return
        answer, cpu = decide(eq, parse, size, seed, mid, cap)
        spent += cpu
        if answer is None:
            print(json.dumps({"failed": True, "spent": spent}))
            return
        times[mid] = cpu
        if answer:
            lo = mid
        else:
            hi = mid
    print(json.dumps({"opt": lo, "t_true": times.get(lo, 0.0), "t_false": times.get(hi, 0.0), "spent": spent}))


if __name__ == "__main__":
    main()
