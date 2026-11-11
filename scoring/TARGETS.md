# Evaluation Targets

Scored targets (hidden test: `bash scripts/evaluate_test.sh` ->
`scoring/scores_test.json`; train: `bash scripts/evaluate_train.sh` ->
`scoring/scores_train.json`; `scoring/scores.json` is the train protocol).

| Experiment | Metric | Direction | Weight | Reference (test) | Baseline (test) | Bound |
|---|---|---|---|---:|---:|---:|
| `qrandomparity_ladder` | `instances_solved` | higher | 0.6 | 79 | 17 | 136 |
| `mcn_ladder` | `instances_solved` | higher | 0.4 | 56 | 38 | 68 |

Benefit and constraint in one number: an instance counts only if its decision
is correct and was reached within the 10 s CPU budget, and any wrong decision
sets every metric to 0 (the correctness constraint the paper's solver
satisfies by construction).  The budget is a constraint too: the evaluator
measures CPU time of the whole process tree itself.

Reference context (not scored on this scale, kept in `scoring/reference.json`
under `_paper_reported`): paper Table 1 median runtimes for n = 100..1000,
Figure 2 comparison for n = 10..26, MCN solved counts (EQuIPS 465, Yasol 431,
MCN_CR 475) and Appendix A.1.3 (initial move ablation).
