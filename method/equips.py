"""
EQuIPS: expansion-based quantified integer programming solver.

This implements the paper's CEGAR + expansion scheme for bounded QIP.
Quantifier-free subproblems are solved with open-source IP/CP-SAT backends.
"""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from math import gcd
from typing import Optional

import highspy as hp
import numpy as np
try:
    from ortools.sat.python import cp_model
except Exception:  # pragma: no cover - optional backend
    cp_model = None

from data.qrandomparity import Constraint, MultiGame, QIPProblem, Subgame, UniversalConstraint, Variable


_TIMEOUT = object()

# Optional random seed forwarded to HiGHS and CP-SAT (None keeps solver defaults).
SOLVER_SEED: Optional[int] = None


def _current_level(problem: QIPProblem) -> int:
    return min(v.level for v in problem.variables)


def _current_block(problem: QIPProblem) -> list[Variable]:
    level = _current_level(problem)
    return [v for v in problem.variables if v.level == level]


def _tail_problem(problem: QIPProblem) -> Optional[QIPProblem]:
    level = _current_level(problem)
    tail_vars = [v for v in problem.variables if v.level != level]
    if not tail_vars:
        return None
    return QIPProblem(
        variables=tail_vars,
        constraints=problem.constraints,
        universal_constraints=problem.universal_constraints,
        objective=problem.objective,
        objective_sense=problem.objective_sense,
    )


def _rename_coeffs(coeffs: dict[str, int], mapping: dict[str, str]) -> dict[str, int]:
    return {mapping.get(name, name): value for name, value in coeffs.items()}


def _rename_problem(problem: QIPProblem, suffix: str) -> QIPProblem:
    mapping = {v.name: f"{v.name}{suffix}" for v in problem.variables}
    return QIPProblem(
        variables=[
            Variable(mapping[v.name], v.lower, v.upper, v.quantifier, v.level)
            for v in problem.variables
        ],
        constraints=[
            Constraint(_rename_coeffs(c.coeffs, mapping), c.rhs, c.is_equality)
            for c in problem.constraints
        ],
        universal_constraints=[
            UniversalConstraint(_rename_coeffs(c.coeffs, mapping), c.rhs)
            for c in problem.universal_constraints
        ],
        objective=None if problem.objective is None else _rename_coeffs(problem.objective, mapping),
        objective_sense=problem.objective_sense,
    )


def _new_highs(time_limit_s: Optional[float] = None) -> hp.Highs:
    highs = hp.Highs()
    highs.setOptionValue("log_to_console", False)
    highs.setOptionValue("output_flag", False)
    if time_limit_s is not None:
        highs.setOptionValue("time_limit", max(0.1, float(time_limit_s)))
    if SOLVER_SEED is not None:
        highs.setOptionValue("random_seed", int(SOLVER_SEED))
    return highs


def _mip_backend() -> str:
    return os.environ.get("EQUIPS_MIP_BACKEND", "auto").strip().lower()


def _use_cp_sat(quantifier: str) -> bool:
    backend = _mip_backend()
    if backend in {"cp-sat", "cpsat"}:
        return True
    if backend == "auto":
        # The universal wins1 model is a pure feasibility/violation search with
        # many indicator-style choices. CP-SAT is a better open-source default
        # there, while HiGHS remains a good default for existential feasibility.
        return cp_model is not None and quantifier == "A"
    return False


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


def _add_universal_constraints(highs: hp.Highs, var_names: list[str], constraints: list[UniversalConstraint]) -> None:
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


def _extract_solution(highs: hp.Highs, var_names: list[str]) -> Optional[dict[str, int]]:
    if highs.getModelStatus() not in (
        hp.HighsModelStatus.kOptimal,
        hp.HighsModelStatus.kSolutionLimit,
        hp.HighsModelStatus.kModelEmpty,
    ):
        return None
    solution = highs.getSolution()
    if solution is None or solution.col_value is None:
        return None
    return {name: int(round(solution.col_value[i])) for i, name in enumerate(var_names)}


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


def _is_constraint_system_feasible(
    constraints: list[Constraint],
    universal_constraints: Optional[list[UniversalConstraint]] = None,
) -> bool:
    return _constant_constraints_feasible(constraints, universal_constraints)


def _build_cp_sat_vars(model: "cp_model.CpModel", variables: list[Variable]) -> dict[str, "cp_model.IntVar"]:
    return {
        variable.name: model.NewIntVar(int(variable.lower), int(variable.upper), variable.name)
        for variable in variables
    }


