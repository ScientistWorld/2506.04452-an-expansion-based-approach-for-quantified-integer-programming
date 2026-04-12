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

### [2026-04-09 08:45] - method_runs
- Final verification confirmed that the repaired workspace layout, scoring files, and problem/method separation are largely in shape for future gym use.
- Re-checking the workspace found no persisted outputs from the submitted validation run: `tmp/results/` is empty and `scoring/scores.json` still has no reproduced method entries.
- Closed the paper at `method_runs` because the current on-disk state does not support `core_claim`.

### [2026-04-12 02:06] - method_runs
- Reopened the workspace after confirming the solver core is a real EQuIPS-style recursive expansion/CEGAR implementation rather than a surrogate.
- Fixed packaging protocol violations so `environment/container.def` now stays OS-only and `scripts/download.sh` no longer installs Python packages.
- Prepared a new CPU validation submission on the scored `qrandomparity_n100` and `qrandomparity_n200` settings to regenerate auditable benchmark artifacts.

### [2026-04-12 02:20] - method_runs
- Final verification found that the queued validation job was still using a 5-instance smoke-test slice, which is not a valid scored benchmark because the reference experiments use 100 instances per setting.
- Hardened `eval/evaluate.py` so the scored `n=100` and `n=200` experiments now require the full 100-instance batch instead of silently accepting undersized samples.
- Replaced the queued smoke test with a normal CPU submission for the minimum full-size scored benchmark (`n=100`, 100 instances) to establish an auditable `scores.json` artifact.

### [2026-04-12 07:20] - method_runs
- Audited the local workspace against the upstream EQuIPS repository and corrected a QRandomParity benchmark mismatch: the local generator had included an extra unconstrained `s1` variable that is not present in the released benchmark instances.
- Fixed the dormant QDIMACS helper numbering for the same benchmark family so the local tooling no longer encodes an invalid variable map.
- Updated the queued CPU validation run to cover both scored settings (`n=100` and `n=200`) with 100 instances each.

### [2026-04-12 07:05] - method_runs
- Final verification found that the workspace still lacks the auditable artifacts needed to justify `core_claim`: there is no persisted benchmark result file in `tmp/results/`, no `logs/run.log`, and `scoring/scores.json` is empty.
- Kept the milestone at `method_runs` and prepared another CPU submission rather than incorrectly signaling done.
- Updated `scripts/run.sh` so the next compute-side run will write a persistent run log and use an explicit results path for both method execution and evaluation.

### [2026-04-12 08:05] - method_runs
- Reviewed the completed CPU job `29e3264f-ca9`; the worker node died before the benchmark emitted any instance-level output, so it did not advance the reproduction milestone.
- Hardened the benchmark harness so `method/run_qrandomparity.py` now writes results incrementally and can resume from an existing JSON file after interruption.
- Narrowed the next scored submission to the minimum valid target `qrandomparity_n100` (100 instances) to establish a first auditable reproduced baseline before retrying the harder `n=200` setting.

### [2026-04-12 08:30] - method_runs
- Reviewed the completed CPU job `a2635080-650`; it persisted three `qrandomparity_n100` records before the worker node died, and all three hit the full 30s per-instance timeout.
- This is real progress in diagnosis because it proves the current bottleneck is solver performance, not just missing checkpointing or missing logs.
- Added solver instrumentation and switched the next submission to a short diagnostic matrix that records recursion, refinement, and abstraction-growth statistics instead of attempting another full scored batch immediately.
