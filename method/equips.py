"""
EQuIPS: Expansion-based Quantified Integer Programming Solver

Implementation of the paper:
"An Expansion-Based Approach for Quantified Integer Programming"
(Hartisch & Chew, 2025)

Uses Counterexample-Guided Abstraction Refinement (CEGAR) adapted from QBF solving.
The IP subproblems are solved using HiGHS (open-source LP/MIP solver).

Usage:
    from method.equips import solve_qip
    result = solve_qip(problem)
    # result = {'status': 'SAT' or 'UNSAT', 'assignment': {...}, 'runtime': float}
"""

import sys
import time
from fractions import Fraction
from math import gcd
from dataclasses import dataclass, field
from typing import Optional

# Import data module for QIPProblem, etc.
from data.qrandomparity import (
    QIPProblem, Variable, Constraint, UniversalConstraint,
    Subgame, MultiGame
)

# Import highspy (HiGHS)
try:
    import highspy as hp
    import numpy as np
except ImportError:
    for p in ['/dev/shm/pylibs', '/home/user/.local/lib/python3.12/site-packages']:
        if p not in sys.path:
            sys.path.insert(0, p)
    try:
        import highspy as hp
        import numpy as np
    except ImportError:
        hp = None
        np = None


def compute_min_lhs(vars_dict: dict[str, Variable], coeffs: dict[str, int]) -> int:
    """Compute min value of sum(a_i * x_i) over domain D."""
    total = 0
    for name, coeff in coeffs.items():
        if name not in vars_dict:
            continue
        v = vars_dict[name]
        if coeff >= 0:
            total += coeff * v.lower
        else:
            total += coeff * v.upper
    return total


def compute_violation_gap(constraint: Constraint, vars_dict: dict[str, Variable]) -> float:
    """
    Compute a positive value r such that for any assignment x in D:
    sum(a*x) > b  <=>  sum(a*x) >= b + r

    For integer coefficients and RHS, r=1 works.
    For rational coefficients, compute LCD of denominators.
    """
    fractions = [Fraction(constraint.rhs, 1)]
    for name, coeff in constraint.coeffs.items():
        fractions.append(Fraction(coeff, 1))

    lcm_val = 1
    for f in fractions:
        if f.denominator > 1:
            lcm_val = lcm_val * f.denominator // gcd(lcm_val, f.denominator)

    return 1.0 / lcm_val if lcm_val > 1 else 1.0


