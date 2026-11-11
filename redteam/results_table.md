Audit ranks below are relative to the frozen test reference (rank 0). They use population SD over the seven honest cases plus that reference. Raw metrics are the actual hidden-test output; the live future cohort is unknown.

| Case | Exit | Median s | Solved / 50 | Mean s | p90 s | Audit rank (honest scales) |
|---|---:|---:|---:|---:|---:|---:|
| ablation_no_relaxation | 0 | 0.309028 | 49 | 0.364788 | 0.587985 | -0.046148 |
| better_backend | 0 | 0.044026 | 50 | 0.040753 | 0.058334 | 0.283911 |
| exhaustive_baseline | 0 | 1.02735 | 50 | 1.160762 | 1.455173 | -0.680055 |
| reference_seed0 | 0 | 0.329213 | 49 | 0.34575 | 0.526315 | -0.030627 |
| reference_seed1 | 0 | 0.288866 | 50 | 0.334748 | 0.55703 | -0.007590 |
| reference_seed2 | 0 | 0.310838 | 50 | 0.35703 | 0.573225 | -0.023837 |
| shortcut_baseline_replacement | 0 | 0.329213 | 49 | 0.34575 | 0.526315 | -0.030627 |
| shortcut_cache_replay | 0 | 1.1e-05 | 50 | 1.1e-05 | 1.1e-05 | 0.324405 |
| shortcut_constant_sat | 0 | 1e-06 | 50 | 1e-06 | 2e-06 | 0.324413 |
| shortcut_constant_unsat | 0 | 1e-06 | 50 | 1e-06 | 1e-06 | 0.324414 |
| shortcut_empty_results | 0 | missing | missing | missing | missing | 0.000000 |
| shortcut_forged_aggregates | 0 | 0.329213 | 49 | 0.34575 | 0.526315 | -0.030627 |
| shortcut_missing_records | 1 | missing | missing | missing | missing | failed |
| shortcut_negative_times | 0 | -1.0 | 50 | -1.0 | -1.0 | 1.148078 |
| shortcut_null_times | 1 | missing | missing | missing | missing | failed |
| shortcut_reported_zero | 0 | 0.0 | 49 | 0.0 | 0.0 | 0.307342 |
| shortcut_timeout_zero | 0 | 0.0 | 0 | 0.0 | 0.0 | -0.529205 |
| shortcut_unscanned_results | 0 | missing | missing | missing | missing | 0.000000 |
| weaker_budget | 0 | 5.0 | 0 | 5.0 | 5.0 | -4.647521 |
