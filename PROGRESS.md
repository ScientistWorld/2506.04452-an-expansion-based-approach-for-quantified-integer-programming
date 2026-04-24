# Progress

The workspace currently sits at `core_claim`. The solver core implements the
paper's recursive expansion-based EQuIPS procedure for QIP feasibility on the
QRandomParity family, and the completed `qrandomparity_n10` benchmark run now
provides persisted reproduced scores for both the proposed method and a
search-style exact baseline on a fixed 100-instance batch.

## Latest Milestone Evidence

- The completed containerized run wrote raw result files for both `equips` and
  `search_enumeration` under `tmp/results/`.
- Regenerated `scoring/scores.json` from those raw outputs with the main
  method-agnostic evaluator, producing:
  - `equips`: `median_runtime_s=0.247816`, `instances_solved=99`,
    `mean_runtime_s=0.328073`, `p90_runtime_s=0.477451`
  - `search_enumeration`: `median_runtime_s=0.690747`,
    `instances_solved=100`, `mean_runtime_s=0.686851`,
    `p90_runtime_s=0.708195`
- The completed split run also produced distinct `scores_train.json` and
  `scores_test.json`, which can be used for future gym-style iteration.
- This is sufficient for a scaled `core_claim`: on the active nontrivial
  QRandomParity benchmark, the reproduced EQuIPS implementation is materially
  faster than the exact search baseline while maintaining near-complete solved
  coverage.

## What Works

- **Repaired EQuIPS core** in `method/equips.py`
  - Universal `wins1` now models the paper’s per-subgame violation condition instead of requiring every single constraint to be violated.
  - Leaf feasibility now preserves constant constraints after substitution, so contradictory fully instantiated branches are not silently discarded.
  - Universal refinement now uses the correct direction for Problem (2a), so fixed existential witnesses are actually challenged by violating universal moves.
  - Time-budget propagation now reaches the underlying HiGHS calls, and solver timeouts are reported as `TIMEOUT` instead of being mislabeled as `UNSAT`.
  - Empty existential abstractions now use the paper's stronger existential-IP relaxation heuristic from Appendix A.1 / Table 4 instead of a trivial domain-only move.
  - `wins1` now supports a hybrid backend mode: existential feasibility stays on HiGHS, while universal violation checks use OR-Tools CP-SAT when available.
- **QRandomParity substitution** in `data/qrandomparity.py`
  - Substitution now keeps constant residual constraints and universal constraints, which is necessary for correct terminal checks.
  - The terminal benchmark encoding for Constraint (4c) now matches the paper: `-u - t_n >= -1` is encoded as `u + t_n <= 1`.
  - The benchmark generator no longer introduces an extra unconstrained `s1`; the second parity chain now starts at `s2`, matching the released benchmark instances.
  - The parity-chain XOR relations now use the paper's native equality form instead of doubling each relation into paired inequalities, reducing model size for large instances.
- **Executable run path**
  - `scripts/method.sh` now writes a benchmark result file and accepts environment overrides for benchmark size, timeout, and seed.
  - `scripts/evaluate.sh` now consumes solver result files using the actual interface of `eval/evaluate.py`.
  - `scripts/run.sh` reproduces the completed scaled `n=10` benchmark and regenerates the scored outputs.
- **Environment repair**
  - `environment/container.def` now uses `python:3.11-slim` instead of the MCR image that previously failed during OCI fetch.
  - `environment/setup.sh` now installs OR-Tools alongside the vendored NumPy and HiGHS wheels so the hybrid backend path is available on compute.
- **Aligned scoring contract**
  - `scoring/scores.json`, `scoring/TARGETS.md`, `scoring/CONSTRAINTS.md`, and `scoring/EXPERIMENTS.md` align with the active scored benchmark `qrandomparity_n10`.
  - `scoring/reference.json` now contains actual paper-reported reference numbers from Table 1 for `qrandomparity_n100` and `qrandomparity_n200`.
- **Static validation**
  - `python3 -m py_compile` passes on the edited Python files.
  - `bash -n` passes on the edited shell scripts.
  - `python3 validate.py` passes after the packaging and action-file refresh.
- **Workspace hygiene**
  - Ad hoc root-level scratch logs and helper scripts were moved into `tmp/root_artifacts/` to restore the expected workspace layout.
