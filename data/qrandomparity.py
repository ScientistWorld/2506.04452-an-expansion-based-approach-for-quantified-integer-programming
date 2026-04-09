"""
QRandomParity problem generator.

From the paper: "An Expansion-Based Approach for Quantified Integer Programming"
(Hartisch & Chew, 2025)

QRandomParity combines QParity (hard for QCDCL QBF solvers) with
RandomParity (hard for CDCL SAT solvers), making it hard for both
search-based and resolution-based approaches.

The problem uses two different orderings of variables to compute parity,
which creates a contradiction under full expansion (since parity is
associative and commutative), but is hard to prove with partial expansion.

This module generates QRandomParity instances in QIP (linear) encoding.
"""

import random
from dataclasses import dataclass, field


@dataclass
class Variable:
    """A single variable in a QIP problem."""
    name: str
    lower: int
    upper: int
    quantifier: str  # 'E' for exists, 'A' for forall
    level: int = 1  # Nesting depth: 1 = outermost block, 2 = next block, etc.


@dataclass
class Constraint:
    """A linear constraint: sum(a_i * x_i) <= b"""
    coeffs: dict[str, int]  # variable name -> coefficient
    rhs: int
    is_equality: bool = False


@dataclass
class UniversalConstraint:
    """Universal (uncertainty) constraint."""
    coeffs: dict[str, int]
    rhs: int


@dataclass
class QIPProblem:
    """
    A Quantified Integer Program.
    Representation: Q_1 X_1 ... Q_k X_k : A x <= b
    """
    variables: list[Variable] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    universal_constraints: list[UniversalConstraint] = field(default_factory=list)
    objective: dict = field(default=None)
    objective_sense: str = "min"

    def outer_quantifier(self) -> str:
        return self.variables[0].quantifier if self.variables else 'E'

    def var_dict(self) -> dict:
        return {v.name: v for v in self.variables}

    def var_names(self) -> list[str]:
        return [v.name for v in self.variables]

    def level_of_var(self, name: str) -> int:
        """Return the quantifier nesting level of a variable (1 = outermost)."""
        for v in self.variables:
            if v.name == name:
                return v.level
        raise ValueError(f"Variable {name} not found")

    def substitute(self, assignment: dict[str, int]) -> 'QIPProblem':
        """Substitute given variable assignments into the problem.

        Removes substituted variables and adjusts constraints accordingly.
        Remaining variable levels are renumbered so that the next quantifier
        block (the smallest level > substituted levels) becomes level 1.
        This maintains the invariant that level 1 = current block being solved,
        needed by _solve_qip_recursive's relative level tracking.
        """
        # Separate variables into assigned and remaining
        remaining_vars = [v for v in self.variables if v.name not in assignment]

        # Renumber levels so the next quantifier block becomes level 1.
        # This restores the invariant that level 1 = current block to solve.
        if remaining_vars:
            min_level = min(v.level for v in remaining_vars)
            remaining_vars = [
                Variable(
                    name=v.name,
                    lower=v.lower,
                    upper=v.upper,
                    quantifier=v.quantifier,
                    level=v.level - min_level + 1
                )
                for v in remaining_vars
            ]

        # Substitute into constraints
        new_constraints = []
        for c in self.constraints:
            new_coeffs = {}
            rhs_adjustment = 0
            for name, coeff in c.coeffs.items():
                if name in assignment:
                    rhs_adjustment += coeff * assignment[name]
                else:
                    new_coeffs[name] = coeff
            new_rhs = c.rhs - rhs_adjustment
            new_constraints.append(Constraint(new_coeffs, new_rhs, c.is_equality))

        # Substitute into universal constraints
        new_uconstrs = []
        for uc in self.universal_constraints:
            new_coeffs = {}
            rhs_adjustment = 0
            for name, coeff in uc.coeffs.items():
                if name in assignment:
                    rhs_adjustment += coeff * assignment[name]
                else:
                    new_coeffs[name] = coeff
            new_rhs = uc.rhs - rhs_adjustment
            new_uconstrs.append(UniversalConstraint(new_coeffs, new_rhs))

        return QIPProblem(
            variables=remaining_vars,
            constraints=new_constraints,
            universal_constraints=new_uconstrs,
            objective=self.objective,
            objective_sense=self.objective_sense
        )

    def with_constraint_added(self, constraint: Constraint) -> 'QIPProblem':
        return QIPProblem(
            variables=self.variables,
            constraints=self.constraints + [constraint],
            universal_constraints=self.universal_constraints,
            objective=self.objective,
            objective_sense=self.objective_sense
        )

    def with_objective_bound(self, bound: int) -> 'QIPProblem':
        if self.objective is None:
            return self
        return self.with_constraint_added(Constraint(dict(self.objective), bound))


