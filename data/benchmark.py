"""
Benchmark instance families for this workspace (public generator, train split).

Two families of quantified integer programs (QIPs) are produced, both written
in the QLP file format used by the paper's released solver:

* ``qrandomparity`` -- the paper's QRandomParity construction (Section 4.2,
  linear encoding (4)): two parity chains over the outer variables in different
  orders, linked to one universal bit.  Besides the paper's own instances the
  family contains planted variants with additional short parity side chains on
  the outer variables, so that both TRUE and FALSE instances occur and are of
  comparable difficulty.

* ``mcn`` -- decision versions of the multilevel critical node problem
  (Section 5.2, model (5)): "can the defender guarantee to save at least K
  nodes?".  K is set at the optimum (TRUE) or one above it (FALSE); the optimum
  for the train split is stored in ``data/train_instances.json``.

All randomness goes through :class:`Rng`, which only uses
``random.Random.random()`` so that instances are reproducible across Python
versions.  Variable names, constraint order and term order are randomised when
an instance is written, so the file text carries no naming hints.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field


# --------------------------------------------------------------------------
# Randomness and a minimal QIP builder
# --------------------------------------------------------------------------


class Rng:
    def __init__(self, seed: int):
        self._r = random.Random(int(seed))

    def random(self) -> float:
        return self._r.random()

    def randint(self, low: int, high: int) -> int:
        """Uniform integer in [low, high] (inclusive)."""
        return low + int(self._r.random() * (high - low + 1))

    def bit(self) -> int:
        return 1 if self._r.random() < 0.5 else 0

    def shuffle(self, seq: list) -> None:
        for i in range(len(seq) - 1, 0, -1):
            j = int(self._r.random() * (i + 1))
            seq[i], seq[j] = seq[j], seq[i]

    def sample(self, population, k: int) -> list:
        pool = list(population)
        self.shuffle(pool)
        return pool[:k]


@dataclass
class Builder:
    """Plain container: variables, existential constraints, universal constraints."""

    variables: list = field(default_factory=list)  # (name, lb, ub, quantifier 'E'/'A', level)
    constraints: list = field(default_factory=list)  # (coeffs dict, sense, rhs)
    universal_constraints: list = field(default_factory=list)  # (coeffs dict, sense, rhs)

    def var(self, name: str, quantifier: str, level: int, lb: int = 0, ub: int = 1) -> str:
        self.variables.append((name, lb, ub, quantifier, level))
        return name

    def con(self, coeffs: dict, sense: str, rhs: int) -> None:
        clean = {k: v for k, v in coeffs.items() if v != 0}
        self.constraints.append((clean, sense, rhs))

    def ucon(self, coeffs: dict, sense: str, rhs: int) -> None:
        clean = {k: v for k, v in coeffs.items() if v != 0}
        self.universal_constraints.append((clean, sense, rhs))


def _format_row(coeffs: dict, sense: str, rhs: int, order: list) -> str:
    terms = []
    for name in order:
        c = coeffs[name]
        sign = "+" if c > 0 else "-"
        mag = abs(c)
        terms.append(f"{sign} {name}" if mag == 1 else f"{sign} {mag} {name}")
    return " ".join(terms) + f" {sense} {rhs}"


def write_qlp(builder: Builder, rng: Rng) -> str:
    """Write a decision QIP in QLP format with randomised names and orders."""
    names = [v[0] for v in builder.variables]
    ids = list(range(1, len(names) + 1))
    rng.shuffle(ids)
    rename = {name: f"v{idx}" for name, idx in zip(names, ids)}

    levels: dict[int, list] = {}
    for name, lb, ub, quant, level in builder.variables:
        levels.setdefault(level, []).append((rename[name], lb, ub, quant))
    order: list = []
    for level in sorted(levels):
        block = list(levels[level])
        rng.shuffle(block)
        order.extend(block)

    def rows(raw_rows: list) -> list:
        out = []
        for coeffs, sense, rhs in raw_rows:
            renamed = {rename[k]: v for k, v in coeffs.items()}
            term_order = list(renamed)
            rng.shuffle(term_order)
            out.append(_format_row(renamed, sense, rhs, term_order))
        rng.shuffle(out)
        return out

    lines = ["MAXIMIZE", "", "SUBJECT TO"]
    lines.extend(rows(builder.constraints))
    if builder.universal_constraints:
        lines.append("UNCERTAINTY SUBJECT TO")
        lines.extend(rows(builder.universal_constraints))
    lines.append("BOUNDS")
    lines.extend(f"{lb} <= {name} <= {ub}" for name, lb, ub, _ in order)
    binaries = [name for name, lb, ub, _ in order if lb == 0 and ub == 1]
    if binaries:
        lines.append("BINARIES")
        lines.extend(binaries)
    lines.append("EXISTS")
    lines.extend(name for name, _, _, quant in order if quant == "E")
    universals = [name for name, _, _, quant in order if quant == "A"]
    if universals:
        lines.append("ALL")
        lines.extend(universals)
    lines.append("ORDER")
    lines.extend(name for name, _, _, _ in order)
    lines.append("END")
    return "\n".join(lines) + "\n"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# QRandomParity family
# --------------------------------------------------------------------------

PARITY_KINDS = ("paper_false", "paper_true", "gen_true", "gen_false", "card_true", "card_false")


def _pinned_subset(rows: list, candidates: list, width: int) -> list:
    """First ``width`` candidates whose value is the same in every solution of
    the parity system {sum_{i in seq} x_i = r (mod 2)} (rows are index lists).
    Returns [] if fewer than ``width`` candidates are pinned."""
    pivots: dict = {}
    for seq in rows:
        row = 0
        for i in seq:
            row ^= 1 << i
        while row:
            p = row.bit_length() - 1
            if p in pivots:
                row ^= pivots[p]
            else:
                pivots[p] = row
                break
    picked = []
    for i in candidates:
        row = 1 << i
        while row:
            p = row.bit_length() - 1
            if p not in pivots:
                break
            row ^= pivots[p]
        if not row:
            picked.append(i)
            if len(picked) == width:
                return picked
    return []


def parity_instance(n: int, kind: str, seed: int) -> tuple[str, bool]:
    """Return (qlp_text, answer) for a QRandomParity-family instance.

    Prefix: exists x_1..x_n, forall u, exists (chain auxiliaries).
    Chain T computes the parity of all x (paper order 1..n), chain S the parity
    of another multiset of x in random order; u=1 forces T to a target a and
    u=0 forces S to a target b.  Optional side chains force the parity of short
    random subsets of x.  The existential player wins iff some x satisfies all
    side parities, T(x)=a and S(x)=b.
    """
    if kind not in PARITY_KINDS:
        raise ValueError(f"unknown parity kind {kind}")
    if n < 4:
        raise ValueError("n must be at least 4")
    rng = Rng(seed)
    b = Builder()
    xs = [b.var(f"x{i}", "E", 1) for i in range(n)]
    b.var("u", "A", 2)
    xstar = [rng.bit() for _ in range(n)]
    counter = [0]

    def chain(seq: list) -> str:
        prev = xs[seq[0]]
        for idx in seq[1:]:
            counter[0] += 1
            t = b.var(f"t{counter[0]}", "E", 3)
            d = b.var(f"d{counter[0]}", "E", 3)
            coeffs: dict = {}
            for name, c in ((prev, 1), (xs[idx], 1), (t, 1), (d, -2)):
                coeffs[name] = coeffs.get(name, 0) + c
            b.con(coeffs, "=", 0)
            prev = t
        return prev

    def parity(seq) -> int:
        return sum(xstar[i] for i in seq) % 2

    t_seq = list(range(n))
    side: list = []
    card: list = []
    if kind == "paper_false":
        a, bb = 0, 1
        s_seq = list(range(n))
        rng.shuffle(s_seq)
        answer = False
    elif kind == "paper_true":
        a, bb = 0, 1
        j, k = rng.sample(range(n), 2)
        s_seq = [k if i == j else i for i in range(n)]
        rng.shuffle(s_seq)
        answer = True
    else:
        card_kind = kind.startswith("card")
        while True:
            rho = (0.95 + 0.05 * rng.random()) if card_kind else (0.6 + 0.4 * rng.random())
            m = min(n - 1, max(1, int(round(n * rho))))
            side = []
            for _ in range(m):
                width = min(n, rng.randint(3, 5))
                side.append(rng.sample(range(n), width))
            chosen = rng.sample(range(m), min(m, rng.randint(1, 3)))
            base = set(t_seq)
            for j in chosen:
                base ^= set(side[j])
            if kind == "gen_true" or card_kind:
                base ^= set(rng.sample(range(n), rng.randint(1, 2)))
            if len(base) < 2:
                continue
            if not card_kind:
                break
            # card kinds: a consistent parity system plus one cardinality
            # equality over outer variables whose values the system pins down.
            width = rng.randint(4, 6)
            candidates = list(range(n))
            rng.shuffle(candidates)
            card = _pinned_subset(side + [t_seq, sorted(base)], candidates, width)
            if card:
                break
        s_seq = sorted(base)
        rng.shuffle(s_seq)
        a = parity(t_seq)
        bb = parity(s_seq) ^ (1 if kind == "gen_false" else 0)
        answer = kind in ("gen_true", "card_true")

    t_out = chain(t_seq)
    s_out = chain(s_seq)
    for seq in side:
        out = chain(seq)
        b.con({out: 1}, "=", parity(seq))
    if a == 0:
        b.con({"u": 1, t_out: 1}, "<=", 1)
    else:
        b.con({"u": 1, t_out: -1}, "<=", 0)
    if bb == 1:
        b.con({"u": 1, s_out: 1}, ">=", 1)
    else:
        b.con({s_out: 1, "u": -1}, "<=", 0)
    card_rhs = None
    if card:
        ones = sum(xstar[i] for i in card)
        if kind == "card_true":
            card_rhs = ones
        else:
            card_rhs = ones + 2 if ones + 2 <= len(card) else ones - 2
        b.con({xs[i]: 1 for i in card}, "=", card_rhs)
    return write_qlp(b, rng), answer


# --------------------------------------------------------------------------
# Multilevel critical node (MCN) family
# --------------------------------------------------------------------------


def mcn_params(num_nodes: int, seed: int) -> dict:
    """Random undirected graph (average degree 1.5-3) and budgets
    (vaccinate, attack, protect), each drawn from {1, 2, 3}."""
    rng = Rng(seed)
    avg_degree = 1.5 + 1.5 * rng.random()
    p = avg_degree / (num_nodes - 1)
    edges = [
        (i, j)
        for i in range(num_nodes)
        for j in range(i + 1, num_nodes)
        if rng.random() < p
    ]
    return {
        "num_nodes": num_nodes,
        "edges": edges,
        "vaccinate": rng.randint(1, 3),
        "attack": rng.randint(1, 3),
        "protect": rng.randint(1, 3),
    }


def mcn_instance(num_nodes: int, seed: int, threshold: int) -> str:
    """QLP text of: exists z forall y (sum y <= attack) exists x, alpha with
    model (5) of the paper and the decision constraint sum(alpha) >= threshold."""
    params = mcn_params(num_nodes, seed)
    rng = Rng(seed * 7919 + 17)
    b = Builder()
    nodes = range(params["num_nodes"])
    z = [b.var(f"z{v}", "E", 1) for v in nodes]
    y = [b.var(f"y{v}", "A", 2) for v in nodes]
    x = [b.var(f"x{v}", "E", 3) for v in nodes]
    alpha = [b.var(f"a{v}", "E", 3) for v in nodes]
    b.con({name: 1 for name in z}, "<=", params["vaccinate"])
    b.con({name: 1 for name in x}, "<=", params["protect"])
    for v in nodes:
        b.con({alpha[v]: 1, y[v]: 1, z[v]: -1}, "<=", 1)
    for i, j in params["edges"]:
        for u, v in ((i, j), (j, i)):
            b.con({alpha[v]: 1, alpha[u]: -1, x[v]: -1, z[v]: -1}, "<=", 0)
    b.con({name: 1 for name in alpha}, ">=", int(threshold))
    b.ucon({name: 1 for name in y}, "<=", params["attack"])
    return write_qlp(b, rng)


# --------------------------------------------------------------------------
# Instance tables
# --------------------------------------------------------------------------


def materialize(experiment: str, size: int, spec: dict) -> tuple[str, bool]:
    """Instance text and answer for one entry of an instance table."""
    if experiment == "qrandomparity_ladder":
        text, answer = parity_instance(size, spec["kind"], spec["seed"])
        if answer != bool(spec["answer"]):
            raise ValueError("instance table answer disagrees with construction")
        return text, answer
    if experiment == "mcn_ladder":
        return mcn_instance(size, spec["seed"], spec["threshold"]), bool(spec["answer"])
    raise ValueError(f"unknown experiment {experiment}")
