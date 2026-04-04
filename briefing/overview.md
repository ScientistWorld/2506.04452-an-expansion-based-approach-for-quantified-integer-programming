# Overview

- **Paper ID:** 2506.04452
- **Title:** An Expansion-Based Approach for Quantified Integer Programming
- **Domain:** Formal Methods / Optimization / SAT Solving
- **TL;DR:** First expansion-based (CEGAR) solver for Quantified Integer Programming (QIP), outperforming search-based QIP solvers on parity-based benchmarks and QBF expansion solvers on linear-encoded instances.

## Short Summary

The paper presents EQuIPS, the first expansion-based solver for Quantified Integer Programming (QIP). QIP extends QBF with integer variables and linear constraints, and extends integer programming with universal quantifiers. EQuIPS uses Counterexample-Guided Abstraction Refinement (CEGAR) adapted from QBF solving, calling an IP solver (Gurobi) to solve abstraction subproblems. The method iteratively builds partial expansions, refines them with found counter-moves, and converges to a solution or proof of unsatisfiability. The paper also shows how linear constraint encodings of parity problems outperform clausal encodings.

## Key Results

- **QRandomParity (n=1000)**: EQuIPS median runtime ~3.4s (10/100 unsolved); QFUNcms 100/100 unsolved — EQuIPS is dramatically faster
- **MCN problem instances**: EQuIPS solves 465/500+ instances, Yasol solves 431, MCN_CR solves 475 — EQuIPS competitive on large instances
- **Ablation**: EQuIPS using existential IP relaxation for initial move outperforms lower-bound initialization