def _cp_sat_expr(var_map: dict[str, "cp_model.IntVar"], coeffs: dict[str, int]):
    terms = [int(coeff) * var_map[name] for name, coeff in coeffs.items() if name in var_map]
    return sum(terms) if terms else 0


def _cp_sat_is_constant(var_map: dict[str, "cp_model.IntVar"], coeffs: dict[str, int]) -> bool:
    return not any(name in var_map and coeff != 0 for name, coeff in coeffs.items())


def _new_cp_sat_solver(time_limit_s: Optional[float]) -> "cp_model.CpSolver":
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.log_search_progress = False
    if SOLVER_SEED is not None:
        solver.parameters.random_seed = int(SOLVER_SEED)
    if time_limit_s is not None:
        solver.parameters.max_time_in_seconds = max(0.1, float(time_limit_s))
    return solver


def _solve_cp_sat_feasible(
    variables: list[Variable],
    constraints: list[Constraint],
    universal_constraints: list[UniversalConstraint],
    time_limit_s: Optional[float] = None,
) -> object:
    if cp_model is None:
        raise RuntimeError("cp-sat backend requested but ortools is not installed")
    model = cp_model.CpModel()
    var_map = _build_cp_sat_vars(model, variables)
    for constraint in constraints:
        if _cp_sat_is_constant(var_map, constraint.coeffs):
            holds = constraint.rhs == 0 if constraint.is_equality else 0 <= constraint.rhs
            if not holds:
                return None
            continue
        expr = _cp_sat_expr(var_map, constraint.coeffs)
        if constraint.is_equality:
            model.Add(expr == int(constraint.rhs))
        else:
            model.Add(expr <= int(constraint.rhs))
    for constraint in universal_constraints:
        if _cp_sat_is_constant(var_map, constraint.coeffs):
            if 0 > constraint.rhs:
                return None
            continue
        model.Add(_cp_sat_expr(var_map, constraint.coeffs) <= int(constraint.rhs))

    solver = _new_cp_sat_solver(time_limit_s)
    status = solver.Solve(model)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {name: int(solver.Value(var)) for name, var in var_map.items()}
    if status == cp_model.INFEASIBLE:
        return None
    return _TIMEOUT


def _solve_cp_sat_violate_all(
    variables: list[Variable],
    constraint_sets: list[list[Constraint]],
    universal_constraints: list[UniversalConstraint],
    time_limit_s: Optional[float] = None,
) -> object:
    if cp_model is None:
        raise RuntimeError("cp-sat backend requested but ortools is not installed")
    model = cp_model.CpModel()
    var_map = _build_cp_sat_vars(model, variables)
    for constraint in universal_constraints:
        if _cp_sat_is_constant(var_map, constraint.coeffs):
            if 0 > constraint.rhs:
                return None
            continue
        model.Add(_cp_sat_expr(var_map, constraint.coeffs) <= int(constraint.rhs))

    for subgame_id, constraints in enumerate(constraint_sets):
        if not constraints:
            return None
        # A row that no longer depends on the universal variables is either
        # already violated (the subgame is lost for the existential player
        # whatever we choose) or can never be violated (ignore it).
        already_violated = False
        live_rows = []
        for constraint in constraints:
            if _cp_sat_is_constant(var_map, constraint.coeffs):
                holds = constraint.rhs == 0 if constraint.is_equality else 0 <= constraint.rhs
                if not holds:
                    already_violated = True
                    break
                continue
            live_rows.append(constraint)
        if already_violated:
            continue
        if not live_rows:
            return None
        literals = []
        for row_id, constraint in enumerate(live_rows):
            violated = model.NewBoolVar(f"viol_{subgame_id}_{row_id}")
            expr = _cp_sat_expr(var_map, constraint.coeffs)
            rhs = int(constraint.rhs)
            if constraint.is_equality:
                direction = model.NewBoolVar(f"viol_eq_dir_{subgame_id}_{row_id}")
                model.Add(expr == rhs).OnlyEnforceIf(violated.Not())
                model.Add(expr <= rhs - 1).OnlyEnforceIf([violated, direction.Not()])
                model.Add(expr >= rhs + 1).OnlyEnforceIf([violated, direction])
            else:
                model.Add(expr <= rhs).OnlyEnforceIf(violated.Not())
                model.Add(expr >= rhs + 1).OnlyEnforceIf(violated)
            literals.append(violated)
        model.Add(sum(literals) >= 1)

    solver = _new_cp_sat_solver(time_limit_s)
    status = solver.Solve(model)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {name: int(solver.Value(var)) for name, var in var_map.items()}
    if status == cp_model.INFEASIBLE:
        return None
    return _TIMEOUT