@dataclass
class Subgame:
    """A subgame in a multi-game."""
    problem: QIPProblem = None
    constraints: list[Constraint] = field(default_factory=list)

    def is_quantifier_free(self) -> bool:
        return self.problem is None


@dataclass
class MultiGame:
    """A multi-game: Q X : {Phi_1 ... Phi_ell}"""
    outer_quantifier: str
    outer_vars: list[Variable]
    subgames: list[Subgame] = field(default_factory=list)
    universal_constraints: list[UniversalConstraint] = field(default_factory=list)


def generate_qrandomparity(n: int, seed: int = None) -> QIPProblem:
    """
    Generate a QRandomParity QIP instance.

    Variables: x_1..x_n (existential),
               u (universal, binary),
               t_2..t_n, d_2..d_n (existential, for first parity chain),
               s_1..s_n, e_2..e_n (existential, for second parity chain)

    The QIP is:
    exists x_1..x_n  forall u  exists t_2..t_n, d_2..d_n, s_1..s_n, e_2..e_n :
        x_1 + x_2 = 2*d_2
        x_σ(1) + x_σ(2) = 2*e_2
        t_{i-1} + x_i = 2*d_i   for i=3..n
        s_{i-1} + x_{σ(i)} = 2*e_i  for i=3..n
        -u - t_n >= -1   (u + t_n >= 1)
        u + s_n >= 1
    """
    if seed is not None:
        rng = random.Random(seed)
    else:
        rng = random.Random()

    # Generate random permutation sigma
    sigma = list(range(1, n + 1))
    rng.shuffle(sigma)

    # Build variable list
    variables = []

    # x_i: existential, level 1, domain {0, 1}
    for i in range(1, n + 1):
        variables.append(Variable(name=f"x{i}", lower=0, upper=1, quantifier='E', level=1))

    # u: universal, level 2, domain {0, 1}
    variables.append(Variable(name="u", lower=0, upper=1, quantifier='A', level=2))

    # t_i: existential, level 3, domain {0, 1}
    for i in range(2, n + 1):
        variables.append(Variable(name=f"t{i}", lower=0, upper=1, quantifier='E', level=3))

    # d_i: existential, level 3, domain {0, 1}
    for i in range(2, n + 1):
        variables.append(Variable(name=f"d{i}", lower=0, upper=1, quantifier='E', level=3))

    # s_i: existential, level 3, domain {0, 1}
    for i in range(1, n + 1):
        variables.append(Variable(name=f"s{i}", lower=0, upper=1, quantifier='E', level=3))

    # e_i: existential, level 3, domain {0, 1}
    for i in range(2, n + 1):
        variables.append(Variable(name=f"e{i}", lower=0, upper=1, quantifier='E', level=3))

    constraints = []

    # (4a): x_1 + x_2 + t_2 = 2*d_2
    constraints.append(Constraint({'x1': 1, 'x2': 1, 't2': 1, 'd2': -2}, 0))
    constraints.append(Constraint({'x1': -1, 'x2': -1, 't2': -1, 'd2': 2}, 0))

    # (4a): x_{σ(1)} + x_{σ(2)} + s_2 = 2*e_2
    constraints.append(Constraint({f'x{sigma[0]}': 1, f'x{sigma[1]}': 1, 's2': 1, 'e2': -2}, 0))
    constraints.append(Constraint({f'x{sigma[0]}': -1, f'x{sigma[1]}': -1, 's2': -1, 'e2': 2}, 0))

    # (4b) t chain: t_{i-1} + x_i + t_i = 2*d_i  for i=3..n
    for i in range(3, n + 1):
        constraints.append(Constraint({f't{i-1}': 1, f'x{i}': 1, f't{i}': 1, f'd{i}': -2}, 0))
        constraints.append(Constraint({f't{i-1}': -1, f'x{i}': -1, f't{i}': -1, f'd{i}': 2}, 0))

    # (4b) s chain: s_{i-1} + x_{σ(i)} + s_i = 2*e_i  for i=3..n
    for i in range(3, n + 1):
        constraints.append(Constraint({f's{i-1}': 1, f'x{sigma[i-1]}': 1, f's{i}': 1, f'e{i}': -2}, 0))
        constraints.append(Constraint({f's{i-1}': -1, f'x{sigma[i-1]}': -1, f's{i}': -1, f'e{i}': 2}, 0))

    # (4c): -u - t_n >= -1  =>  -u - t_n <= -1
    constraints.append(Constraint({'u': -1, f't{n}': -1}, -1))
    # (4c): u + s_n >= 1  ->  -u - s_n <= -1
    constraints.append(Constraint({'u': -1, f's{n}': -1}, -1))

    return QIPProblem(variables=variables, constraints=constraints)


