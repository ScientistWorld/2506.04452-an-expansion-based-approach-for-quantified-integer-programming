#!/usr/bin/env python3
"""Audit variants of the reference solver (hidden; not methods).

Usage: python3 eval/test/audit/variant_solve.py VARIANT INSTANCE.qlp ANSWER.json

Every variant runs a copy of the reference implementation (equips_copy.py)
with one change:
  ref_copy                unchanged
  cpsat_all               CP-SAT for every integer subproblem (incl. relaxation)
  gf2_presolve            sound mod-2 elimination on equality rows (after bound
                          propagation) before each existential IP call
  cpsat_gf2               both of the above
  highs_only              HiGHS for every subproblem (paper's Problem (2) as a MIP)
  lb_initial_move         lower-bound first move instead of the existential IP
                          relaxation (paper Appendix A.1.3, "LB")
  tenth_budget            gives up after 10% of the CPU budget
  guess_false_on_timeout  answers FALSE whenever the reference would time out
  guess_true_on_timeout   answers TRUE whenever the reference would time out
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(HERE))


def gf2_infeasible(variables, constraints, universal_constraints) -> bool:
    """Sound infeasibility test: bound propagation from single-variable rows,
    then Gaussian elimination over GF(2) on every equality row."""
    lower = {v.name: v.lower for v in variables}
    upper = {v.name: v.upper for v in variables}
    rows = [(c.coeffs, c.rhs, c.is_equality) for c in constraints]
    rows += [(c.coeffs, c.rhs, False) for c in universal_constraints]
    for coeffs, rhs, is_eq in rows:
        items = [(n, a) for n, a in coeffs.items() if a != 0]
        if len(items) != 1 or items[0][0] not in lower:
            continue
        name, a = items[0]
        # a*x <= rhs (and >= rhs for equalities)
        if a > 0:
            upper[name] = min(upper[name], _floor_div(rhs, a))
            if is_eq:
                lower[name] = max(lower[name], _ceil_div(rhs, a))
        else:
            lower[name] = max(lower[name], _ceil_div(rhs, a))
            if is_eq:
                upper[name] = min(upper[name], _floor_div(rhs, a))
    for name in lower:
        if lower[name] > upper[name]:
            return True
    fixed = {n: lower[n] for n in lower if lower[n] == upper[n]}
    index: dict = {}
    pivots: dict = {}
    for coeffs, rhs, is_eq in rows:
        if not is_eq:
            continue
        row = 0
        parity = rhs & 1
        for name, a in coeffs.items():
            if a % 2 == 0:
                continue
            if name in fixed:
                parity ^= fixed[name] & 1
                continue
            bit = index.setdefault(name, len(index))
            row ^= 1 << bit
        while row:
            p = row.bit_length() - 1
            if p in pivots:
                prow, prhs = pivots[p]
                row ^= prow
                parity ^= prhs
            else:
                pivots[p] = (row, parity)
                break
        else:
            if parity:
                return True
    return False


def _ceil_div(num: int, den: int) -> int:
    return -((-num) // den)


def _floor_div(num: int, den: int) -> int:
    return num // den


def main() -> None:
    variant, instance, answer_path = sys.argv[1], sys.argv[2], sys.argv[3]
    budget = float(os.environ.get("QIP_CPU_BUDGET_S", "10"))
    if variant in ("cpsat_all", "cpsat_gf2"):
        os.environ["EQUIPS_MIP_BACKEND"] = "cp-sat"
    elif variant == "highs_only":
        os.environ["EQUIPS_MIP_BACKEND"] = "highs"
    else:
        os.environ["EQUIPS_MIP_BACKEND"] = "auto"

    import equips_copy as eq
    from data.qlp import parse_qlp

    if variant in ("cpsat_all", "cpsat_gf2"):
        eq._solve_ip_feasible = eq._solve_cp_sat_feasible
    if variant in ("gf2_presolve", "cpsat_gf2"):
        def wrap(fn):
            def wrapped(variables, constraints, universal_constraints, time_limit_s=None):
                if gf2_infeasible(variables, constraints, universal_constraints):
                    return None
                return fn(variables, constraints, universal_constraints, time_limit_s=time_limit_s)
            return wrapped
        eq._solve_ip_feasible = wrap(eq._solve_ip_feasible)
        eq._solve_cp_sat_feasible = wrap(eq._solve_cp_sat_feasible)
    if variant == "lb_initial_move":
        eq._existential_relaxation_move = lambda multigame, time_limit_s=None: {
            v.name: v.lower for v in multigame.outer_vars
        }

    problem = parse_qlp(instance)
    timeout = 0.92 * budget - time.process_time() - 0.2
    if variant == "tenth_budget":
        timeout = min(timeout, 0.1 * budget)
    result = eq.solve_qip(problem, timeout_s=max(0.2, timeout))
    answer = {"SAT": "TRUE", "UNSAT": "FALSE"}.get(result["status"], "UNKNOWN")
    if answer == "UNKNOWN" and variant == "guess_false_on_timeout":
        answer = "FALSE"
    if answer == "UNKNOWN" and variant == "guess_true_on_timeout":
        answer = "TRUE"
    Path(answer_path).write_text(json.dumps({"answer": answer}))


if __name__ == "__main__":
    main()
