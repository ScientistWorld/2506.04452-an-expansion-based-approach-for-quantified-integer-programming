# Research Direction

## Research Problem
This paper addresses the problem of efficiently solving Quantified Integer Programming (QIP) — extending QBF with integer variables and linear constraints. The core challenge is that QIP combines the combinatorial complexity of quantification with continuous optimization, making both search-based and naive expansion-based approaches inefficient on many problem classes.

The paper shows that expansion-based methods with CEGAR can outperform search-based QIP solvers on certain problem families (like QRandomParity), while struggling on others (like deep quantifier alternations). The scientist should work on improving the expansion-based approach for QIP.

## Core Contribution
The paper's novelty is EQuIPS: the first expansion-based QIP solver using CEGAR. The key insight is that by iteratively building partial expansions and refining them with counter-moves, the solver can avoid full exponential expansion while still being complete. The scientist must work within this CEGAR-based expansion paradigm — improving the abstraction construction, counter-move generation, or refinement strategy.

## Approach Scope
The scientist should focus on improving the EQuIPS algorithm. They may:
- Improve the wins1 subroutine for finding winning/violating moves
- Improve the abstraction refinement strategy
- Add heuristics for initial move selection
- Combine with search-based techniques
- Optimize the IP solver interface
- Extend to additional problem types (MCN, etc.)

The scientist may NOT replace the core CEGAR expansion approach with a fundamentally different algorithm.

## Out of Bounds
- Replacing the CEGAR approach with pure QCDCL search
- Using a generic MILP solver without the CEGAR expansion framework
- Working on problem families that are known to be easy for search-based solvers
- Modifying the QRandomParity benchmark to trivialize it
