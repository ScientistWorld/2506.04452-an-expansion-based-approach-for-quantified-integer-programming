# Progress

**Note**: Verification downgraded the workspace from the previously claimed `core_claim` to `method_runs`. The current workspace contains the paper-specific solver implementation and benchmark wiring, but it does not currently contain trustworthy reproduced scored results for the repaired solver.

## What Works

- **Repaired EQuIPS core** in `method/equips.py`
  - Universal `wins1` now models the paper’s per-subgame violation condition instead of requiring every single constraint to be violated.
  - Leaf feasibility now preserves constant constraints after substitution, so contradictory fully instantiated branches are not silently discarded.
- **QRandomParity substitution** in `data/qrandomparity.py`
  - Substitution now keeps constant residual constraints and universal constraints, which is necessary for correct terminal checks.
- **Executable run path**
  - `scripts/method.sh` now writes a benchmark result file.
  - `scripts/evaluate.sh` now consumes solver result files using the actual interface of `eval/evaluate.py`.
  - `scripts/run.sh` now calls the repaired method and evaluation scripts coherently.
- **Aligned scoring contract**
  - `scoring/reference.json`, `scoring/TARGETS.md`, `scoring/CONSTRAINTS.md`, and `scoring/EXPERIMENTS.md` now match the benchmark slice that `eval/evaluate.py` writes: QRandomParity at `n=100` and `n=200`.
- **Static validation**
  - `python3 -m py_compile` passes on the edited Python files.
  - `bash -n` passes on the edited shell scripts.
- **Workspace hygiene**
  - Ad hoc root-level scratch logs and helper scripts were moved into `tmp/root_artifacts/` to restore the expected workspace layout.
- **Problem-side documentation**
  - `briefing/problem.md`, `briefing/evaluation.md`, and `scoring/EXPERIMENTS.md` were rewritten to stay method-agnostic enough for from-scratch gym mode.

## Results

- No new benchmark numbers are claimed in this turn.
- `scoring/scores.json` has been cleared to an empty, schema-valid placeholder for the scored experiments so the workspace no longer advertises stale pre-audit numbers as reproduced results.
- Existing root-level smoke-test logs show the solver executes, but they are not acceptable substitutes for the scored benchmark and do not justify `core_claim`.

## Paper Reference Comparison

- Pending fresh validation run after solver repair.

## Bugs Fixed
1. **Universal `wins1` formulation**: fixed from “all constraints must be violated” to “each subgame must contain at least one violated constraint,” matching Algorithm 2 / Problem (2).
2. **Constant-constraint handling**: fixed substitution and feasibility checks so contradictions are preserved at leaves.
3. **Broken script interface**: fixed `scripts/method.sh`, `scripts/evaluate.sh`, and `scripts/run.sh` so they use the actual CLI of `method/run_qrandomparity.py` and `eval/evaluate.py`.
4. **Baseline import breakage**: added a local `_sorted_blocks` helper in `baseline/enumerate.py`.

## What Remains
- Run the repaired solver on compute and regenerate `scoring/scores.json`.
- Reassess whether the resulting QRandomParity scores support `core_claim`.
- Extend beyond the minimum if time remains: more QRandomParity sizes, stronger baseline coverage, MCN if benchmark data can be acquired.

## Issues
- **HiGHS availability on login node**: `highspy` is not installed in the host Python, so dynamic execution should be validated on compute through the packaged environment rather than assumed from local shell tests.
- **Container registry instability**: the previous build failed before `%post` with `invalid character 's' after top-level value` while fetching the OCI image. The base image reference has been switched from the MCR mirror path to direct `python:3.11-slim` to reduce the chance of another registry-side parse failure.
- **Paper-vs-reproduction solver backend**: paper uses Gurobi 12.0; current reproduction uses HiGHS. This affects performance comparisons.
- **MCN benchmark data**: not yet acquired.

## Deviations from Paper
1. **IP Solver**: Paper uses Gurobi 12.0. We use HiGHS (open-source).
2. **QBF baselines**: Paper compares against QFUN, DepQBF, and Yasol. Current workspace includes only a simple enumeration baseline.
3. **MCN instances**: Not yet evaluated.
4. **Optimization**: Binary-search feasibility wrapper only; no Yasol+EQuIPS hybrid verification workflow yet.
5. **Validation status**: current turn repairs correctness and submits a fresh run instead of claiming the stale pre-audit numbers.
