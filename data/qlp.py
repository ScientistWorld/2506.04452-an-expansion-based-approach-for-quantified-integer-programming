"""
Minimal QLP parser for the upstream EQuIPS instances used in this workspace.

The parser is intentionally conservative: it supports the constructs needed by
the released `MiniLotSizing.qlp`, `MiniMCN.qlp`, and `QRandomParity_1000.qlp`
instances and converts all linear expressions to integer coefficients by row.
"""

from __future__ import annotations

import re
from fractions import Fraction
from math import gcd
from pathlib import Path

from data.qrandomparity import Constraint, QIPProblem, UniversalConstraint, Variable


_TERM_RE = re.compile(r"([+-])\s*(?:(\d+(?:\.\d+)?)\s+)?([A-Za-z_][A-Za-z0-9_]*)")


def _lcm(a: int, b: int) -> int:
    return abs(a * b) // gcd(a, b) if a and b else abs(a or b)


def _scale_linear_row(coeffs: dict[str, Fraction], rhs: Fraction) -> tuple[dict[str, int], int]:
    denominator_lcm = 1
    for value in list(coeffs.values()) + [rhs]:
        denominator_lcm = _lcm(denominator_lcm, value.denominator)
    scaled_coeffs = {
        name: int(value * denominator_lcm)
        for name, value in coeffs.items()
        if value != 0
    }
    scaled_rhs = int(rhs * denominator_lcm)
    return scaled_coeffs, scaled_rhs


def _parse_linear_expr(expr: str) -> dict[str, Fraction]:
    coeffs: dict[str, Fraction] = {}
    for sign, raw_coeff, name in _TERM_RE.findall(expr):
        coeff = Fraction(raw_coeff or "1")
        if sign == "-":
            coeff = -coeff
        coeffs[name] = coeffs.get(name, Fraction(0)) + coeff
    return coeffs


def _parse_constraint(line: str) -> Constraint:
    relation = None
    for candidate in ("<=", ">=", "="):
        if candidate in line:
            relation = candidate
            lhs, rhs = line.split(candidate, 1)
            break
    if relation is None:
        raise ValueError(f"Could not parse constraint line: {line}")

    coeffs, rhs_value = _scale_linear_row(_parse_linear_expr(lhs), Fraction(rhs.strip()))
    if relation == ">=":
        coeffs = {name: -coeff for name, coeff in coeffs.items()}
        rhs_value = -rhs_value
        relation = "<="

    return Constraint(coeffs=coeffs, rhs=rhs_value, is_equality=(relation == "="))


def _parse_universal_constraint(line: str) -> UniversalConstraint:
    constraint = _parse_constraint(line)
    if constraint.is_equality:
        raise ValueError("Universal constraints must be inequalities in supported QLP instances.")
    return UniversalConstraint(coeffs=constraint.coeffs, rhs=constraint.rhs)


def _parse_bound(line: str) -> tuple[str, int, int]:
    left, name, right = [part.strip() for part in line.split("<=")]
    lower = Fraction(left)
    upper = Fraction(right)
    if lower.denominator != 1 or upper.denominator != 1:
        raise ValueError(f"Non-integral bounds are not supported: {line}")
    return name, int(lower), int(upper)


def parse_qlp(path: str | Path) -> QIPProblem:
    path = Path(path)
    lines = [line.strip() for line in path.read_text().splitlines()]

    section = None
    objective_lines: list[str] = []
    constraint_lines: list[str] = []
    universal_constraint_lines: list[str] = []
    bound_lines: list[str] = []
    binary_names: set[str] = set()
    quantifier_blocks: list[tuple[str, list[str]]] = []
    order_names: list[str] = []

    current_quantifier: str | None = None
    current_quantifier_names: list[str] = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line in {"MINIMIZE", "MAXIMIZE"}:
            section = line
            continue
        if line == "SUBJECT TO":
            section = "SUBJECT TO"
            continue
        if line == "UNCERTAINTY SUBJECT TO":
            section = "UNCERTAINTY SUBJECT TO"
            continue
        if line == "BOUNDS":
            section = "BOUNDS"
            continue
        if line == "BINARIES":
            section = "BINARIES"
            continue
        if line in {"EXISTS", "ALL"}:
            if current_quantifier is not None:
                quantifier_blocks.append((current_quantifier, current_quantifier_names))
            current_quantifier = line
            current_quantifier_names = []
            section = line
            continue
        if line == "ORDER":
            if current_quantifier is not None:
                quantifier_blocks.append((current_quantifier, current_quantifier_names))
                current_quantifier = None
                current_quantifier_names = []
            section = "ORDER"
            continue
        if line == "END":
            break

        if section in {"MINIMIZE", "MAXIMIZE"}:
            objective_lines.append(line)
        elif section == "SUBJECT TO":
            constraint_lines.append(line)
        elif section == "UNCERTAINTY SUBJECT TO":
            universal_constraint_lines.append(line)
        elif section == "BOUNDS":
            bound_lines.append(line)
        elif section == "BINARIES":
            binary_names.add(line)
        elif section in {"EXISTS", "ALL"}:
            current_quantifier_names.append(line)
        elif section == "ORDER":
            order_names.append(line)
        else:
            raise ValueError(f"Unexpected QLP line outside a recognized section: {line}")

    if current_quantifier is not None:
        quantifier_blocks.append((current_quantifier, current_quantifier_names))

    bounds: dict[str, tuple[int, int]] = {}
    for line in bound_lines:
        name, lower, upper = _parse_bound(line)
        bounds[name] = (lower, upper)

    quantifier_by_name: dict[str, tuple[str, int]] = {}
    for level, (quantifier, names) in enumerate(quantifier_blocks, start=1):
        mapped = "E" if quantifier == "EXISTS" else "A"
        for name in names:
            quantifier_by_name[name] = (mapped, level)

    variable_names = order_names or list(bounds.keys())
    variables: list[Variable] = []
    for name in variable_names:
        if name not in bounds:
            raise ValueError(f"Missing bounds for variable {name} in {path}")
        if name not in quantifier_by_name:
            raise ValueError(f"Missing quantifier declaration for variable {name} in {path}")
        lower, upper = bounds[name]
        quantifier, level = quantifier_by_name[name]
        variables.append(Variable(name=name, lower=lower, upper=upper, quantifier=quantifier, level=level))

    objective = None
    if objective_lines:
        objective_expr = " ".join(objective_lines).strip()
        if objective_expr:
            objective, _ = _scale_linear_row(_parse_linear_expr(objective_expr), Fraction(0))

    constraints = [_parse_constraint(line) for line in constraint_lines]
    universal_constraints = [_parse_universal_constraint(line) for line in universal_constraint_lines]

    return QIPProblem(
        variables=variables,
        constraints=constraints,
        universal_constraints=universal_constraints,
        objective=objective,
        objective_sense="min" if lines[0].strip() == "MINIMIZE" else "max",
    )
