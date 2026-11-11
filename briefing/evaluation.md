# Evaluation

## Scored Experiments

| Experiment | Instances | Sizes | Weight |
|---|---|---|---|
| `qrandomparity_ladder` | 136 (8 per size) | n = 10, 14, 18, 22, 26, 32, 40, 50, 64, 80, 100, 128, 160, 256, 400, 640, 1000 | 0.6 |
| `mcn_ladder` | 68 (4 per size) | 8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 36, 40, 48, 56, 64, 80, 96 nodes | 0.4 |

Each size holds TRUE and FALSE instances in equal numbers.  The train split
has the same sizes and composition with public seeds and answers.

## Metric

`instances_solved` (higher is better), per experiment: the number of
instances whose TRUE/FALSE decision is correct and was reached within the CPU
budget.
- Any wrong decision, anywhere, fails the run: every experiment then scores 0.
- A missing or invalid solver manifest also scores 0 everywhere.
- `UNKNOWN`, no answer, a crash, or exceeding the budget leaves the instance
  unsolved.
- After two consecutive sizes with no solved instance, the remaining larger
  sizes of that ladder count as unsolved without being run.

## Protocol

The evaluator runs the solvers itself; nothing a solver reports besides the
decision is read.
1. A solver is a directory with `solver.json`:
   `{"name": "...", "command": ["python3", "path/solve.py"]}`.  The evaluators
   score `method/`, `baseline/` and every directory under `methods/`.
2. For each instance the evaluator calls `command + [instance.qlp, answer.json]`
   from the workspace root with `QIP_CPU_BUDGET_S=10` in the environment; the
   solver writes `{"answer": "TRUE" | "FALSE" | "UNKNOWN"}`.
3. CPU time (user + system) of the whole process tree is measured by the
   evaluator, including detached or orphaned descendants, which are killed and
   counted when the solver exits.  Budget: 10 s CPU per instance; a
   wall-clock watchdog kills the tree after 25 s.  Python start-up counts.
4. `bash scripts/evaluate_train.sh` scores the public train split
   (`scoring/scores_train.json`); `bash scripts/evaluate_test.sh` scores the
   hidden test (`scoring/scores_test.json`).  Both take no arguments.

## Interpretation

Counts depend on the CPU speed of the machine: the reference solver rescored
on different compute nodes varied by about 7 parity and 3 MCN instances.
Compare methods on the same machine where possible, and treat differences of
that size as noise.