def build_and_solve_ip(vars_dict: dict[str, Variable],
                       constraints: list[Constraint],
                       universal_constraints: list[UniversalConstraint],
                       objective: Optional[dict[str, int]] = None,
                       sense: str = "min",
                       extra_vars: Optional[dict] = None) -> Optional[dict]:
    """
    Build and solve an IP using the HiGHS Python API.

    extra_vars: dict of name -> (lower, upper, integrality) for extra variables
    Returns solution dict or None.
    """
    if hp is None or np is None:
        raise RuntimeError("highspy (HiGHS) not available")

    highs = hp.Highs()
    highs.setOptionValue("log_to_console", False)
    highs.setOptionValue("output_flag", False)
    highs.setOptionValue("time_limit", 5.0)  # 5 second limit per IP solve

    var_names = list(vars_dict.keys())
    n_vars = len(var_names)

    # Add problem variables
    if n_vars > 0:
        col_low = np.array([float(vars_dict[name].lower) for name in var_names], dtype=np.float64)
        col_up = np.array([float(vars_dict[name].upper) for name in var_names], dtype=np.float64)
        status = highs.addVars(n_vars, col_low, col_up)
        if status != hp.HighsStatus.kOk:
            return None

        for i, name in enumerate(var_names):
            highs.passColName(i, name)

        # Mark as integer
        for i in range(n_vars):
            highs.changeColIntegrality(i, hp.HighsVarType.kInteger)

    # Add extra variables (y, v, etc.)
    extra_indices = {}
    if extra_vars:
        for name, (lo, hi, is_int) in extra_vars.items():
            col_l = np.array([float(lo)], dtype=np.float64)
            col_u = np.array([float(hi)], dtype=np.float64)
            idx = highs.addVars(1, col_l, col_u)
            if idx != hp.HighsStatus.kOk:
                return None
            n = highs.getNumCol() - 1
            highs.passColName(n, name)
            if is_int:
                highs.changeColIntegrality(n, hp.HighsVarType.kInteger)
            extra_indices[name] = n

    # Add problem constraints
    for c in constraints:
        row_idxs = []
        row_vals = []
        for name, coeff in c.coeffs.items():
            if name in var_names:
                row_idxs.append(var_names.index(name))
                row_vals.append(float(coeff))
        if c.is_equality:
            lower = float(c.rhs)
            upper = float(c.rhs)
        else:
            lower = -hp.kHighsInf
            upper = float(c.rhs)
        if row_idxs:
            highs.addRow(lower, upper, len(row_idxs),
                        np.array(row_idxs, dtype=np.int64),
                        np.array(row_vals, dtype=np.float64))

    # Add universal constraints
    for uc in universal_constraints:
        row_idxs = []
        row_vals = []
        for name, coeff in uc.coeffs.items():
            if name in vars_dict:
                row_idxs.append(var_names.index(name))
                row_vals.append(float(coeff))
        if row_idxs:
            highs.addRow(-hp.kHighsInf, float(uc.rhs), len(row_idxs),
                        np.array(row_idxs, dtype=np.int64),
                        np.array(row_vals, dtype=np.float64))

    # Set objective
    if objective:
        for i, name in enumerate(var_names):
            highs.changeColCost(i, float(objective.get(name, 0)))
        if sense == "min":
            highs.changeObjectiveSense(hp.ObjSense.kMinimize)
        else:
            highs.changeObjectiveSense(hp.ObjSense.kMaximize)

    # Solve
    try:
        status = highs.run()
    except Exception:
        return None

    if status != hp.HighsStatus.kOk:
        return None

    model_status = highs.getModelStatus()
    # Feasible statuses: kOptimal, kSolutionLimit, kModelEmpty
    # kInfeasible / kUnboundedOrInfeasible mean no solution exists
    if model_status not in (hp.HighsModelStatus.kOptimal,
                           hp.HighsModelStatus.kSolutionLimit,
                           hp.HighsModelStatus.kModelEmpty):
        return None

    # Try to get solution
    try:
        sol = highs.getSolution()
    except Exception:
        return None

    # Check if solution is valid
    if not sol.col_value:
        return None

    result = {}
    for i, name in enumerate(var_names):
        result[name] = int(round(sol.col_value[i]))
    return result


def solve_ip_feasible(vars_dict: dict[str, Variable],
                      constraints: list[Constraint],
                      universal_constraints: list[UniversalConstraint],
                      objective: Optional[dict[str, int]] = None,
                      sense: str = "min") -> Optional[dict[str, int]]:
    """Find x satisfying all constraints. Problem (1) from paper."""
    return build_and_solve_ip(vars_dict, constraints, universal_constraints, objective, sense)


