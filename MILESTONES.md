# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-04-09 07:40] - none
- Audited the existing EQuIPS implementation against Algorithms 1 and 2 in the paper.
- Found correctness issues that invalidate the previous `core_claim` bookkeeping:
  universal `wins1` was enforcing violation of every constraint instead of one per subgame,
  and substitution dropped constant constraints, hiding leaf-level contradictions.
- Repaired the solver core and fixed the broken script interface so the workspace is ready for a fresh validation run.

### [2026-04-09 08:10] - none
- Cleared stale `scoring/scores.json` contents so the workspace no longer claims pre-audit benchmark results.
- Switched the container base image from the MCR mirror path to direct `python:3.11-slim` after the prior build failed during OCI metadata fetch.
- Fixed `scripts/download.sh` to follow the environment protocol (`uv pip install --system`) and validated the scoring/structure files with `python validate.py`.

### [2026-04-09 08:25] - method_runs
- Final verification found that the workspace has a real implementation of the paper's algorithm and executable benchmark wiring, but no trustworthy reproduced scored results for the repaired solver.
- Rewrote problem-side docs to remove method leakage and cleaned root-level scratch artifacts into `tmp/root_artifacts/`.
- Prepared the workspace for a fresh scored validation run; `core_claim` is pending actual benchmark results.

### [2026-04-09 08:41] - method_runs
- Fixed a QRandomParity encoding bug in Constraint (4c): `-u - t_n >= -1` had been translated with the wrong inequality direction, which made benchmark instances spuriously satisfiable.
- Fixed the universal `wins1` MILP so Problem (2a) is added with the correct inequality direction; universal refinement now finds real violating countermoves.
- Added timeout propagation and `TIMEOUT` reporting, restored universal-constraint checks at fully substituted leaves, and added the paper's existential-IP relaxation heuristic for the first move on empty existential abstractions.
- Verified locally with the packaged HiGHS wheels that `n=4..6` QRandomParity instances are `UNSAT` for both exact enumeration and EQuIPS; prepared a CPU test-node run for the scored `n=100,200` slice.

## Stop Justification
