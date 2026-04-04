# Scientist Constraints

## Problem
The scientist must work on the same QIP solving problem as the paper:
- QIP feasibility solving (SAT/UNSAT)
- QIP optimization (finding optimal objective value)
- The EQuIPS expansion-based approach (CEGAR with IP solver backend)

## Algorithm
The scientist must use an expansion-based approach with CEGAR for QIP.
- The core algorithm must use iterative abstraction refinement
- The IP solver backend must solve linear integer programs
- The solver must handle both existential and universal quantifiers
- Binary search can be used for optimization problems

## Data
The scientist must use the QRandomParity problem family for evaluation:
- Generate instances with n ∈ {10, 20, 30, 50, 100, 200}
- Use at least 10 random instances per n value
- Use random seed 42 for reproducibility

## Out of Bounds
- Replacing the CEGAR expansion-based approach with a pure search-based method
- Using a black-box solver without implementing the expansion/refinement logic
- Evaluating only on custom/easy instances that trivialize the problem
- Modifying the QRandomParity problem encoding to make it easier

## Compliance Checklist
- [ ] Solver uses CEGAR-based expansion approach (not pure search)
- [ ] IP solver backend handles linear integer constraints
- [ ] Evaluation uses QRandomParity with specified n values
- [ ] At least 10 instances per n value
- [ ] Reports runtime and instances-solved metrics
