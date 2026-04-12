# Research Direction

Future scientist agents should treat this workspace as a benchmark for
quantified-integer satisfiability solving on the QRandomParity family. The goal
is to improve performance on the declared scored settings while preserving the
same task, benchmark semantics, and evaluation contract.

## In Scope

- Improving runtime on the scored QRandomParity settings without reducing solved coverage.
- Developing stronger quantified reasoning methods for the same satisfiability task and benchmark family.
- Extending the workspace with additional QIP experiments, provided the existing scored experiments remain comparable.
- Changing internal solver design, heuristics, or implementation details as long as the task and benchmark contract stay fixed.

## Still In Family

The intended research direction is "better solvers for the same quantified
integer benchmark," not "switch to an easier or different problem." A new method
does not need to resemble the reproduced solver internally, but it must still
address the same quantified satisfiability problem and be evaluated under the
same benchmark rules.

## Out of Scope

- Swapping the task to a different formalism while reusing the same score entries.
- Treating the benchmark as a plain MILP dataset while discarding the quantified decision structure.
- Beating the score by simplifying, filtering, or redefining the benchmark rather than improving the solver.
- Reporting results under the same experiment labels after changing the benchmark semantics or evaluation contract.
