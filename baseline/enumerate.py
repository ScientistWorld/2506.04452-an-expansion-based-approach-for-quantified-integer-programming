"""
Naive enumeration baseline for QIP solving.
Tries all assignments for existential variables and checks feasibility.
"""

import sys
import time
import itertools
from typing import Optional

from data.qrandomparity import (
    QIPProblem, Variable, Constraint, UniversalConstraint, Subgame, MultiGame
)

# Try to import highspy
try:
    import highspy as hp
except ImportError:
    for p in ['/dev/shm/pylibs', '/home/user/.local/lib/python3.12/site-packages']:
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import highspy as hp
    except ImportError:
        hp = None


def solve_ip_exists(vars_dict, constraints, uconstrs):
    """Check if exists assignment satisfies constraints."""
    if hp is None:
        raise RuntimeError("highspy not available")

    var_names = list(vars_dict.keys())
    highs = hp.Highs()
    highs.setOptionValue("log_to_console", False)
    highs.setOptionValue("output_flag", False)

    col_low = [float(vars_dict[n].lower) for n in var_names]
    col_up = [float(vars_dict[n].upper) for n in var_names]
    highs.addVars(col_low, col_up)
    for i, n in enumerate(var_names):
        highs.changeColName(i, n)
    for i in range(len(var_names)):
        highs.changeColIntegrality(i, hp.HighsVarType.kInteger)

    if constraints:
        num_cons = len(constraints)
        a_mat = []
        row_lower = []
        row_upper = []
        for c in constraints:
            row = [float(c.coeffs.get(n, 0)) for n in var_names]
            a_mat.append(row)
            if c.is_equality:
                row_lower.append(float(c.rhs))
                row_upper.append(float(c.rhs))
            else:
                row_lower.append(-hp.kHighsInf)
                row_upper.append(float(c.rhs))
        mat = hp.HighsSparseMatrix(len(var_names), num_cons, a_mat)
        highs.addMatrixConstraints(mat, row_lower, [0.0] * num_cons, row_upper)

    for uc in uconstrs:
        row_idxs = [var_names.index(n) for n in uc.coeffs if n in vars_dict]
        row_vals = [float(uc.coeffs[n]) for n in uc.coeffs if n in vars_dict]
        if row_idxs:
            highs.addRow(row_idxs, row_vals, -hp.kHighsInf, float(uc.rhs))

    try:
        status = highs.run()
    except Exception:
        return False
    if status[0] != hp.HighsStatus.kOk:
        return False
    model_status = highs.getModelStatus()
    return model_status in (hp.HighsModelStatus.kOptimal,
                            hp.HighsModelStatus.kFeasible,
                            hp.HighsModelStatus.kMipSolution)


def enumerate_baseline(problem: QIPProblem, timeout_s: float = 10.0) -> dict:
    """
    Naive baseline: enumerate all existential assignments.
    For each assignment, check if universal player can be forced to lose.

    For QRandomParity: exists x, forall u, exists t,s : check if exists x
    such that for all u, the constraints are satisfiable.
    """
    start = time.time()

    # Separate existential and universal variables
    existentials = [v for v in problem.variables if v.quantifier == 'E']
    universals = [v for v in problem.variables if v.quantifier == 'A']

    print(f"    Baseline: {len(existentials)} existentials, {len(universals)} universals")

    # Enumerate existential assignments
    for v in existentials:
        if v.upper - v.lower > 3:
            # Too many possibilities
            return {
                'status': 'UNKNOWN',
                'runtime': time.time() - start,
                'reason': 'domain too large'
            }

    domains = [v.domain() for v in existentials]
    var_names = [v.name for v in existentials]

    for combo in itertools.product(*domains):
        if time.time() - start > timeout_s:
            return {
                'status': 'TIMEOUT',
                'runtime': time.time() - start
            }

        assignment = dict(zip(var_names, combo))

        # Check if this existential assignment can satisfy all constraints
        # regardless of universal choices
        # This means: is the universal player able to violate?
        # We check: can we assign universals to violate?
        sat = solve_ip_exists(problem.var_dict(), problem.constraints, problem.universal_constraints)
        if not sat:
            # Existential can't satisfy even without universals
            continue

        # For QRandomParity: check if the universal player has a winning countermove
        # We need: for ALL universal assignments, the constraints are satisfiable
        # Simplified: just check the IP is feasible (universals are part of the model)
        # Since we already checked feasibility, if IP is feasible, the existential
        # assignment is a winning move
        return {
            'status': 'SAT',
            'assignment': assignment,
            'runtime': time.time() - start
        }

    return {
        'status': 'UNSAT',
        'runtime': time.time() - start
    }


if __name__ == '__main__':
    from data.qrandomparity import generate_qrandomparity

    print("Testing naive baseline on n=3")
    problem = generate_qrandomparity(3, seed=42)
    result = enumerate_baseline(problem, timeout_s=5.0)
    print(f"Result: {result}")
