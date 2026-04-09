# Scientist Constraints

## Problem
The scientist must work on the same QIP feasibility problem family used for the scored benchmark:
- SAT/UNSAT solving for quantified integer programs
- QRandomParity instances generated from the provided benchmark generator
- The scored settings are the large-instance QRandomParity runs at n=100 and n=200

## Algorithm
The scientist must use an expansion-based approach with CEGAR for QIP.
- The core algorithm must use iterative abstraction refinement
- The IP solver backend must solve linear integer programs
- The solver must handle both existential and universal quantifiers

## Data
The scientist must use the QRandomParity problem family for evaluation:
- Generate instances with n in {100, 200} for the scored benchmark
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
- [ ] Evaluation uses QRandomParity with n=100 and n=200
- [ ] At least 10 instances per n value
- [ ] Reports runtime and instances-solved metrics
