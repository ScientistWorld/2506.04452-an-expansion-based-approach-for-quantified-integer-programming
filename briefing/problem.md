# Problem Definition

## Research Question

Quantified Integer Programming (QIP) extends Quantified Boolean Formulas (QBF) with general integer variables and linear constraints, and extends Integer Programming with variable quantification. How can we solve QIP problems efficiently? The paper focuses on QIP feasibility and optimization, where variables are either existentially (∃) or universally (∀) quantified, bounded by integer domains, and constrained by linear inequalities.

## Why It Matters

QIP provides a unified framework for modeling adversarial decision-making and robust optimization, where universal variables represent uncertainty an adversary can exploit. Existing QIP solvers use search-based (QCDCL) methods. The paper shows that expansion-based methods—previously unexplored for QIP—can outperform search-based solvers on certain problem classes.

## Success Criteria

A successful QIP solver should:
- Correctly determine whether a QIP instance is satisfiable (existential player wins) or unsatisfiable (universal player wins)
- For optimization problems: find the optimal objective value
- Solve instances within reasonable time limits
- Handle problems with polyhedral uncertainty sets (universal constraints)

The evaluation uses runtime and number of instances solved as the primary metrics: faster solvers and solvers that complete more instances within a time limit are better.