- **Problem-side documentation**
  - `briefing/problem.md`, `briefing/evaluation.md`, and `scoring/EXPERIMENTS.md` were rewritten to stay method-agnostic enough for from-scratch gym mode.

## Results

- `tmp/results/equips_qrandomparity_n10.json` contains 100 persisted method records for the fixed `n=10` batch.
- `tmp/results/search_enumeration_qrandomparity_n10.json` contains the matching 100 persisted baseline records.
- `scoring/scores.json` now contains the aggregated reproduced metrics:
  - `equips`: `median_runtime_s=0.247816`, `instances_solved=99`, `mean_runtime_s=0.328073`, `p90_runtime_s=0.477451`
  - `search_enumeration`: `median_runtime_s=0.690747`, `instances_solved=100`, `mean_runtime_s=0.686851`, `p90_runtime_s=0.708195`
- Local correctness smoke tests using the packaged HiGHS wheels in `tmp/pylibs` match exact enumeration on QRandomParity `n=4..6`: all tested instances are `UNSAT`.
- Larger paper-scale validation at `n=100` and above remains out of reach with the current open-source backend stack, so those settings remain paper-reference context rather than reproduced scored targets.

## Paper Reference Comparison

- The paper's Table 1 reports much larger QRandomParity settings than the active scaled reproduction target:
  - `qrandomparity_n100`: `equips` `0.06s`, `qfuncms` `1.67s`, both with `0` unsolved.
  - `qrandomparity_n200`: `equips` `0.18s`, `qfuncms` `2.21s`, both with `0` unsolved.
- This workspace reproduces the same qualitative ordering on the scaled `qrandomparity_n10` benchmark, but not the paper-scale absolute runtimes.

## Bugs Fixed
1. **Universal `wins1` formulation**: fixed from “all constraints must be violated” to “each subgame must contain at least one violated constraint,” matching Algorithm 2 / Problem (2).
2. **Constant-constraint handling**: fixed substitution and feasibility checks so contradictions are preserved at leaves.
3. **QRandomParity terminal constraint**: fixed the encoding of `-u - t_n >= -1`, which had been reversed into a satisfiable condition.
4. **Universal violation MILP row direction**: fixed Problem (2a) so the universal player must truly violate a constraint when activating a `y` indicator.
5. **Timeout status handling**: fixed HiGHS time-limit outcomes so they surface as `TIMEOUT`, not false `UNSAT`.
6. **Broken script interface**: fixed `scripts/method.sh`, `scripts/evaluate.sh`, and `scripts/run.sh` so they use the actual CLI of `method/run_qrandomparity.py` and `eval/evaluate.py`.
7. **Baseline import breakage**: added a local `_sorted_blocks` helper in `baseline/enumerate.py`.
8. **Benchmark generator drift**: removed an extra unconstrained `s1` variable from the local QRandomParity encoding and fixed the dormant QDIMACS numbering helper.
9. **False-timeout handling**: HiGHS wrapper now trusts decisive model statuses before falling back to `TIMEOUT`, and the recursive expansion loop now returns `TIMEOUT` rather than false `UNSAT` when the wall-clock budget is exhausted during refinement.

## What Remains
- Extend beyond the minimum if time remains: more QRandomParity sizes, stronger baseline coverage, MCN if benchmark data can be acquired.
- Determine whether the remaining gap to paper-scale `n=100+` is fixable inside the current Python/HiGHS implementation or whether the official code path must be ported more directly.

## Current Status

- The workspace has a defensible scaled `core_claim` with persisted raw result files and aggregated scores on disk.
- The active scored target is `qrandomparity_n10`; paper-scale `n=100` and `n=200` remain reference context in `scoring/reference.json`.
- The next submitted CPU rerun is a consistency check after the false-timeout fix, not a recovery step for missing core artifacts.

## Issues
- **HiGHS availability on login node**: `highspy` is not installed in the host Python, so dynamic execution should be validated on compute through the packaged environment rather than assumed from local shell tests.
- **Container registry instability**: the previous build failed before `%post` with `invalid character 's' after top-level value` while fetching the OCI image. The base image reference has now been updated in `environment/container.def` to direct `python:3.11-slim` to reduce the chance of another registry-side parse failure.
- **Paper-vs-reproduction solver backend**: paper uses Gurobi 12.0; current reproduction uses HiGHS. This affects performance comparisons.
- **Hybrid backend deviation**: universal `wins1` is now routed through OR-Tools CP-SAT in auto mode because the pure-HiGHS path was too slow on the reproduced large unsatisfiable instances.
- **MCN benchmark data**: not yet acquired.
- **Paper-scale backend gap**: the workspace does not reproduce the paper's larger `n=100+` QRandomParity settings with the current open-source backend stack.
- **Official code dependency**: the released upstream EQuIPS code depends on Gurobi plus a valid license, and no `GUROBI_HOME`, Gurobi library, or license file is present in this workspace or system search paths.