def _solve_ip_feasible(
    variables: list[Variable],
    constraints: list[Constraint],
    universal_constraints: list[UniversalConstraint],
    time_limit_s: Optional[float] = None,
) -> object:
    if not _constant_constraints_feasible(constraints, universal_constraints):
        return None
    highs = _new_highs(time_limit_s)
    names = _add_integer_vars(highs, variables)
    _add_constraints(highs, names, constraints)
    _add_universal_constraints(highs, names, universal_constraints)
    run_status = highs.run()
    model_status = highs.getModelStatus()
    if model_status in (
        hp.HighsModelStatus.kOptimal,
        hp.HighsModelStatus.kSolutionLimit,
        hp.HighsModelStatus.kModelEmpty,
    ):
        return _extract_solution(highs, names)
    if model_status == hp.HighsModelStatus.kInfeasible:
        return None
    if run_status != hp.HighsStatus.kOk:
        return _TIMEOUT
    return _TIMEOUT


def _compute_min_lhs(vars_dict: dict[str, Variable], coeffs: dict[str, int]) -> int:
    total = 0
    for name, coeff in coeffs.items():
        if name not in vars_dict:
            continue
        var = vars_dict[name]
        total += coeff * (var.lower if coeff >= 0 else var.upper)
    return total


def _compute_violation_gap(constraint: Constraint) -> float:
    fractions = [Fraction(constraint.rhs, 1)]
    fractions.extend(Fraction(value, 1) for value in constraint.coeffs.values())
    lcm_value = 1
    for frac in fractions:
        lcm_value = lcm_value * frac.denominator // gcd(lcm_value, frac.denominator)
    return 1.0 / lcm_value if lcm_value > 1 else 1.0


def _solve_ip_violate_all(
    variables: list[Variable],
    constraint_sets: list[list[Constraint]],
    universal_constraints: list[UniversalConstraint],
    time_limit_s: Optional[float] = None,
) -> object:
    if not _constant_constraints_feasible([], universal_constraints):
        return None

    highs = _new_highs(time_limit_s)
    var_names = _add_integer_vars(highs, variables)
    index = {name: idx for idx, name in enumerate(var_names)}

    # For a universal winning move, each subgame must have at least one violated
    # constraint, matching Problem (2) from the paper.
    extra_names: list[str] = []
    extra_bounds: list[tuple[float, float]] = []
    for subgame_id, constraints in enumerate(constraint_sets):
        if not constraints:
            return None
        if not _constant_constraints_feasible(constraints):
            continue
        extra_names.append(f"_vl{subgame_id}")
        extra_bounds.append((0.0, 1.0))
        for row_id in range(len(constraints)):
            extra_names.append(f"_y{subgame_id}_{row_id}")
            extra_bounds.append((0.0, 1.0))

    if extra_names:
        highs.addVars(
            len(extra_names),
            np.array([lo for lo, _ in extra_bounds], dtype=np.float64),
            np.array([hi for _, hi in extra_bounds], dtype=np.float64),
        )
    offset = len(var_names)
    extra_idx = {}
    for local_idx, name in enumerate(extra_names):
        col = offset + local_idx
        highs.passColName(col, name)
        highs.changeColIntegrality(col, hp.HighsVarType.kInteger)
        extra_idx[name] = col

    vars_dict = {var.name: var for var in variables}
    for subgame_id, constraints in enumerate(constraint_sets):
        active_y_cols = []
        for row_id, constraint in enumerate(constraints):
            row_idx = []
            row_val = []
            for name, coeff in constraint.coeffs.items():
                if name in index:
                    row_idx.append(index[name])
                    row_val.append(float(-coeff))

            y_name = f"_y{subgame_id}_{row_id}"
            y_col = extra_idx[y_name]
            active_y_cols.append(y_col)

            lower_bound = _compute_min_lhs(vars_dict, constraint.coeffs)
            rhs_shift = lower_bound - float(constraint.rhs) - _compute_violation_gap(constraint)
            row_idx.append(y_col)
            row_val.append(float(-rhs_shift))
            highs.addRow(
                -hp.kHighsInf,
                float(-lower_bound),
                len(row_idx),
                np.array(row_idx, dtype=np.int64),
                np.array(row_val, dtype=np.float64),
            )

        vl_col = extra_idx[f"_vl{subgame_id}"]
        highs.addRow(
            -hp.kHighsInf,
            0.0,
            1 + len(active_y_cols),
            np.array([vl_col, *active_y_cols], dtype=np.int64),
            np.array([1.0] + [-1.0] * len(active_y_cols), dtype=np.float64),
        )
        highs.addRow(
            1.0,
            hp.kHighsInf,
            1,
            np.array([vl_col], dtype=np.int64),
            np.array([1.0], dtype=np.float64),
        )

    _add_universal_constraints(highs, var_names, universal_constraints)

    for col in range(highs.getNumCol()):
        highs.changeColCost(col, 0.0)

    run_status = highs.run()
    model_status = highs.getModelStatus()
    if model_status == hp.HighsModelStatus.kInfeasible:
        return None
    if model_status not in (hp.HighsModelStatus.kOptimal, hp.HighsModelStatus.kSolutionLimit):
        if run_status != hp.HighsStatus.kOk:
            return _TIMEOUT
        return _TIMEOUT

    solution = highs.getSolution()
    if extra_idx:
        for subgame_id in range(len(constraint_sets)):
            vl_name = f"_vl{subgame_id}"
            if vl_name in extra_idx and solution.col_value[extra_idx[vl_name]] < 0.99:
                return _TIMEOUT
    return {name: int(round(solution.col_value[i])) for i, name in enumerate(var_names)}


