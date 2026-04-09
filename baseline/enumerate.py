"""
Exact enumeration baseline for small `exists X forall U exists Z` QIPs.
"""

from __future__ import annotations

import itertools
import time

from data.qrandomparity import QIPProblem
from method.equips import _solve_ip_feasible


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