def to_qdimacs(problem: QIPProblem, sigma: list[int]) -> str:
    """Convert to QDIMACS format for QBF solvers."""
    n = len([v for v in problem.variables if v.quantifier == 'E' and v.name.startswith('x')])
    # Count variables: x_1..x_n (n), u (1), t_2..t_n (n-1), d_2..d_n (n-1), s_1..s_n (n), e_2..e_n (n-1)
    total_vars = 4 * n
    n_clauses = 4 * n - 2

    lines = [f"c QRandomParity n={n}", f"p cnf {total_vars} {n_clauses}"]

    # Quantifier prefix: exists x_1..x_n, forall u, exists rest
    lines.append("e " + " ".join(str(i+1) for i in range(n)))
    lines.append(f"a {n+1}")  # u

    # Remaining variables: t_2..s_n
    remaining = list(range(n+2, 4*n+1))
    if remaining:
        lines.append("e " + " ".join(str(x) for x in remaining))

    # t chain init
    lines.append(f"1 2 {n+2} 0")
    lines.append(f"-1 2 {n+2} 0")
    lines.append(f"1 -2 {n+2} 0")
    lines.append(f"-1 -2 {n+2} 0")

    # s chain init
    s1 = 2*n
    lines.append(f"{sigma[0]+1} {sigma[1]+1} {s1} 0")
    lines.append(f"{-sigma[0]-1} {sigma[1]+1} {s1} 0")
    lines.append(f"{sigma[0]+1} {-sigma[1]-1} {s1} 0")
    lines.append(f"{-sigma[0]-1} {-sigma[1]-1} {s1} 0")

    # t chain propagation for i=3..n
    for i in range(3, n+1):
        t_prev = n + i - 1
        t_curr = n + i
        lines.append(f"{-i} {t_prev} {t_curr} 0")
        lines.append(f"{i} {-(t_prev)} {t_curr} 0")
        lines.append(f"{i} {t_prev} {-(t_curr)} 0")
        lines.append(f"{-i} {-(t_prev)} {-(t_curr)} 0")

    # s chain propagation for i=3..n
    for i in range(3, n+1):
        s_prev = 2*n + i - 2
        s_curr = 2*n + i - 1
        x_si = sigma[i-1] + 1
        lines.append(f"{-x_si} {s_prev} {s_curr} 0")
        lines.append(f"{x_si} {-(s_prev)} {s_curr} 0")
        lines.append(f"{x_si} {s_prev} {-(s_curr)} 0")
        lines.append(f"{-x_si} {-(s_prev)} {-(s_curr)} 0")

    # Final
    t_n = 2*n - 1
    s_n = 3*n - 1
    u = n + 1
    lines.append(f"{-u} {-t_n} 0")
    lines.append(f"{u} {s_n} 0")

    return "\n".join(lines)


if __name__ == '__main__':
    # Test: generate a small instance
    print("Generating QRandomParity instance with n=5...")
    problem = generate_qrandomparity(n=5, seed=42)
    print(f"Problem: {len(problem.variables)} variables, {len(problem.constraints)} constraints")