def _normalize_violation_constraints(constraints: list[Constraint]) -> list[Constraint]:
    normalized: list[Constraint] = []
    for constraint in constraints:
        if constraint.is_equality:
            normalized.append(Constraint(dict(constraint.coeffs), constraint.rhs))
            normalized.append(
                Constraint(
                    {name: -coeff for name, coeff in constraint.coeffs.items()},
                    -constraint.rhs,
                )
            )
            continue
        normalized.append(constraint)
    return normalized


def _wins1(multigame: MultiGame, time_limit_s: Optional[float] = None) -> object:
    constraint_sets: list[list[Constraint]] = []
    universal_constraints = list(multigame.universal_constraints)
    for subgame in multigame.subgames:
        if subgame.problem is None:
            constraint_sets.append(subgame.constraints)
            universal_constraints.extend(subgame.universal_constraints)
            continue
        constraint_sets.append(subgame.problem.constraints)
    if multigame.outer_quantifier == "E":
        if _use_cp_sat(multigame.outer_quantifier):
            constraints: list[Constraint] = []
            for constraint_set in constraint_sets:
                constraints.extend(constraint_set)
            return _solve_cp_sat_feasible(
                multigame.outer_vars,
                constraints,
                universal_constraints,
                time_limit_s=time_limit_s,
            )
        constraints: list[Constraint] = []
        for constraint_set in constraint_sets:
            constraints.extend(constraint_set)
        return _solve_ip_feasible(
            multigame.outer_vars,
            constraints,
            universal_constraints,
            time_limit_s=time_limit_s,
        )
    constraint_sets = [_normalize_violation_constraints(constraint_set) for constraint_set in constraint_sets]
    if _use_cp_sat(multigame.outer_quantifier):
        return _solve_cp_sat_violate_all(
            multigame.outer_vars,
            constraint_sets,
            universal_constraints,
            time_limit_s=time_limit_s,
        )
    return _solve_ip_violate_all(
        multigame.outer_vars,
        constraint_sets,
        universal_constraints,
        time_limit_s=time_limit_s,
    )


def _existential_relaxation_move(multigame: MultiGame, time_limit_s: Optional[float] = None) -> object:
    """Pick a stronger first move by solving the current multi-game as a plain IP.

    This follows the paper's Appendix A.1 heuristic: on an empty existential
    abstraction, solve the existential relaxation instead of picking an arbitrary
    domain point.
    """
    variables_by_name = {var.name: var for var in multigame.outer_vars}
    constraints: list[Constraint] = []
    universal_constraints = list(multigame.universal_constraints)

    for subgame in multigame.subgames:
        if subgame.problem is None:
            constraints.extend(subgame.constraints)
            continue
        for variable in subgame.problem.variables:
            variables_by_name.setdefault(variable.name, variable)
        constraints.extend(subgame.problem.constraints)
        universal_constraints.extend(subgame.problem.universal_constraints)

    return _solve_ip_feasible(
        list(variables_by_name.values()),
        constraints,
        universal_constraints,
        time_limit_s=time_limit_s,
    )


