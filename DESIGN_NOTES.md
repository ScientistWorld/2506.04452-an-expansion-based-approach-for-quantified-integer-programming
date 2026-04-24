# Design Notes — Iteration 5 (designer_stage_2)

## What was checked

### Failure-mode audit

1. **evaluate_test.sh copy-paste bug** — Both scripts reviewed side-by-side. `evaluate_test.sh` correctly invokes `eval/test/evaluate.py` and writes to `scoring/scores_test.json`. No issue.
2. **Hardcoded method defaults** — Both scripts pass results files as positional arguments and default to a single path (`/home/user/tmp/results/equips_results.json`). This is a known limitation: future variants added by improve-mode agents would require explicit argument passing. However, the scripts do enumerate from disk correctly when arguments are provided, and this pattern matches the existing `evaluate.sh`.
3. **Paper-agreement metrics** — No metric in `reference.json` measures deviation from the paper. All metrics measure the underlying scientific quantity (runtime, solved count). No `author`, `paper`, `published`, `vs_paper`, or equivalent in metric names.
4. **Leakage between train and test** — `eval/train/` and `eval/test/` are fully independent. No cross-imports.
5. **Coverage mismatch** — `reference.json` experiments (`qrandomparity_n100`, `qrandomparity_n200`) map to `SLICE_INSTANCE_IDS` keys in both eval files. Every metric in `reference.json` is computed by `eval/` code.

### Split style analysis

The first pass uses a 50/50 data split by instance ID (even=train, odd=test). For this problem:
- **Pros**: Simple, clean split; train and test have equal sample counts; legitimate methods should perform consistently across both.
- **Cons**: Both n=100 and n=200 use identical split, so any instance-specific shortcut would affect both.
- **Verdict**: Adequate for this SAT-solver runtime benchmark. The primary defense is metric triangulation (see below), not split complexity.

### Saturation analysis

The reproduced method (EQuIPS) solves all 100 instances for both n=100 and n=200 with fast runtime (~0.06s and ~0.18s median). `instances_solved` is likely to saturate at 100 for any legitimate solver on this batch. The 50/50 split means each slice has 50 instances, so saturation is possible but not certain (a shortcut method that gives up on harder instances could regress). `median_runtime_s` has room to improve (current ~0.06s at n=100) but may also compress for very fast solvers.

**Runtime concern**: At n=100, median runtimes of 0.06s are near the measurement floor. A future method that's marginally faster would produce identical median values due to discretization. This is not a design flaw, but a practical limitation of the benchmark at small n.

## What was changed

### 1. Added `mean_runtime_s` metric (both slices + reference.json)

The first pass relied on `median_runtime_s` and `p90_runtime_s`. Median is robust but can miss systematic differences: a method that's slightly faster on most instances but slightly slower on outliers will show identical median. Mean is sensitive to outliers in a complementary way.

Added to both `eval/train/evaluate.py` and `eval/test/evaluate.py`. Added to `reference.json` with coefficient -0.3 (secondary to median's -0.8).

### 2. Reweighted coefficients in reference.json

Original coefficients: median=-1.0, solved=0.5, p90=-0.4
New coefficients: median=-0.8, solved=0.4, mean=-0.3, p90=-0.7

Rationale:
- p90 is now the strongest anti-shortcut signal (coefficient -0.7) — a method that optimized for median on easy instances while leaving hard instances unsolved will be penalized heavily by p90
- median remains primary (-0.8) but no longer dominates
- mean provides triangulation (-0.3)
- solved count reduced slightly (0.4) since it saturates at 100

### 3. Added descriptions to all metrics

All four metrics in `reference.json` now have one-sentence descriptions explaining what they measure and why they belong. This helps future agents understand the anti-shortcut intent.

## Open concerns for runner iteration

1. **Metric saturation**: `instances_solved` will likely saturate at 100/50 for any legitimate solver. The anti-shortcut signal comes primarily from `p90_runtime_s` and secondarily from `median_runtime_s` and `mean_runtime_s`. If the solver is so fast it times out rarely, all runtime metrics may also compress, leaving `instances_solved` as the only differentiating metric. This is a characteristic of the problem, not a design flaw.

2. **Seed stability**: The eval uses a fixed seed schedule (`seed = args.seed + 1000 * n + instance_id`) to generate instances. The train/test split uses instance ID parity, not seeds. If the seed schedule changes, the eval would use different instances. The constraint is documented in `scoring/CONSTRAINTS.md`.

3. **Runtime measurement precision**: At sub-second median runtimes, measurement noise may exceed signal. Consider increasing the benchmark scale (more instances, larger n) if differentiation matters.

## Summary

The first pass was solid. Main improvement is metric triangulation: adding `mean_runtime_s` and reweighting coefficients so p90 is the primary anti-shortcut metric while median remains the primary scientific metric. No structural changes to split or scripts.
