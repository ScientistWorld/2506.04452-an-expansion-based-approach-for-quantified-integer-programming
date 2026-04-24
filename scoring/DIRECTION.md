# Research Direction

Future scientist agents should treat this workspace as a benchmark for
quantified-integer satisfiability solving on the QRandomParity family.

## In Scope

- Improving runtime on `qrandomparity_n10` without reducing solved coverage.
- Developing stronger quantified-integer solvers for the same benchmark family.
- Adding larger QRandomParity settings as new experiments while keeping the
  existing scored target comparable.
- Improving the search-style baseline or adding additional exact baselines under
  separate method names.

## Out of Scope

- Replacing QRandomParity with an easier benchmark while keeping the same score label.
- Converting the task into an unquantified MILP benchmark.
- Claiming improvement by changing timeout rules, batch size, or seeds without
  recording a new experiment name.