def _extract_assignment(assignment: dict[str, int], variables: list[Variable]) -> dict[str, int]:
    return {var.name: assignment[var.name] for var in variables if var.name in assignment}


def _problem_to_multigame(problem: QIPProblem) -> MultiGame:
    outer_vars = _current_block(problem)
    tail = _tail_problem(problem)
    if tail is None:
        subgames = [Subgame(constraints=problem.constraints)]
    else:
        subgames = [Subgame(problem=tail)]
    return MultiGame(
        outer_quantifier=outer_vars[0].quantifier,
        outer_vars=outer_vars,
        subgames=subgames,
        universal_constraints=problem.universal_constraints,
    )


@dataclass
class _RefinementState:
    counter: int = 0
    copy_outer_constraints: list[UniversalConstraint] = field(default_factory=list)


@dataclass
class SolverStats:
    recursive_calls: int = 0
    nested_solves: int = 0
    quantifier_free_calls: int = 0
    wins1_calls: int = 0
    abstraction_iterations: int = 0
    counterexample_checks: int = 0
    refinements: int = 0
    max_recursion_depth: int = 0
    max_outer_vars: int = 0
    max_subgames: int = 0
    max_problem_variables: int = 0
    max_problem_constraints: int = 0
    ip_feasible_calls: int = 0
    ip_feasible_time_s: float = 0.0
    ip_violate_calls: int = 0
    ip_violate_time_s: float = 0.0
    exist_relax_calls: int = 0
    exist_relax_time_s: float = 0.0


def _update_stats(stats: SolverStats, multigame: MultiGame, depth: int) -> None:
    stats.recursive_calls += 1
    stats.max_recursion_depth = max(stats.max_recursion_depth, depth)
    stats.max_outer_vars = max(stats.max_outer_vars, len(multigame.outer_vars))
    stats.max_subgames = max(stats.max_subgames, len(multigame.subgames))
    for subgame in multigame.subgames:
        if subgame.problem is None:
            stats.max_problem_constraints = max(stats.max_problem_constraints, len(subgame.constraints))
            continue
        stats.max_problem_variables = max(stats.max_problem_variables, len(subgame.problem.variables))
        stats.max_problem_constraints = max(stats.max_problem_constraints, len(subgame.problem.constraints))


def _refine_from_counter(
    abstraction: MultiGame,
    subgame: Subgame,
    counter_move: dict[str, int],
    state: _RefinementState,
) -> MultiGame:
    assert subgame.problem is not None
    reduced = subgame.problem.substitute(counter_move)
    if not reduced.variables:
        return MultiGame(
            outer_quantifier=abstraction.outer_quantifier,
            outer_vars=abstraction.outer_vars,
            subgames=abstraction.subgames
            + [
                Subgame(
                    constraints=reduced.constraints,
                    universal_constraints=reduced.universal_constraints,
                )
            ],
            universal_constraints=abstraction.universal_constraints,
        )

    state.counter += 1
    renamed = _rename_problem(reduced, f"__exp{state.counter}")
    exposed = _current_block(renamed)
    tail = _tail_problem(renamed)
    new_subgames = list(abstraction.subgames)
    if tail is None:
        new_subgames.append(
            Subgame(
                constraints=renamed.constraints,
                universal_constraints=renamed.universal_constraints,
            )
        )
    else:
        new_subgames.append(Subgame(problem=tail))

    return MultiGame(
        outer_quantifier=abstraction.outer_quantifier,
        outer_vars=abstraction.outer_vars + exposed,
        subgames=new_subgames,
        universal_constraints=abstraction.universal_constraints,
    )