def solve_ip_violate_all(vars_dict: dict[str, Variable],
                         constraints: list[Constraint],
                         universal_constraints: list[UniversalConstraint]) -> Optional[dict[str, int]]:
    """
    Find assignment x that VIOLATES all constraint systems.
    For universal quantifier case in wins1.
    This is Problem (2) from the paper.
    """
    if hp is None or np is None:
        raise RuntimeError("highspy (HiGHS) not available")

    n_vars = len(vars_dict)
    var_names = list(vars_dict.keys())

    # Compute L and r for each constraint
    L = [float(compute_min_lhs(vars_dict, c.coeffs)) for c in constraints]
    r = [compute_violation_gap(c, vars_dict) for c in constraints]
    n_cons = len(constraints)

    # Extra variables: v, v_l, y_l
    extra_vars = {
        '_v': (1.0, 1.0, True),  # v must be 1
    }
    for l in range(n_cons):
        extra_vars[f'_vl{l}'] = (0.0, 1.0, True)
        extra_vars[f'_y{l}'] = (0.0, 1.0, True)

    # Add constraints: call build_and_solve_ip and add constraints
    highs = hp.Highs()
    highs.setOptionValue("log_to_console", False)
    highs.setOptionValue("output_flag", False)
    highs.setOptionValue("time_limit", 5.0)  # 5 second limit per IP solve

    # Add x variables
    if n_vars > 0:
        col_low = np.array([float(vars_dict[name].lower) for name in var_names], dtype=np.float64)
        col_up = np.array([float(vars_dict[name].upper) for name in var_names], dtype=np.float64)
        highs.addVars(n_vars, col_low, col_up)
        for i, name in enumerate(var_names):
            highs.passColName(i, name)
        for i in range(n_vars):
            highs.changeColIntegrality(i, hp.HighsVarType.kInteger)

    # Add extra variables
    extra_indices = {}
    for name, (lo, hi, is_int) in extra_vars.items():
        col_l = np.array([float(lo)], dtype=np.float64)
        col_u = np.array([float(hi)], dtype=np.float64)
        idx = highs.addVars(1, col_l, col_u)
        n = highs.getNumCol() - 1
        highs.passColName(n, name)
        if is_int:
            highs.changeColIntegrality(n, hp.HighsVarType.kInteger)
        extra_indices[name] = n

    # Constraint (2a): -A_l*x - (L_l - b_l - r_l)*y_l >= -L_l
    for l, c in enumerate(constraints):
        L_l = L[l]
        rhs_adj = L_l - float(c.rhs) - r[l]

        row_idxs = []
        row_vals = []

        # -A_l*x
        for name, coeff in c.coeffs.items():
            if name in var_names:
                row_idxs.append(var_names.index(name))
                row_vals.append(float(-coeff))

        # -(L_l - b_l - r_l)*y_l
        row_idxs.append(extra_indices[f'_y{l}'])
        row_vals.append(float(-rhs_adj))

        highs.addRow(float(-L_l), hp.kHighsInf, len(row_idxs),
                    np.array(row_idxs, dtype=np.int64),
                    np.array(row_vals, dtype=np.float64))

    # Constraint (2b): v_l <= y_l  (v_l - y_l <= 0)
    for l in range(n_cons):
        highs.addRow(-hp.kHighsInf, 0.0, 2,
            np.array([extra_indices[f'_vl{l}'], extra_indices[f'_y{l}']], dtype=np.int64),
            np.array([1.0, -1.0], dtype=np.float64))

    # Constraint (2c): v <= v_l  (v - v_l <= 0)
    for l in range(n_cons):
        highs.addRow(-hp.kHighsInf, 0.0, 2,
            np.array([extra_indices['_v'], extra_indices[f'_vl{l}']], dtype=np.int64),
            np.array([1.0, -1.0], dtype=np.float64))

    # Constraint (2d): v >= 1  (v >= 1)
    highs.addRow(1.0, hp.kHighsInf, 1,
        np.array([extra_indices['_v']], dtype=np.int64),
        np.array([1.0], dtype=np.float64))

    # Add universal constraints (2e)
    for uc in universal_constraints:
        row_idxs = []
        row_vals = []
        for name, coeff in uc.coeffs.items():
            if name in vars_dict:
                row_idxs.append(var_names.index(name))
                row_vals.append(float(coeff))
        if row_idxs:
            highs.addRow(-hp.kHighsInf, float(uc.rhs), len(row_idxs),
                        np.array(row_idxs, dtype=np.int64),
                        np.array(row_vals, dtype=np.float64))

    # Objective: maximize v
    for i in range(highs.getNumCol()):
        if i == extra_indices['_v']:
            highs.changeColCost(i, 1.0)
        else:
            highs.changeColCost(i, 0.0)
    highs.changeObjectiveSense(hp.ObjSense.kMaximize)

    # Solve
    try:
        status = highs.run()
    except Exception:
        return None

    if status != hp.HighsStatus.kOk:
        return None

    model_status = highs.getModelStatus()
    if model_status not in (hp.HighsModelStatus.kOptimal,
                           hp.HighsModelStatus.kSolutionLimit):
        return None

    try:
        sol = highs.getSolution()
    except Exception:
        return None

    if not sol.col_value:
        return None

    v_val = sol.col_value[extra_indices['_v']]
    if v_val >= 0.99:  # v = 1 means we found violating assignment
        result = {}
        for i, name in enumerate(var_names):
            result[name] = int(round(sol.col_value[i]))
        return result
    return None


