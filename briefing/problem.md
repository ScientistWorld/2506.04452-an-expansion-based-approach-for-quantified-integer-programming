# Problem Definition

## Research Question

Quantified Integer Programming (QIP) asks whether a bounded integer decision process with alternating existential and universal choices satisfies a linear constraint system. In the optimization variant, the existential side must also achieve the best worst-case objective value. The core problem in this workspace is to solve such quantified linear instances efficiently and correctly.

## Problem Setting

Each instance contains:
- Integer variables with finite lower and upper bounds
- An ordered quantifier prefix over variable blocks
- A linear feasibility system
- Optionally, additional linear restrictions on the universally quantified choices

The scored benchmark is a procedurally generated satisfiability family called
QRandomParity. It produces hard quantified instances by combining parity
relations under different variable orderings. The active scored slice in this
gym is a fixed 100-instance batch at `n=10`, which is large enough to separate
the expansion-based method from the exact search baseline in the current
open-source reproduction.

## Success Criteria

A successful solver should:
- Return the correct satisfiability outcome for each instance
- Respect the bounded integer domains and any universal-domain restrictions
- Solve more instances within the timeout and do so faster on the solved subset

This gym scores runtime and solved-instance count, so both speed and reliability matter.
