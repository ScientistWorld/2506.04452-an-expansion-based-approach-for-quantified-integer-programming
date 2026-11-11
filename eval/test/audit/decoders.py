#!/usr/bin/env python3
"""Family-specific decoders used to audit the hidden test (shortcuts, not methods).

Usage: python3 eval/test/audit/decoders.py MODE INSTANCE.qlp ANSWER.json
  gf2       full expansion of a small universal block, then GF(2) elimination on
            the equality rows; answers only when every remaining inequality is a
            single-variable bound (i.e. the instance looks like a parity family),
            assuming mod-2 consistency implies integer feasibility.
  mcn       recognises the critical-node model (5) in the rows, rebuilds the
            graph and budgets, and runs an exact problem-specific minimax.
  gf2_strict  like gf2, but also abstains when an equality row with several
            variables has no negative coefficient (a cardinality row), i.e. it
            answers only on instances made of XOR-shaped rows.
  combined  gf2, then mcn.
  combined_strict  gf2_strict, then mcn.
Both decode the generating process rather than solving a QIP.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

from data.qlp import parse_qlp  # noqa: E402
from data.qrandomparity import Constraint, Variable  # noqa: E402
from variant_solve import gf2_infeasible  # noqa: E402


def _blocks(problem):
    levels = sorted({v.level for v in problem.variables})
    return [[v for v in problem.variables if v.level == lvl] for lvl in levels]


def gf2_decide(problem, strict=False):
    blocks = _blocks(problem)
    if len(blocks) != 3 or blocks[1][0].quantifier != "A" or len(blocks[1]) > 12:
        return None
    outer, univ, inner = blocks
    univ_names = [v.name for v in univ]
    copies = []
    for values in itertools.product(*[range(v.lower, v.upper + 1) for v in univ]):
        mu = dict(zip(univ_names, values))
        ok = all(sum(c.coeffs.get(n, 0) * mu[n] for n in univ_names) <= c.rhs for c in problem.universal_constraints)
        if ok:
            copies.append(mu)
    variables = list(outer)
    constraints = []
    for k, mu in enumerate(copies):
        reduced = problem.substitute(mu)
        rename = {v.name: f"{v.name}__{k}" for v in inner}
        variables += [Variable(rename[v.name], v.lower, v.upper, v.quantifier, 2) for v in inner]
        for c in reduced.constraints:
            coeffs = {rename.get(n, n): a for n, a in c.coeffs.items() if a != 0}
            if not c.is_equality and len(coeffs) > 1:
                return None  # not parity-shaped: abstain
            if strict and c.is_equality and len(coeffs) > 1 and min(coeffs.values()) > 0:
                return None  # cardinality row: abstain
            constraints.append(Constraint(coeffs, c.rhs, c.is_equality))
    return not gf2_infeasible(variables, constraints, [])


def mcn_decide(problem):
    import qip_hidden_gen as gen

    blocks = _blocks(problem)
    if len(blocks) != 3:
        return None
    zs = {v.name for v in blocks[0]}
    ys = {v.name for v in blocks[1]}
    ws = {v.name for v in blocks[2]}
    n = len(zs)
    if len(ys) != n or len(ws) != 2 * n or len(problem.universal_constraints) != 1:
        return None
    attack = problem.universal_constraints[0].rhs
    vaccinate = protect = threshold = None
    alpha = set()
    xset = set()
    triples = []
    arcs = []
    for c in problem.constraints:
        names = set(c.coeffs)
        vals = set(c.coeffs.values())
        if names == zs and vals == {1}:
            vaccinate = c.rhs
        elif names <= ws and vals == {-1} and len(names) == n:
            alpha = names
            threshold = -c.rhs
        elif names <= ws and vals == {1} and len(names) == n:
            xset = names
            protect = c.rhs
        elif len(names) == 3 and c.rhs == 1:
            triples.append(c.coeffs)
        elif len(names) == 4 and c.rhs == 0:
            arcs.append(c.coeffs)
    if None in (vaccinate, protect, threshold) or not alpha:
        return None
    node_of = {}
    for coeffs in triples:
        a = [k for k, v in coeffs.items() if k in alpha and v == 1]
        y = [k for k, v in coeffs.items() if k in ys and v == 1]
        z = [k for k, v in coeffs.items() if k in zs and v == -1]
        if len(a) == len(y) == len(z) == 1:
            node_of[a[0]] = len(node_of)
    if len(node_of) != n:
        return None
    edges = set()
    for coeffs in arcs:
        head = [k for k, v in coeffs.items() if k in alpha and v == 1]
        tail = [k for k, v in coeffs.items() if k in alpha and v == -1]
        if len(head) == 1 and len(tail) == 1:
            i, j = node_of[tail[0]], node_of[head[0]]
            edges.add((min(i, j), max(i, j)))
    params = {"num_nodes": n, "edges": sorted(edges), "vaccinate": vaccinate, "attack": attack, "protect": protect}
    return threshold <= gen.mcn_optimum(params)


def main() -> None:
    mode, instance, answer_path = sys.argv[1], sys.argv[2], sys.argv[3]
    problem = parse_qlp(instance)
    decision = None
    if mode in ("gf2", "combined"):
        decision = gf2_decide(problem)
    if mode in ("gf2_strict", "combined_strict"):
        decision = gf2_decide(problem, strict=True)
    if decision is None and mode in ("mcn", "combined", "combined_strict"):
        decision = mcn_decide(problem)
    answer = "UNKNOWN" if decision is None else ("TRUE" if decision else "FALSE")
    Path(answer_path).write_text(json.dumps({"answer": answer}))


if __name__ == "__main__":
    main()