def wins1(multigame: MultiGame) -> Optional[dict[str, int]]:
    """
    Solve a multi-game where all subgames are quantifier-free.
    Returns a winning move for the outer quantifier, or None.
    Algorithm 2 from the paper.
    """
    Q = multigame.outer_quantifier
    X = multigame.outer_vars
    vars_dict = {v.name: v for v in X}

    # Collect constraints from all subgames
    all_constraints = []
    for sg in multigame.subgames:
        if sg.problem:
            all_constraints.extend(sg.problem.constraints)
        else:
            all_constraints.extend(sg.constraints)

    if Q == 'E':
        return solve_ip_feasible(vars_dict, all_constraints,
                              multigame.universal_constraints)
    else:
        return solve_ip_violate_all(vars_dict, all_constraints,
                                   multigame.universal_constraints)


def extract_assignment(full_assignment: dict[str, int], var_names: list[str]) -> dict[str, int]:
    """Extract assignment for specific variables."""
    return {name: full_assignment[name] for name in var_names if name in full_assignment}


def equips(multigame: MultiGame, depth: int = 0, max_depth: int = 200,
            timeout_s: float = float('inf'), elapsed_start: float = None) -> Optional[dict[str, int]]:
    """
    EQuIPS: Expansion-based QIP Solver (Algorithm 1 from the paper).

    Finds a winning move for the outer quantifier block in a multi-game.
    Uses CEGAR: iteratively solve abstractions, find counter-moves, refine.
    """
    if elapsed_start is None:
        elapsed_start = time.time()

    if depth > max_depth:
        return None

    # Check timeout
    if time.time() - elapsed_start > timeout_s:
        return None

    # Line 1: If all subgames are quantifier-free, call wins1
    all_qf = all(sg.is_quantifier_free() for sg in multigame.subgames)
    if all_qf:
        outer_names = [v.name for v in multigame.outer_vars]
        result = wins1(multigame)
        if result is not None:
            return extract_assignment(result, outer_names)
        return None

    # Line 2: Initialize empty abstraction
    abstraction = MultiGame(
        outer_quantifier=multigame.outer_quantifier,
        outer_vars=multigame.outer_vars,
        subgames=[],
        universal_constraints=multigame.universal_constraints
    )

    iteration = 0
    while True:
        iteration += 1
        if iteration > 5000:
            return None

        # Check timeout inside CEGAR loop
        if time.time() - elapsed_start > timeout_s:
            return None

        # Line 4: Solve current abstraction
        tau = equips(abstraction, depth + 1, max_depth, timeout_s, elapsed_start)
        if tau is None:
            # Line 5: No winning move
            return None

        # Lines 8-11: Check for counter-moves
        lambda_val = -1
        for l, sg in enumerate(multigame.subgames):
            if sg.is_quantifier_free():
                continue

            sub_qip = sg.problem
            if sub_qip is None:
                continue

            # Substitute current move into subgame
            reduced = sub_qip.substitute(tau)

            if reduced.variables:
                # Still has quantifiers — recursively solve for counter-move
                sub_multigame = MultiGame(
                    outer_quantifier=reduced.outer_quantifier(),
                    outer_vars=reduced.variables,
                    subgames=[Subgame(problem=reduced)],
                    universal_constraints=reduced.universal_constraints
                )
                counter = equips(sub_multigame, depth + 1, max_depth, timeout_s, elapsed_start)
                if counter is not None:
                    # Found a counter-move — reduced game is won by opponent
                    lambda_val = l
                    break
            else:
                # Quantifier-free after substitution
                subgame_multigame = MultiGame(
                    outer_quantifier=reduced.outer_quantifier(),
                    outer_vars=[],
                    subgames=[Subgame(constraints=reduced.constraints)],
                    universal_constraints=reduced.universal_constraints
                )
                counter = wins1(subgame_multigame)
                if counter is not None:
                    lambda_val = l
                    break

        # Line 11: No counter-move -> tau is winning
        if lambda_val == -1:
            return tau

        # Line 12: Refine abstraction
        counter_subgame = multigame.subgames[lambda_val]
        if counter_subgame.problem:
            substituted = counter_subgame.problem.substitute(tau)
            if substituted.variables:
                refined_subgame = Subgame(problem=substituted)
            else:
                refined_subgame = Subgame(constraints=substituted.constraints)
        else:
            refined_subgame = counter_subgame

        abstraction = MultiGame(
            outer_quantifier=abstraction.outer_quantifier,
            outer_vars=abstraction.outer_vars,
            subgames=abstraction.subgames + [refined_subgame],
            universal_constraints=abstraction.universal_constraints
        )


