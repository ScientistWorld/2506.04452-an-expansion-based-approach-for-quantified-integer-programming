# Paper's Method

## Key Contribution

The paper introduces **EQuIPS** (Expansion-based Quantified Integer Programming Solver): the first expansion-based solver for QIP, using Counterexample-Guided Abstraction Refinement (CEGAR). This is the first expansion-based approach for QIP — previously only search-based (QCDCL) methods existed.

## Approach

### Core Algorithm: CEGAR for QIP

EQuIPS iteratively solves QIP by building and refining abstractions:

1. **Start**: Empty abstraction (no constraints, only domain compliance)
2. **Solve abstraction**: Call EQuIPS recursively on the current abstraction
3. **Extract move**: Get a candidate assignment τ for the outer-level variables
4. **Find counter**: For each subgame, check if ∃ opponent has a counter-move μ to τ
5. **If no counter**: τ is a winning move — return it
6. **If counter found**: Refine abstraction by adding the counter scenario, repeat

The algorithm uses an IP solver (Gurobi in the paper) to solve two key subproblems:

**wins1(∃X : Φ)**: Find assignment τ satisfying all constraint systems. Modeled as a standard IP:
- Minimize or maximize the assignment (or use any feasible solution)
- Subject to: all constraint systems + variable domains

**wins1(∀X : Φ)**: Find assignment τ that violates all constraint systems. This requires:
- Computing lower bounds L on each constraint's LHS
- Computing minimal violation gap r (reciprocal of LCD of coefficients)
- Using indicator variables y to ensure at least one constraint violated per system

### Optimization

Two methods for optimization (min-max QIP):
1. **Binary search**: Find optimal z by binary searching on objective value
2. **Hybrid approach**: Use Yasol (search-based) for solution finding, EQuIPS for optimality verification

### QRandomParity Encoding

Two encodings for the parity problem:
- **QBF encoding**: CNF clauses (3a-3e) solved by SAT-based QBF solvers
- **QIP encoding**: Linear constraints (4a-4c) solved by EQuIPS

The QIP encoding uses auxiliary variables for XOR: x_i + x_j + t = 2d.

## Main Claims

1. EQuIPS outperforms search-based QIP solvers (Yasol) on QRandomParity instances
2. EQuIPS outperforms state-of-the-art QBF expansion solvers (QFUN) on QIP-encoded instances
3. The linear constraint encoding provides advantages over clausal encodings
4. EQuIPS solves more MCN instances than Yasol, with moderate runtime trade-offs
