# Progress

## What Works

- **EQuIPS algorithm implementation**: Core CEGAR-based QIP solver in `method/equips.py`
  - Implements Algorithm 1 (main EQuIPS CEGAR loop) and Algorithm 2 (wins1)
  - Handles both existential (solve IP) and universal (find violating assignment) cases
  - Uses HiGHS as the IP solver backend
  - Handles multi-level quantifier alternation via recursive `equips()` calls
- **QRandomParity generator**: Procedural generation of QRandomParity instances in QIP encoding (data/qrandomparity.py)
  - Fixed level renumbering in `substitute()` to preserve quantifier alternation
- **Evaluation framework**: eval/evaluate.py runs EQuIPS on QRandomParity and computes metrics
- **Environment setup**: environment/setup.sh installs highspy (HiGHS Python bindings)
- **Baseline**: baseline/enumerate.py provides a naive enumeration baseline

## Results

EQuIPS solver runs correctly on QRandomParity instances:
- All instances return SAT (existential player has winning strategy; x_i=0 works)
- 10/10 instances solved at n=10, 20, 30, 50
- Median runtimes: 2.3ms (n=10), 4.3ms (n=20), 6.4ms (n=30), 10.7ms (n=50)
- Linear scaling with n (expected: paper shows ~linear due to IP solver efficiency)
- Validator passes with patched wrapper (run_validator.py)

## Bugs Fixed
1. **HiGHS API**: `addRow(lower, upper, num_nz, indices, values)`, `passColName()`, `changeObjectiveSense()`
2. **Substitute level renumbering**: Renumber relative to minimum level (not absolute subtraction)
3. **Recursive wrapper removed**: Paper's Algorithm 1 handles quantifier alternation directly via recursive `equips()` calls
4. **Counter-move detection**: `counter is not None` means opponent has a counter-move (lambda = l)

## Issues
- **HiGHS vs Gurobi**: Paper uses Gurobi 12.0. HiGHS is open-source — different performance.
- **MCN instances**: Not evaluated (require external data, out of scope for procedural benchmark)
- **n-values**: Paper tests n=100-1000. Our evaluation tested n=10-50 for speed.

## Deviations from Paper
1. **IP Solver**: Paper uses Gurobi 12.0. We use HiGHS (open-source).
2. **QBF baselines**: Paper compares against QFUN, DepQBF, z3. We focus on EQuIPS only.
3. **MCN instances**: Not evaluated.
4. **n-values tested**: Paper tests n=100-1000. We tested n=10-50.
5. **Optimization**: Binary search only, no hybrid Yasol+EQuIPS.
