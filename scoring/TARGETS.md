# Evaluation Targets

This file documents the scored targets that future scientist agents should optimize.
Every named target below corresponds to an experiment key that already exists in
`scoring/scores.json`.

Run evaluation with:

```bash
bash scripts/evaluate.sh /path/to/results.json
```

The evaluator writes `scoring/scores.json`.

## Primary Targets

### `qrandomparity_n100`
- What it tests: whether a solver improves turnaround time on the easier of the two scored QRandomParity settings.
- Primary metric: `median_runtime_s`
- Direction: lower is better
- Evaluation: produce a results JSON containing the full 100 scored runs for `n=100`, then call `bash scripts/evaluate.sh /path/to/results.json`

### `qrandomparity_n200`
- What it tests: whether a solver maintains or improves efficiency on the harder scored QRandomParity setting.
- Primary metric: `median_runtime_s`
- Direction: lower is better
- Evaluation: produce a results JSON containing the full 100 scored runs for `n=200`, then call `bash scripts/evaluate.sh /path/to/results.json`

## Constraint Targets

### `qrandomparity_n100`
- What it tests: the runtime improvement at `n=100` only counts if the solver still returns decisive answers on the benchmark instances.
- Constraint metric: `instances_solved`
- Direction: higher is better
- Evaluation: computed automatically by `bash scripts/evaluate.sh /path/to/results.json`

### `qrandomparity_n200`
- What it tests: the harder `n=200` setting should not be "improved" by timing out or declining to solve instances.
- Constraint metric: `instances_solved`
- Direction: higher is better
- Evaluation: computed automatically by `bash scripts/evaluate.sh /path/to/results.json`

## Ablation Targets

No ablation experiment is currently scored in `scoring/scores.json`.
Future agents should add an ablation target here only after adding the matching
experiment entry to both `scoring/reference.json` and `scoring/scores.json`.
