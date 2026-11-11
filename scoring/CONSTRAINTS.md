# Scientist Constraints

What must stay fixed when claiming an improvement.

## Evaluation contract
- Solvers are scored only through `scripts/evaluate_test.sh` /
  `scripts/evaluate_train.sh` (no arguments): a directory with `solver.json`
  whose command takes `INSTANCE.qlp ANSWER.json` and writes
  `{"answer": "TRUE" | "FALSE" | "UNKNOWN"}`.
- The CPU budget (10 s per instance, whole process tree, measured by the
  evaluator), the wall-clock watchdog, the instance ladders and the
  wrong-answer rule are part of the evaluator and must not be changed.
- Answer `UNKNOWN` when not certain: one wrong decision zeroes every metric.

## Data
- Instances are produced by `data/benchmark.py` (train) and its hidden copy
  (test).  Do not change the generator, the ladder sizes or the per-size
  composition; new benchmark variants go under new experiment names.
- Do not read anything under `eval/test/` from a solver, and do not use
  answers or seeds of instances at solve time.

## Solver
- A solver must decide each instance from its QLP text alone.  Decoding the
  instance generator (recognising a family and running a family-specific
  routine instead of solving the QIP) is not a method improvement.
- Parallelism is allowed but all CPU time of all processes counts.
