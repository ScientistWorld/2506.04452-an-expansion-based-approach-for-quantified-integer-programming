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
  minresp                 minimal responses: a check whose problem is a single
                          existential block (the answer to a complete move of
                          the opponent) returns a solution with the smallest
                          total value of its variables (HiGHS MIP), instead of
                          any feasible one, so each refinement covers more
                          opponent moves (wins1 guided by an objective, one of
                          the paper's suggested improvements)
  cpsat_minresp           cpsat_all + minimal responses (CP-SAT)
  short_timeout           gives up after 3 s of its own CPU time (start-up
                          included), a fraction of what the budget allows
  guess_false_on_timeout  stops after 3 s of CPU time and then answers FALSE
  guess_true_on_timeout   stops after 3 s of CPU time and then answers TRUE

The audit runner copies this file and equips_copy.py into each case's solver
directory, because the solver sandbox cannot read eval/test/.
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


def _minimal_cp_sat(eq, variables, constraints, universal_constraints, time_limit_s):
    cp = eq.cp_model
    model = cp.CpModel()
    var_map = eq._build_cp_sat_vars(model, variables)
    for c in list(constraints) + [None] + list(universal_constraints):
        if c is None:
            continue
        is_eq = getattr(c, "is_equality", False)
        if eq._cp_sat_is_constant(var_map, c.coeffs):
            holds = c.rhs == 0 if is_eq else 0 <= c.rhs
            if not holds:
                return None
            continue
        expr = eq._cp_sat_expr(var_map, c.coeffs)
        if is_eq:
            model.Add(expr == int(c.rhs))
        else:
            model.Add(expr <= int(c.rhs))
    model.Minimize(sum(var_map[v.name] for v in variables))
    solver = eq._new_cp_sat_solver(time_limit_s)
    status = solver.Solve(model)
    if status in (cp.OPTIMAL, cp.FEASIBLE):
        return {name: int(solver.Value(var)) for name, var in var_map.items()}
    if status == cp.INFEASIBLE:
        return None
    return eq._TIMEOUT


def _minimal_highs(eq, variables, constraints, universal_constraints, time_limit_s):
    if not eq._constant_constraints_feasible(constraints, universal_constraints):
        return None
    highs = eq._new_highs(time_limit_s)
    names = eq._add_integer_vars(highs, variables)
    eq._add_constraints(highs, names, constraints)
    eq._add_universal_constraints(highs, names, universal_constraints)
    for col in range(len(names)):
        highs.changeColCost(col, 1.0)
    highs.run()
    status = highs.getModelStatus()
    if status in (eq.hp.HighsModelStatus.kOptimal, eq.hp.HighsModelStatus.kModelEmpty):
        return eq._extract_solution(highs, names)
    if status == eq.hp.HighsModelStatus.kInfeasible:
        return None
    return eq._TIMEOUT


def install_minimal_responses(eq, minimal) -> None:
    original = eq._solve_qip_internal

    def internal(problem, timeout_s, stats, depth):
        if problem.variables and len({v.level for v in problem.variables}) == 1 \
                and problem.variables[0].quantifier == "E":
            start = time.time()
            sol = minimal(eq, problem.variables, problem.constraints, problem.universal_constraints, timeout_s)
            if sol is eq._TIMEOUT:
                return {"status": "TIMEOUT", "assignment": None, "runtime": time.time() - start}
            return {"status": "SAT" if sol is not None else "UNSAT", "assignment": sol,
                    "runtime": time.time() - start}
        return original(problem, timeout_s, stats, depth)

    eq._solve_qip_internal = internal


def _ceil_div(num: int, den: int) -> int:
    return -((-num) // den)


def _floor_div(num: int, den: int) -> int:
    return num // den


def main() -> None:
    variant, instance, answer_path = sys.argv[1], sys.argv[2], sys.argv[3]
    limit = float(os.environ.get("QIP_WALL_LIMIT_S", "600"))
    if variant in ("cpsat_all", "cpsat_gf2", "cpsat_minresp"):
        os.environ["EQUIPS_MIP_BACKEND"] = "cp-sat"
    elif variant == "highs_only":
        os.environ["EQUIPS_MIP_BACKEND"] = "highs"
    else:
        os.environ["EQUIPS_MIP_BACKEND"] = "auto"

    import equips_copy as eq
    from data.qlp import parse_qlp

    if variant in ("cpsat_all", "cpsat_gf2", "cpsat_minresp"):
        eq._solve_ip_feasible = eq._solve_cp_sat_feasible
    if variant == "minresp":
        install_minimal_responses(eq, _minimal_highs)
    if variant == "cpsat_minresp":
        install_minimal_responses(eq, _minimal_cp_sat)
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
    timeout = limit
    if variant == "short_timeout":
        timeout = max(0.1, 3.0 - time.process_time())
    elif variant in ("guess_false_on_timeout", "guess_true_on_timeout"):
        timeout = max(0.1, 3.0 - time.process_time())
    result = eq.solve_qip(problem, timeout_s=timeout)
    answer = {"SAT": "TRUE", "UNSAT": "FALSE"}.get(result["status"], "UNKNOWN")
    if answer == "UNKNOWN" and variant == "guess_false_on_timeout":
        answer = "FALSE"
    if answer == "UNKNOWN" and variant == "guess_true_on_timeout":
        answer = "TRUE"
    Path(answer_path).write_text(json.dumps({"answer": answer}))


if __name__ == "__main__":
    main()
