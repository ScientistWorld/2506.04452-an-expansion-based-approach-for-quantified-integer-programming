This folder contains the scoring audit and all nineteen executed variants. The main report is [REDTEAM.md](../REDTEAM.md). `results_table.md` and `summary.json` summarize actual hidden-test output, seed spreads, and illustrative normalized audit ranks. The ranking service's implementation and future attempt population are unavailable; raw metrics and direction-independent dominance are the primary evidence.

Run a single case in the packaged compute environment, for example:

```bash
bash redteam/shortcut_constant_sat/run.sh
```

Every case first prepares its persistent JSON report under `outputs/redteam_active`, ends the producer process, then runs the original `bash scripts/evaluate_test.sh` with no arguments. The next case replaces only the preceding audit report directory. This matches the gym's evaluation boundary: no producer process survives, and the hidden test consumes only files. Existing unrelated reports in the evaluator's discovery roots are not removed. As with the original audit, use an otherwise clean discovery area to reproduce these exact results.

Each case folder contains:

- `method.py` and `run.sh`: the runnable variant or explicitly labeled shortcut.
- `raw.json`, optional companion reports, and `installation.json`: what was persisted before evaluation. For `shortcut_unscanned_results`, the failed candidate is `shortcut_unscanned_candidate.json` and `raw.json` is the surviving baseline.
- `method.log`, `hidden_test.log`, `test_exit.txt`: observed execution evidence.
- `scores_test.json`: an exact copy of the score file after a successful hidden test. Failed probes instead preserve `stale_scores_after_failure.json`, which is not counted as their score.
- For measured variants, `provenance.json` records the data seed, actual solver budget, and reporting timeout. Cache construction has its own explicit provenance file.

Some report shortcuts depend on measured reference or enumeration results. Their `run.sh` runs those dependencies only if the saved raw output is absent. These dependencies use only the future agent's visible `method/`, `baseline/` and `data/`. Constants and baseline cache replay do not require the method source. No shortcut reads hidden IDs, hidden answers, frozen target scores, paper contents, or hidden evaluator modules. All emit the full public seed batch.

`job.sh` bundles all cases into one CPU job, skips cases with saved exit statuses, and restores the original test evaluator, test script, score file and job runner afterwards. To repeat the solver computations, first archive the case outputs and remove the corresponding `test_exit.txt` files. Actual solver work belongs on compute jobs, not the login node. The audit ran with no package installation, no environment interception, and no GPU.

`analyze.py` is lightweight report analysis, separate from any method. It reads saved hidden outputs and the initial coefficient/score snapshots. It can be rerun without the solver packages:

```bash
python3 redteam/analyze.py > redteam/analysis.log
```

Reference data seeds are fixed at `42 + 1000*n + instance_id`; solver seeds vary across the three reference methods. The honest normalization cohort is the three references, better backend, weaker budget, relaxation ablation, enumeration, plus the frozen test reference. A second cohort includes all successful audit cases. Neither cohort is presented as the unknown future leaderboard population.

`initial/` preserves the audit's original base commit, relevant source hashes, score/reference snapshots, runner, scheduler state and dirty-worktree listing. `job_artifacts/` archives the completed job's scheduler logs. Preexisting unrelated workspace modifications were preserved when restoring the gym. The required final `action.yaml` scheduler signal is separate from the scientific artifacts.
