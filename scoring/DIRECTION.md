# Research Direction

Future scientist agents should treat this workspace as a benchmark for
quantified-integer satisfiability solvers in the same broad family as the paper:
expansion-based solving with iterative refinement on QIP instances.

## In Scope

- Improving how partial quantified expansions are chosen, reused, or refined.
- Improving how violating counterexamples are detected inside the same overall solving paradigm.
- Improving runtime on the scored QRandomParity settings without reducing solved coverage.
- Extending the benchmark with additional QIP experiments, provided the existing scored experiments remain comparable.

## Still In Family

The intended research direction is "better expansion-based QIP solving," not
"any method that solves some related optimization problem." A new method can be
substantially different internally, but it should still operate as a quantified
solver that reasons through iterative expansion/refinement rather than replacing
the benchmark with a generic unrelated paradigm.

## Out of Scope

- Swapping the task to a different formalism while reusing the same score entries.
- Treating the benchmark as a plain MILP dataset and ignoring the quantified structure.
- Beating the score by simplifying or filtering the benchmark rather than improving the solver.
- Reporting results from an unrelated search paradigm under the same experimental labels without documenting a new research direction.