def solve_qip(problem: QIPProblem, timeout_s: float = 30.0) -> dict:
    """
    Solve a QIP problem.

    Returns dict with:
        - status: 'SAT' or 'UNSAT'
        - assignment: winning move (if SAT)
        - runtime: time in seconds
    """
    start = time.time()

    if not problem.variables:
        result = solve_ip_feasible({}, problem.constraints, problem.universal_constraints)
        return {
            'status': 'SAT' if result else 'UNSAT',
            'assignment': result,
            'runtime': time.time() - start
        }

    # Build initial multi-game matching the paper's Algorithm 1.
    # All variables are outer_vars; the CEGAR loop handles quantifier alternation
    # through recursive counter-move checking (equips calls itself on reduced
    # problems, and wins1 handles universal quantifier via solve_ip_violate_all).
    multigame = MultiGame(
        outer_quantifier=problem.outer_quantifier(),
        outer_vars=problem.variables,
        subgames=[Subgame(problem=problem)],
        universal_constraints=problem.universal_constraints
    )

    result = equips(multigame, depth=0, max_depth=200,
                    timeout_s=timeout_s, elapsed_start=start)

    return {
        'status': 'SAT' if result is not None else 'UNSAT',
        'assignment': result,
        'runtime': time.time() - start
    }


def solve_qip_optimization(problem: QIPProblem, timeout_s: float = 60.0) -> dict:
    """
    Solve a QIP optimization problem using binary search on objective value.
    Algorithm 3 from the paper.
    """
    start = time.time()

    if problem.objective is None:
        return solve_qip(problem, timeout_s)

    obj_coeffs = problem.objective

    # Compute bounds using variable domains
    vd = problem.var_dict()
    lb = sum(coeff * (vd[name].lower if coeff >= 0 else vd[name].upper)
              for name, coeff in obj_coeffs.items())
    ub = sum(coeff * (vd[name].upper if coeff >= 0 else vd[name].lower)
             for name, coeff in obj_coeffs.items())

    lower = min(lb, ub)
    upper = max(lb, ub)
    best_feasible = None
    best_value = None

    while upper - lower > 0:
        if time.time() - start > timeout_s:
            break

        z = (lower + upper) // 2 if lower != upper else lower
        test_problem = problem.with_objective_bound(z)
        remaining = timeout_s - (time.time() - start)
        result = solve_qip(test_problem, max(remaining, 0.1))

        if result['status'] == 'SAT':
            best_feasible = result['assignment']
            best_value = z
            if problem.objective_sense == "min":
                upper = z
            else:
                lower = z
        else:
            if problem.objective_sense == "min":
                lower = z + 1
            else:
                upper = z - 1

    return {
        'status': 'SAT' if best_feasible else 'UNSAT',
        'assignment': best_feasible,
        'optimal_value': best_value,
        'runtime': time.time() - start
    }


def solve_instance(n: int, seed: int, timeout_s: float = 30.0) -> dict:
    """Convenience: solve a QRandomParity instance."""
    from data.qrandomparity import generate_qrandomparity
    problem = generate_qrandomparity(n, seed)
    return solve_qip(problem, timeout_s)
