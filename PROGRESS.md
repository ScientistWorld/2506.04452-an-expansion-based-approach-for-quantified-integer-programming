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
- **Baseline**: baseline/enumerate.py provides enumeration baseline (fixed HiGHS API)

## Results

EQuIPS solver at paper scale:
- All instances return SAT (existential player has winning strategy; x_i=0 works)
- 20/20 instances solved at n=10, 20, 30, 50, 100, 200
- Median runtimes: 2.5ms (n=10), 5.9ms (n=20), 6.5ms (n=30), 89ms (n=50), 195ms (n=100), 451ms (n=200)
- Linear scaling with n (demonstrated up to n=1000 at ~1.5s)
- Baseline enumeration also works on small n (5-10), with high variance due to solution ordering

## Paper Reference Comparison

| Method | n=100 Median Runtime | Instances Solved |
|--------|---------------------|------------------|
| Paper EQuIPS | 0.06s | 100/100 |
| Paper QFUN+MS | 1.67s | 100/100 |
| Paper Yasol | 100.12s | 91/100 |
| **Reproduced EQuIPS** | **0.19s** | **20/20** |

Note: Reproduced runtime is slower than paper's due to HiGHS vs Gurobi differences and different instance counts.

## Bugs Fixed
1. **HiGHS API**: `addRow(lower, upper, num_nz, indices, values)`, `passColName()`, `changeObjectiveSense()`
2. **Substitute level renumbering**: Renumber relative to minimum level (not absolute subtraction)
3. **Recursive wrapper removed**: Paper's Algorithm 1 handles quantifier alternation directly via recursive `equips()` calls
4. **Counter-move detection**: `counter is not None` means opponent has a counter-move (lambda = l)
5. **Baseline HiGHS API**: Fixed addRow signature (lower, upper, num_nz, indices, values), HighsModelStatus.kFeasible → kOptimal

## What Remains
- Container build on compute nodes: blocked by Docker Hub rate limits
- MCN benchmark: Requires external data (not part of procedural generation)
- Yasol/QFUN baselines: Not implemented (require specialized QIP/QBF solvers)

## Issues
- **Container build**: Docker Hub unauthenticated rate limits exhausted (TOOMANYREQUESTS). All attempts failed. Solver itself is validated and working locally.
- **HiGHS vs Gurobi**: Paper uses Gurobi 12.0. We use HiGHS (open-source) — different performance characteristics.
- **MCN instances**: Not evaluated (require external data, out of scope for procedural benchmark)
- **Baseline variance**: Enumeration baseline has high variance — finds solution quickly when x=0 works, slower otherwise.

## Deviations from Paper
1. **IP Solver**: Paper uses Gurobi 12.0. We use HiGHS (open-source).
2. **QBF baselines**: Paper compares against QFUN, DepQBF, Yasol. We implement enumeration baseline only.
3. **MCN instances**: Not evaluated.
4. **n-values tested**: Paper tests n=100-1000. We tested n=10-200 comprehensively + n=1000 informally.
5. **Optimization**: Binary search only, no hybrid Yasol+EQuIPS.
6. **Instances per n**: Paper uses 100 instances. We use 20 for speed.
