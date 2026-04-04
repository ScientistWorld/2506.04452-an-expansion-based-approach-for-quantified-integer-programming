# Evaluation Targets

## Primary: qrandomparity_performance
QRandomParity benchmark — median runtime and instances solved.
- **Metric**: `median_runtime_s` (lower is better)
- **Constraint metric**: `instances_solved_100` (must be close to 100 — a solver that times out frequently is not useful)

## Primary: mcn_instances_solved
Multilevel Critical Node problem — number of instances solved within 2-hour timeout.
- **Metric**: `instances_solved` (higher is better)

## Ablation: qip_encoding_vs_qbf_encoding
EQuIPS on QIP linear encoding vs clausal encoding — demonstrates advantage of linear constraints.
- **Metric**: `n200_instances_solved` (EQuIPS solves n=200 in QIP encoding, fails in clausal)
