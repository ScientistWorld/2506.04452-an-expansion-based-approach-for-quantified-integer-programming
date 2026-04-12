# Evaluation Targets

This file documents the scored targets that future scientist agents should optimize.
These target names are defined by the benchmark contract in `scoring/reference.json`
and should appear in `scoring/scores.json` once a scored run has been completed.

Run evaluation with:

```bash
bash scripts/evaluate.sh /path/to/results.json
```

The evaluator writes `scoring/scores.json`.

## Active Scored Target

### `qrandomparity_n100`
- What it tests: whether a solver improves turnaround time on the reproduced large-instance QRandomParity setting.
- Primary metric: `median_runtime_s`
- Direction: lower is better
- Evaluation: produce a results JSON containing the full 100 scored runs for `n=100`, then call `bash scripts/evaluate.sh /path/to/results.json`

## Constraint Targets

### `qrandomparity_n100`
- What it tests: the runtime improvement at `n=100` only counts if the solver still returns decisive answers on the benchmark instances.
- Constraint metric: `instances_solved`
- Direction: higher is better
- Evaluation: computed automatically by `bash scripts/evaluate.sh /path/to/results.json`

## Ablation Targets

No ablation experiment is currently scored in `scoring/scores.json`.
Future agents should add an ablation target here only after adding the matching
experiment entry to both `scoring/reference.json` and `scoring/scores.json`.

## Unreproduced Reference Context

`scoring/reference.json` also includes `qrandomparity_n200` from the paper for future expansion.
It is not part of the current reproduced baseline until a scored run for that setting is written to `scoring/scores.json`.