def equips(
    multigame: MultiGame,
    timeout_s: float,
    start_time: float,
    refinement_state: Optional[_RefinementState] = None,
    stats: Optional[SolverStats] = None,
    depth: int = 0,
) -> object:
    if refinement_state is None:
        refinement_state = _RefinementState()
    if stats is None:
        stats = SolverStats()

    _update_stats(stats, multigame, depth)

    if timeout_s - (time.time() - start_time) <= 0:
        return _TIMEOUT

    if all(subgame.is_quantifier_free() for subgame in multigame.subgames):
        stats.quantifier_free_calls += 1
        stats.wins1_calls += 1
        return _wins1(multigame, time_limit_s=timeout_s - (time.time() - start_time))

    abstraction = MultiGame(
        outer_quantifier=multigame.outer_quantifier,
        outer_vars=list(multigame.outer_vars),
        subgames=[],
        universal_constraints=multigame.universal_constraints,
    )

    for _ in range(10000):
        stats.abstraction_iterations += 1
        iteration_remaining = timeout_s - (time.time() - start_time)
        if iteration_remaining <= 0:
            return _TIMEOUT
        if not abstraction.subgames and multigame.outer_quantifier == "E":
            tau_full = _existential_relaxation_move(multigame, time_limit_s=iteration_remaining)
        else:
            tau_full = equips(
                abstraction,
                timeout_s,
                start_time,
                refinement_state,
                stats,
                depth + 1,
            )
        if tau_full is _TIMEOUT:
            return _TIMEOUT
        if tau_full is None:
            return None
        tau = _extract_assignment(tau_full, multigame.outer_vars)

        found_counter = None
        found_subgame = None
        for subgame in multigame.subgames:
            stats.counterexample_checks += 1
            if subgame.problem is None:
                continue
            reduced = subgame.problem.substitute(tau)
            if not reduced.variables:
                if not _is_constraint_system_feasible(reduced.constraints, reduced.universal_constraints):
                    found_counter = {}
                    found_subgame = subgame
                    break
                continue
            stats.nested_solves += 1
            counter = _solve_qip_internal(
                reduced,
                max(0.1, timeout_s - (time.time() - start_time)),
                stats,
                depth + 1,
            )
            if counter["status"] == "TIMEOUT":
                return _TIMEOUT
            if counter["status"] == "SAT":
                found_counter = counter["assignment"]
                found_subgame = subgame
                break

        if found_counter is None:
            return tau

        abstraction = _refine_from_counter(abstraction, found_subgame, found_counter, refinement_state)
        stats.refinements += 1
        if time.time() - start_time > timeout_s:
            return _TIMEOUT

    # Iteration cap reached without a decision: report unknown, never a verdict.
    return _TIMEOUT


def _solve_qip_internal(
    problem: QIPProblem,
    timeout_s: float,
    stats: SolverStats,
    depth: int,
) -> dict:
    start = time.time()
    if not problem.variables:
        feasible = _is_constraint_system_feasible(problem.constraints, problem.universal_constraints)
        return {
            "status": "SAT" if feasible else "UNSAT",
            "assignment": {} if feasible else None,
            "runtime": time.time() - start,
        }

    multigame = _problem_to_multigame(problem)
    assignment = equips(multigame, timeout_s, start, stats=stats, depth=depth)
    if assignment is _TIMEOUT:
        return {
            "status": "TIMEOUT",
            "assignment": None,
            "runtime": time.time() - start,
        }
    return {
        "status": "SAT" if assignment is not None else "UNSAT",
        "assignment": assignment,
        "runtime": time.time() - start,
    }


def solve_qip(problem: QIPProblem, timeout_s: float = 30.0) -> dict:
    stats = SolverStats()
    result = _solve_qip_internal(problem, timeout_s, stats, depth=0)
    result["stats"] = asdict(stats)
    return result


def solve_qip_optimization(problem: QIPProblem, timeout_s: float = 60.0) -> dict:
    start = time.time()
    if problem.objective is None:
        return solve_qip(problem, timeout_s)

    var_dict = problem.var_dict()
    lower = sum(
        coeff * (var_dict[name].lower if coeff >= 0 else var_dict[name].upper)
        for name, coeff in problem.objective.items()
    )
    upper = sum(
        coeff * (var_dict[name].upper if coeff >= 0 else var_dict[name].lower)
        for name, coeff in problem.objective.items()
    )

    lo = min(lower, upper)
    hi = max(lower, upper)
    best_assignment = None
    best_value = None

    while lo <= hi and time.time() - start < timeout_s:
        mid = (lo + hi) // 2
        result = solve_qip(problem.with_objective_bound(mid), max(0.1, timeout_s - (time.time() - start)))
        if result["status"] == "SAT":
            best_assignment = result["assignment"]
            best_value = mid
            if problem.objective_sense == "min":
                hi = mid - 1
            else:
                lo = mid + 1
        elif result["status"] == "TIMEOUT":
            return {
                "status": "TIMEOUT",
                "assignment": best_assignment,
                "optimal_value": best_value,
                "runtime": time.time() - start,
            }
        else:
            if problem.objective_sense == "min":
                lo = mid + 1
            else:
                hi = mid - 1

    return {
        "status": "SAT" if best_assignment is not None else "TIMEOUT" if time.time() - start >= timeout_s else "UNSAT",
        "assignment": best_assignment,
        "optimal_value": best_value,
        "runtime": time.time() - start,
    }
