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

This implementation generates both:
1. QIP encoding (linear constraints, used by EQuIPS)
2. QBF encoding (CNF clauses, used by QBF solvers)
"""

import random
import math
from dataclasses import dataclass
from method.equips import (
    QIPProblem, Variable, Constraint, Subgame, MultiGame,
    solve_qip, solve_ip_exists
)


@dataclass
class QRandomParityQIP:
    """QRandomParity in QIP (linear) encoding."""
    n: int
    sigma: list[int]  # Random permutation of [1..n]
    problem: QIPProblem

    @staticmethod
    def generate(n: int, seed: int = None) -> 'QRandomParityQIP':
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
            -u - t_n >= -1   (i.e., u + t_n >= 1)
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
        # Quantification: exists x_1..x_n, forall u, exists t_2..t_n, d_2..d_n, s_1..s_n, e_2..e_n
        variables = []

        # x_i: existential, domain {0, 1}
        for i in range(1, n + 1):
            variables.append(Variable(name=f"x{i}", lower=0, upper=1, quantifier='E'))

        # u: universal, domain {0, 1}
        variables.append(Variable(name="u", lower=0, upper=1, quantifier='A'))

        # t_i: existential, domain {0, 1}
        for i in range(2, n + 1):
            variables.append(Variable(name=f"t{i}", lower=0, upper=1, quantifier='E'))

        # d_i: existential, domain {0, 1}
        for i in range(2, n + 1):
            variables.append(Variable(name=f"d{i}", lower=0, upper=1, quantifier='E'))

        # s_i: existential, domain {0, 1}
        for i in range(1, n + 1):
            variables.append(Variable(name=f"s{i}", lower=0, upper=1, quantifier='E'))

        # e_i: existential, domain {0, 1}
        for i in range(2, n + 1):
            variables.append(Variable(name=f"e{i}", lower=0, upper=1, quantifier='E'))

        # Build constraints (4a)-(4c) from the paper
        constraints = []

        # (4a): x_1 + x_2 = 2*d_2  =>  x_1 + x_2 - 2*d_2 <= 0 and -x_1 - x_2 + 2*d_2 <= 0
        constraints.append(Constraint({'x1': 1, 'x2': 1, 'd2': -2}, 0))
        constraints.append(Constraint({'x1': -1, 'x2': -1, 'd2': 2}, 0))

        # (4a): x_{σ(1)} + x_{σ(2)} = 2*e_2
        constraints.append(Constraint({f'x{sigma[0]}': 1, f'x{sigma[1]}': 1, f'e2': -2}, 0))
        constraints.append(Constraint({f'x{sigma[0]}': -1, f'x{sigma[1]}': -1, f'e2': 2}, 0))

        # (4b) for t chain: t_{i-1} + x_i = 2*d_i  for i=3..n
        for i in range(3, n + 1):
            constraints.append(Constraint({f't{i-1}': 1, f'x{i}': 1, f'd{i}': -2}, 0))
            constraints.append(Constraint({f't{i-1}': -1, f'x{i}': -1, f'd{i}': 2}, 0))

        # (4b) for s chain: s_{i-1} + x_{σ(i)} = 2*e_i  for i=3..n
        for i in range(3, n + 1):
            constraints.append(Constraint({f's{i-1}': 1, f'x{sigma[i-1]}': 1, f'e{i}': -2}, 0))
            constraints.append(Constraint({f's{i-1}': -1, f'x{sigma[i-1]}': -1, f'e{i}': 2}, 0))

        # (4c): -u - t_n >= -1  =>  -u - t_n <= -1
        constraints.append(Constraint({'u': -1, f't{n}': -1}, -1))
        # (4c): u + s_n >= 1  =>  u + s_n <= ? (no upper bound needed for >= constraint)
        # We express as: u + s_n >= 1  =>  -(u + s_n) <= -1
        constraints.append(Constraint({'u': 1, f's{n}': 1}, 1))

        problem = QIPProblem(variables=variables, constraints=constraints)
        return QRandomParityQIP(n=n, sigma=sigma, problem=problem)

    def solve(self, timeout_s: float = 30.0) -> dict:
        """Solve this QRandomParity instance."""
        return solve_qip(self.problem, timeout_s)

    def to_dimacs(self) -> str:
        """
        Convert to QDIMACS format for QBF solvers.

        The QBF formula:
        exists x_1..x_n  forall u  exists t_2..t_n, s_1..s_n
        with CNF clauses encoding the XOR relations.
        """
        lines = []
        # Comment
        lines.append(f"c QRandomParity n={self.n} sigma={self.sigma}")
        lines.append(f"p cnf {2*n + 1} {4*n - 2}")  # variables and clauses

        # Quantifier prefix
        # exists x_1..x_n  forall u  exists rest
        prefix = "e " + " ".join(str(i+1) for i in range(n))  # x_1..x_n
        lines.append(prefix)
        lines.append(f"a {n+1}")  # u is at position n+1
        # exists t_2..t_n (positions n+2..n+n-1), s_1..s_n (n+n..3n-1)
        # u is at index n (0-based), x_1 is at 0, x_n is at n-1
        # t_2 at n+1, ..., t_n at 2n-1
        # s_1 at 2n, s_2 at 2n+1, ..., s_n at 3n-1
        remaining = list(range(n+2, 3*n))  # t_2..s_n
        if remaining:
            lines.append("e " + " ".join(str(x) for x in remaining))

        # t chain initialization (clause 3a)
        lines.append(f"{1} {2} {n+2} 0")  # x1 ∨ x2 ∨ t2
        lines.append(f"{-1} {2} {n+2} 0")  # ¬x1 ∨ x2 ∨ t2
        lines.append(f"{1} {-2} {n+2} 0")  # x1 ∨ ¬x2 ∨ t2
        lines.append(f"{-1} {-2} {n+2} 0")  # ¬x1 ∨ ¬x2 ∨ t2

        # s chain initialization (clause 3c)
        s1_var = 2*n  # s_1 variable
        lines.append(f"{self.sigma[0]+1} {self.sigma[1]+1} {s1_var} 0")
        lines.append(f"{-self.sigma[0]-1} {self.sigma[1]+1} {s1_var} 0")
        lines.append(f"{self.sigma[0]+1} {-self.sigma[1]-1} {s1_var} 0")
        lines.append(f"{-self.sigma[0]-1} {-self.sigma[1]-1} {s1_var} 0")

        # t chain propagation (clause 3b) for i=3..n
        for i in range(3, n+1):
            t_prev = n + i - 1  # t_{i-1}
            t_curr = n + i      # t_i
            x_i = i             # x_i (1-indexed)
            lines.append(f"{-x_i} {t_prev} {t_curr} 0")
            lines.append(f"{x_i} {-(t_prev)} {t_curr} 0")
            lines.append(f"{x_i} {t_prev} {-(t_curr)} 0")
            lines.append(f"{-x_i} {-(t_prev)} {-(t_curr)} 0")

        # s chain propagation (clause 3d) for i=3..n
        for i in range(3, n+1):
            s_prev = 2*n + i - 2  # s_{i-1}
            s_curr = 2*n + i - 1  # s_i
            x_si = self.sigma[i-1] + 1  # x_{σ(i)}
            lines.append(f"{-x_si} {s_prev} {s_curr} 0")
            lines.append(f"{x_si} {-(s_prev)} {s_curr} 0")
            lines.append(f"{x_si} {s_prev} {-(s_curr)} 0")
            lines.append(f"{-x_si} {-(s_prev)} {-(s_curr)} 0")

        # Final constraints (3e): (u̅ ∨ t_n) (u ∨ s_n)
        t_n = 2*n - 1  # t_n
        s_n = 3*n - 1  # s_n
        u = n + 1
        lines.append(f"{-u} {-t_n} 0")  # ¬u ∨ ¬t_n
        lines.append(f"{u} {s_n} 0")   # u ∨ s_n

        return "\n".join(lines)


def generate_instances(n_values: list[int], num_per_n: int = 10, seed: int = 42) -> dict:
    """
    Generate QRandomParity instances for multiple n values.

    Returns dict: n -> list of QRandomParityQIP instances
    """
    instances = {}
    rng = random.Random(seed)
    for n in n_values:
        instances[n] = []
        for i in range(num_per_n):
            instance = QRandomParityQIP.generate(n, seed=seed + n * 1000 + i)
            instances[n].append(instance)
    return instances


def solve_instances(instances: dict, timeout_s: float = 30.0) -> dict:
    """
    Solve a dict of instances and return results.
    """
    results = {}
    for n, inst_list in instances.items():
        results[n] = []
        for i, inst in enumerate(inst_list):
            result = inst.solve(timeout_s=timeout_s)
            result['n'] = n
            result['instance_id'] = i
            results[n].append(result)
    return results


def benchmark_summary(results: dict, timeout_s: float = 30.0) -> dict:
    """
    Compute benchmark summary statistics.
    """
    summary = {}
    for n, res_list in results.items():
        runtimes = []
        solved = 0
        unsolved = 0
        for r in res_list:
            if r['runtime'] < timeout_s:
                runtimes.append(r['runtime'])
                solved += 1
            else:
                unsolved += 1

        if runtimes:
            median = sorted(runtimes)[len(runtimes) // 2]
            mean = sum(runtimes) / len(runtimes)
        else:
            median = None
            mean = None

        summary[n] = {
            'solved': solved,
            'unsolved': unsolved,
            'total': len(res_list),
            'median_runtime': median,
            'mean_runtime': mean
        }
    return summary


if __name__ == '__main__':
    # Test: generate and solve a small instance
    print("Generating QRandomParity instance with n=5...")
    inst = QRandomParityQIP.generate(n=5, seed=42)
    print(f"Problem: {len(inst.problem.variables)} variables, {len(inst.problem.constraints)} constraints")
    print(f"Sigma: {inst.sigma}")

    print("\nSolving...")
    result = inst.solve(timeout_s=10.0)
    print(f"Result: {result}")

    print("\nGenerating n=10 instance...")
    inst2 = QRandomParityQIP.generate(n=10, seed=123)
    result2 = inst2.solve(timeout_s=10.0)
    print(f"Result: {result2}")
