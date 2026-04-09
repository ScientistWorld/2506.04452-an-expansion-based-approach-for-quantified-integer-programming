# Progress

**Note**: I audited the existing reproduction before submitting a new job and found that the prior milestone bookkeeping was overstated. The current turn repairs solver correctness and job wiring, then submits a fresh validation run.

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
- **Static validation**
  - `python3 -m py_compile` passes on the edited Python files.
  - `bash -n` passes on the edited shell scripts.

## Results

- No new benchmark numbers are claimed in this turn.
- Existing numbers in `scoring/scores.json` should be treated as stale until the repaired solver is re-run on compute.

## Paper Reference Comparison

- Pending fresh validation run after solver repair.

## Bugs Fixed
1. **Universal `wins1` formulation**: fixed from “all constraints must be violated” to “each subgame must contain at least one violated constraint,” matching Algorithm 2 / Problem (2).
2. **Constant-constraint handling**: fixed substitution and feasibility checks so contradictions are preserved at leaves.
3. **Broken script interface**: fixed `scripts/method.sh`, `scripts/evaluate.sh`, and `scripts/run.sh` so they use the actual CLI of `method/run_qrandomparity.py` and `eval/evaluate.py`.
4. **Baseline import breakage**: added a local `_sorted_blocks` helper in `baseline/enumerate.py`.

## What Remains
- Run the repaired solver on compute and regenerate `scoring/scores.json`.
- Reassess milestone level from actual post-fix results.
- Extend beyond the minimum if time remains: more QRandomParity sizes, stronger baseline coverage, MCN if benchmark data can be acquired.

## Issues
- **HiGHS availability on login node**: `highspy` is not installed in the host Python, so dynamic execution should be validated on compute through the packaged environment rather than assumed from local shell tests.
- **Paper-vs-reproduction solver backend**: paper uses Gurobi 12.0; current reproduction uses HiGHS. This affects performance comparisons.
- **MCN benchmark data**: not yet acquired.

## Deviations from Paper
1. **IP Solver**: Paper uses Gurobi 12.0. We use HiGHS (open-source).
2. **QBF baselines**: Paper compares against QFUN, DepQBF, and Yasol. Current workspace includes only a simple enumeration baseline.
3. **MCN instances**: Not yet evaluated.
4. **Optimization**: Binary-search feasibility wrapper only; no Yasol+EQuIPS hybrid verification workflow yet.
5. **Validation status**: current turn repairs correctness and submits a fresh run instead of claiming the stale pre-audit numbers.
