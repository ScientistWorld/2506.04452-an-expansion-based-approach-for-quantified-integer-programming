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

    import numpy as np
    var_names = list(vars_dict.keys())
    highs = hp.Highs()
    highs.setOptionValue("log_to_console", False)
    highs.setOptionValue("output_flag", False)

    n_vars = len(var_names)
    col_low = np.array([float(vars_dict[n].lower) for n in var_names], dtype=np.float64)
    col_up = np.array([float(vars_dict[n].upper) for n in var_names], dtype=np.float64)
    highs.addVars(n_vars, col_low, col_up)
    for i, n in enumerate(var_names):
        highs.passColName(i, n)
    for i in range(n_vars):
        highs.changeColIntegrality(i, hp.HighsVarType.kInteger)

    if constraints:
        for c in constraints:
            row_idxs = []
            row_vals = []
            for n in var_names:
                coeff = c.coeffs.get(n, 0)
                if coeff != 0:
                    row_idxs.append(var_names.index(n))
                    row_vals.append(float(coeff))
            if row_idxs:
                rhs = float(c.rhs)
                if c.is_equality:
                    highs.addRow(np.array(row_idxs, dtype=np.int64),
                                np.array(row_vals, dtype=np.float64),
                                rhs, rhs)
                else:
                    highs.addRow(np.array(row_idxs, dtype=np.int64),
                                np.array(row_vals, dtype=np.float64),
                                -hp.kHighsInf, rhs)

    for uc in uconstrs:
        row_idxs = []
        row_vals = []
        for n in uc.coeffs:
            if n in vars_dict:
                row_idxs.append(var_names.index(n))
                row_vals.append(float(uc.coeffs[n]))
        if row_idxs:
            highs.addRow(np.array(row_idxs, dtype=np.int64),
                        np.array(row_vals, dtype=np.float64),
                        -hp.kHighsInf, float(uc.rhs))

    try:
        status = highs.run()
    except Exception:
        return False
    if status != hp.HighsStatus.kOk:
        return False
    model_status = highs.getModelStatus()
    return model_status in (hp.HighsModelStatus.kOptimal,
                            hp.HighsModelStatus.kInfeasible,
                            hp.HighsModelStatus.kUnboundedOrInfeasible,
                            hp.HighsModelStatus.kFeasible,
                            hp.HighsModelStatus.kMipSolution)


def enumerate_baseline(problem: QIPProblem, timeout_s: float = 10.0) -> dict:
    """
    Naive baseline: enumerate all existential outer assignments.
    For each assignment, check if the IP with universals is still feasible.

    For QRandomParity: exists x (outer), forall u, exists inner : check if exists x
    such that for all u, the inner exists can find a satisfying assignment.
    This means: for the given x, the universal cannot force a contradiction.
    """
    import numpy as np
    start = time.time()

    # Separate existential and universal variables
    existentials = [v for v in problem.variables if v.quantifier == 'E']
    universals = [v for v in problem.variables if v.quantifier == 'A']

    print(f"    Baseline: {len(existentials)} existentials, {len(universals)} universals")

    # For QRandomParity, outer existentials are x_1..x_n (domain 0..1)
    # Enumerate only the outer (first n) existential assignments
    outer_existentials = [v for v in existentials if v.name.startswith('x_')]
    inner_existentials = [v for v in existentials if not v.name.startswith('x_')]

    if not outer_existentials:
        # Fallback: enumerate all existentials (will be very slow)
        outer_existentials = existentials

    # Check domain sizes
    for v in outer_existentials:
        if v.upper - v.lower > 5:  # Limit enumeration
            return {
                'status': 'UNKNOWN',
                'runtime': time.time() - start,
                'reason': f'domain too large ({v.name}: {v.lower}..{v.upper})'
            }

    domains = [range(v.lower, v.upper + 1) for v in outer_existentials]
    var_names_outer = [v.name for v in outer_existentials]

    for combo in itertools.product(*domains):
        if time.time() - start > timeout_s:
            return {
                'status': 'TIMEOUT',
                'runtime': time.time() - start
            }

        assignment = dict(zip(var_names_outer, combo))

        # Build IP with this x assignment fixed
        # Variables: all existentials + universals
        all_vars = outer_existentials + inner_existentials + universals
        all_var_names = [v.name for v in all_vars]
        var_dict = {v.name: v for v in all_vars}

        highs = hp.Highs()
        highs.setOptionValue("log_to_console", False)
        highs.setOptionValue("output_flag", False)

        n_vars = len(all_vars)
        col_low = np.array([float(v.lower) for v in all_vars], dtype=np.float64)
        col_up = np.array([float(v.upper) for v in all_vars], dtype=np.float64)
        highs.addVars(n_vars, col_low, col_up)
        for i, n in enumerate(all_var_names):
            highs.passColName(i, n)
        for i in range(n_vars):
            highs.changeColIntegrality(i, hp.HighsVarType.kInteger)

        # Fix outer existential vars to the enumerated values
        for name, val in assignment.items():
            idx = all_var_names.index(name)
            highs.changeColBounds(idx, float(val), float(val))

        # Add constraints (inner existentials + universals)
        for c in problem.constraints:
            row_idxs = []
            row_vals = []
            for n in all_var_names:
                coeff = c.coeffs.get(n, 0)
                if coeff != 0:
                    row_idxs.append(all_var_names.index(n))
                    row_vals.append(float(coeff))
            if row_idxs:
                rhs = float(c.rhs)
                if c.is_equality:
                    highs.addRow(rhs, rhs, len(row_idxs),
                                np.array(row_idxs, dtype=np.int32),
                                np.array(row_vals, dtype=np.float64))
                else:
                    highs.addRow(-hp.kHighsInf, rhs, len(row_idxs),
                                np.array(row_idxs, dtype=np.int32),
                                np.array(row_vals, dtype=np.float64))

        try:
            status = highs.run()
        except Exception:
            continue
        if status != hp.HighsStatus.kOk:
            continue
        model_status = highs.getModelStatus()
        # kOptimal means feasible solution found
        if model_status == hp.HighsModelStatus.kOptimal:
            # IP is feasible with this x assignment
            # Universal cannot force a contradiction
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
