# Evaluation Targets

This file documents the scored targets that future scientist agents should optimize.
These target names should appear in `scoring/scores.json` after running:

```bash
bash scripts/reproduce.sh
```

## Active Scored Target

### `qrandomparity_n10`
- What it tests: a scaled but nontrivial QRandomParity slice where a candidate solver can be compared directly against a search-style exact baseline.
- Primary metric: `median_runtime_s`
- Direction: lower is better
- Evaluation: run both `scripts/method.sh` and `scripts/baseline.sh` on the same 100-instance `n=10` batch, then call `bash scripts/evaluate.sh <method_results> <baseline_results>`

## Constraint Target

### `qrandomparity_n10`
- What it tests: runtime gains only count if the solver still returns decisive answers across the fixed batch.
- Constraint metric: `instances_solved`
- Direction: higher is better
- Evaluation: computed automatically by `scripts/evaluate.sh`

## Reference Context

The paper's reported large-instance settings remain in `scoring/reference.json`:

- `qrandomparity_n100`
- `qrandomparity_n200`

Those paper-scale settings are reference-only context in this open-source workspace until the larger run becomes practical with the available backend.
