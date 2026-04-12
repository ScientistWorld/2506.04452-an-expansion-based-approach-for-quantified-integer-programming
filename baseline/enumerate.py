"""
Exact enumeration baseline for small `exists X forall U exists Z` QIPs.
"""

from __future__ import annotations

import itertools
import time
from typing import Optional

import highspy as hp
import numpy as np

from data.qrandomparity import Constraint, QIPProblem, UniversalConstraint, Variable


def _sorted_blocks(problem: QIPProblem):
    blocks = []
    for level in sorted({var.level for var in problem.variables}):
        level_vars = [var for var in problem.variables if var.level == level]
        blocks.append(type("Block", (), {"variables": level_vars, "quantifier": level_vars[0].quantifier}))
    return blocks


def _enumerate_block(block_vars):
    domains = [range(var.lower, var.upper + 1) for var in block_vars]
    for values in itertools.product(*domains):
        yield {var.name: value for var, value in zip(block_vars, values)}


def _new_highs(time_limit_s: Optional[float] = None) -> hp.Highs:
    highs = hp.Highs()
    highs.setOptionValue("log_to_console", False)
    highs.setOptionValue("output_flag", False)
    if time_limit_s is not None:
        highs.setOptionValue("time_limit", max(0.1, float(time_limit_s)))
    return highs


def _add_integer_vars(highs: hp.Highs, variables: list[Variable]) -> list[str]:
    names = [var.name for var in variables]
    if not names:
        return names
    highs.addVars(
        len(variables),
        np.array([float(v.lower) for v in variables], dtype=np.float64),
        np.array([float(v.upper) for v in variables], dtype=np.float64),
    )
    for idx, var in enumerate(variables):
        highs.passColName(idx, var.name)
        highs.changeColIntegrality(idx, hp.HighsVarType.kInteger)
    return names


def _add_constraints(highs: hp.Highs, var_names: list[str], constraints: list[Constraint]) -> None:
    index = {name: idx for idx, name in enumerate(var_names)}
    for constraint in constraints:
        row_idx = []
        row_val = []
        for name, coeff in constraint.coeffs.items():
            if name in index:
                row_idx.append(index[name])
                row_val.append(float(coeff))
        lower = float(constraint.rhs) if constraint.is_equality else -hp.kHighsInf
        upper = float(constraint.rhs)
        highs.addRow(
            lower,
            upper,
            len(row_idx),
            np.array(row_idx, dtype=np.int64),
            np.array(row_val, dtype=np.float64),
        )


def _add_universal_constraints(
    highs: hp.Highs,
    var_names: list[str],
    constraints: list[UniversalConstraint],
) -> None:
    index = {name: idx for idx, name in enumerate(var_names)}
    for constraint in constraints:
        row_idx = []
        row_val = []
        for name, coeff in constraint.coeffs.items():
            if name in index:
                row_idx.append(index[name])
                row_val.append(float(coeff))
        highs.addRow(
            -hp.kHighsInf,
            float(constraint.rhs),
            len(row_idx),
            np.array(row_idx, dtype=np.int64),
            np.array(row_val, dtype=np.float64),
        )


def _constant_constraints_feasible(
    constraints: list[Constraint],
    universal_constraints: Optional[list[UniversalConstraint]] = None,
) -> bool:
    for constraint in constraints:
        if constraint.coeffs:
            continue
        if constraint.is_equality:
            if constraint.rhs != 0:
                return False
        elif 0 > constraint.rhs:
            return False
    if universal_constraints is not None:
        for constraint in universal_constraints:
            if constraint.coeffs:
                continue
            if 0 > constraint.rhs:
                return False
    return True


def _solve_ip_feasible(
    variables: list[Variable],
    constraints: list[Constraint],
    universal_constraints: list[UniversalConstraint],
    time_limit_s: Optional[float] = None,
) -> Optional[dict[str, int]]:
    if not _constant_constraints_feasible(constraints, universal_constraints):
        return None
    highs = _new_highs(time_limit_s)
    names = _add_integer_vars(highs, variables)
    _add_constraints(highs, names, constraints)
    _add_universal_constraints(highs, names, universal_constraints)
    run_status = highs.run()
    model_status = highs.getModelStatus()
    if run_status != hp.HighsStatus.kOk:
        return None
    if model_status == hp.HighsModelStatus.kInfeasible:
        return None
    if model_status not in (
        hp.HighsModelStatus.kOptimal,
        hp.HighsModelStatus.kSolutionLimit,
        hp.HighsModelStatus.kModelEmpty,
    ):
        return None
    solution = highs.getSolution()
    if solution is None or solution.col_value is None:
        return None
    return {name: int(round(solution.col_value[i])) for i, name in enumerate(names)}


def enumerate_baseline(problem: QIPProblem, timeout_s: float = 30.0) -> dict:
    start = time.time()
    blocks = _sorted_blocks(problem)
    if len(blocks) != 3 or blocks[0].quantifier != "E" or blocks[1].quantifier != "A" or blocks[2].quantifier != "E":
        raise NotImplementedError("Baseline supports only exists-forall-exists problems.")

    outer_block = blocks[0].variables
    universal_block = blocks[1].variables

    for outer_assignment in _enumerate_block(outer_block):
        if time.time() - start > timeout_s:
            return {"status": "TIMEOUT", "runtime": time.time() - start}

        valid_for_all = True
        for universal_assignment in _enumerate_block(universal_block):
            reduced = problem.substitute(outer_assignment | universal_assignment)
            if _solve_ip_feasible(reduced.variables, reduced.constraints, reduced.universal_constraints) is None:
                valid_for_all = False
                break

        if valid_for_all:
            return {"status": "SAT", "assignment": outer_assignment, "runtime": time.time() - start}

    return {"status": "UNSAT", "runtime": time.time() - start}