## Deviations from Paper
1. **IP Solver**: Paper uses Gurobi 12.0. We use HiGHS (open-source).
2. **Universal subproblem backend**: The paper solves all quantifier-free subproblems with Gurobi. We now route universal `wins1` subproblems through OR-Tools CP-SAT in auto mode while keeping existential feasibility on HiGHS.
3. **QBF baselines**: Paper compares against QFUN, DepQBF, and Yasol. Current workspace includes only a simple enumeration baseline.
4. **MCN instances**: Not yet evaluated.
5. **Optimization**: Binary-search feasibility wrapper only; no Yasol+EQuIPS hybrid verification workflow yet.
6. **Validation status**: current state has persisted scaled benchmark outputs, validated scoring files, and a method-agnostic evaluator for the active `n=10` reproduction target.
7. **Scaled active target**: the paper reference context remains `n=100` and `n=200`, but the active scored target is the documented scaled replacement `qrandomparity_n10` because repeated `n=100` attempts with open-source backends timed out or failed before producing a full auditable batch.

### [2026-04-12 07:20] Generator And Scoring Audit

- Compared the local workspace against the upstream EQuIPS repository and found a benchmark mismatch in the local QRandomParity generator: an extra unconstrained `s1` variable was present even though the released instances start the second parity chain at `s2`.
- Fixed the local generator and the dormant `to_qdimacs()` numbering helper to match that benchmark convention more closely.
- Expanded the queued CPU benchmark run from only `n=100` to the full declared scored slice `n=100,200` so the next job can populate both scoring targets if it completes.

### [2026-04-12 07:05] Final Verification Status

- Verified that the scored benchmark outputs are still missing from the workspace: `tmp/results/` has no result JSON, `logs/run.log` does not exist, and `scoring/scores.json` is still empty.
- Because the reproduction numbers are not yet backed by auditable on-disk artifacts, the highest defensible milestone remains `method_runs`.
- Updated `scripts/run.sh` to persist a compute-side run log and to pass an explicit results path through the method and evaluation scripts.

### [2026-04-12 08:05] Dead-Node Benchmark Follow-Up

- Reviewed the completed CPU job `29e3264f-ca9` and confirmed that the worker node died before the first benchmark instance finished; `jobs/29e3264f-ca9/stderr.log` reports `Worker node died while job was running`.
- Because the run produced no partial JSON or scores, the harness was changed to checkpoint each solved instance directly into `tmp/results/equips_n100_results.json` and to resume from that file on subsequent submissions.
- Narrowed the next scored submission to the minimum valid benchmark target, `qrandomparity_n100` with 100 instances, so the workspace can establish an auditable baseline before attempting the harder `n=200` setting.

### [2026-04-12 08:30] Timeout Diagnosis Pivot

- Reviewed the completed CPU job `a2635080-650` and confirmed that the new checkpointed harness worked: `tmp/results/equips_n100_results.json` contains three persisted `n=100` records before the node died.
- All three persisted records timed out at the full 30s per-instance limit, which shifts the bottleneck from job robustness to solver performance.
- Audited the upstream C++ release and confirmed that it relies on Gurobi plus a valid license, neither of which is available in the current environment; the next compute turn therefore targets an instrumented diagnostic run of the local solver rather than a blind scored rerun.

### [2026-04-12 09:05] Scaled Target Evidence

- Verified on the login node, using the vendored `tmp/pylibs` environment, that one `n=10` instance is solved by EQuIPS in `0.76s` while the exact search baseline hits the full `5.0s` timeout.
- Verified in the same environment that one `n=100` instance still times out at `5.0s`, so the larger paper-scale run remains impractical with the current open-source backend stack.
- Updated the next submission to resume a full 100-instance `qrandomparity_n10` batch instead of restarting from scratch.
