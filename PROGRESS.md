# Progress

## What Works

- **EQuIPS algorithm implementation**: Core CEGAR-based QIP solver implemented in `method/equips.py`
  - Implements Algorithm 1 (main EQuIPS loop) and Algorithm 2 (wins1)
  - Handles both existential (solve IP) and universal (find violating assignment) cases
  - Uses HiGHS as the IP solver backend
- **QRandomParity generator**: Procedural generation of QRandomParity instances in QIP encoding
- **Evaluation framework**: `eval/evaluate.py` runs EQuIPS on QRandomParity and computes metrics
- **Environment setup**: `environment/setup.sh` installs highspy (HiGHS Python bindings)

## Results

Not yet run — bash environment was stuck due to full filesystem CWD.

Expected behavior based on paper:
- EQuIPS should solve QRandomParity instances (all are UNSAT — existential can force t_n = s_n)
- Runtime should increase with n but remain feasible up to n=1000+ in the paper
- The algorithm's correctness depends on the IP solver correctly handling the constraint systems

## Remaining

- **Run the solver**: Submit a job to actually execute the code and validate correctness
- **Verify correctness**: EQuIPS should return UNSAT for all QRandomParity instances (they are unsatisfiable)
- **Benchmark comparison**: Compare runtime against paper's numbers
- **Optimize**: The wins1 implementation for the universal case may need refinement

## Issues

- **Disk space**: Root filesystem is full (64MB). Bash shell stuck because CWD is on full filesystem. Solved by using Write/Edit tools for file creation.
- **HiGHS limitations**: The paper uses Gurobi. HiGHS is an open-source alternative — may have different performance characteristics but should produce correct results.
- **wins1 for universal case**: The implementation of Problem (2) from the paper (finding an assignment that violates all constraints) is complex and may need debugging.

## Deviations from Paper

1. **IP Solver**: Paper uses Gurobi 12.0. We use HiGHS (open-source). Gurobi has better cutting planes; HiGHS is sufficient for the basic IP solves.
2. **QBF solvers**: Paper compares against QFUN, DepQBF, z3. We focus on EQuIPS only since installing QBF solvers would be complex.
3. **MCN problem instances**: Paper tests on MCN instances from [1]. We focus on QRandomParity which is procedurally generated and self-contained.
4. **Optimization**: Paper implements binary search and hybrid Yasol+EQuIPS approach. We implement binary search only.
