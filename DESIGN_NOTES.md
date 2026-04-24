# Design Notes — Iteration 6 (designer_stage_3)

## What the shipped split measures

The active gym target is the fixed 100-instance `qrandomparity_n10` batch.
Both slices score the same scientific quantity:

- `median_runtime_s`: typical-case runtime on solved instances
- `instances_solved`: correctness / decisiveness constraint
- `mean_runtime_s`: outlier-sensitive runtime triangulation
- `p90_runtime_s`: tail-latency anti-shortcut metric

The train/test split is a disjoint 50/50 partition over fixed instance IDs.
A real improvement should lower runtime on both slices while preserving solved
coverage. A train-only shortcut should show up as a train/test gap in the tail
metrics or solved count.

## What changed after the real run

### 1. Reference contract aligned to the active scored target

The previous design pass still left `scoring/reference.json` on paper-scale
`qrandomparity_n100` / `qrandomparity_n200` entries even though the shipped gym,
evaluation scripts, and score files all target `qrandomparity_n10`. That made
the completed train/test score files inconsistent with the validator contract.

`reference.json` now contains the actual scored experiment:

- `qrandomparity_n10`
- methods: `equips` and `search_enumeration`
- the four runtime / coverage metrics computed by `eval/train/` and `eval/test/`

No paper-agreement metrics were introduced, and no score values were hand-filled
into the reference methods block.

### 2. Real-run results recorded

The first full containerized run produced non-saturated, method-differentiating
scores on both slices:

- Train, `equips`: solved `50/50`, median `0.247814`, mean `0.309736`, p90 `0.46106`
- Test, `equips`: solved `49/50`, median `0.257841`, mean `0.346785`, p90 `0.510841`
- Train, `search_enumeration`: solved `50/50`, median `0.692309`, mean `0.686238`, p90 `0.709138`
- Test, `search_enumeration`: solved `50/50`, median `0.690046`, mean `0.687464`, p90 `0.702065`

These numbers match the intended interpretation:

- the proposed method is materially faster than the exact-search baseline
- the train/test gap is small but nonzero for `equips`
- the split is not byte-identical across slices
- no metric is pegged at a ceiling or floor across all methods

## Caveat from the real run

One `equips` test instance (`instance 97`) was emitted by the frozen method as
`TIMEOUT` despite a logged runtime of `0.1296s`, which is well below the nominal
`5.0s` timeout. The evaluator correctly treated that status as unsolved because
the method output is the contract. This looks like a method-side status issue,
not an evaluation bug, so it was documented rather than scored around.

## Sign-off judgment

The split is now usable as a ResearchGym anti-shortcut harness:

- train and test score the same scientific quantity on different fixed slices
- both methods are discovered and scored without hardcoded single-method routing
- the baseline is slower on both slices, so future agents have a real target
- the score files now match the reference experiment / metric contract

I did not modify the frozen method, checkpoints, or hyperparameters.
