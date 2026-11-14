# Evaluation

## Scored Experiments

| Experiment | Instances | Sizes | Weight |
|---|---|---|---|
| `qrandomparity_ladder` | 136 (8 per size) | n = 10, 14, 18, 22, 26, 32, 40, 50, 64, 80, 100, 128, 160, 256, 400, 640, 1000 | 0.6 |
| `mcn_ladder` | 48 (6 per size) | 16, 24, 32, 40, 48, 56, 64, 72 nodes | 0.4 |

Each size holds TRUE and FALSE instances in equal numbers.  The train split
has the same sizes and composition with public seeds and answers.

## Metric

`instances_solved` (higher is better), per experiment: the number of
instances whose TRUE/FALSE decision is correct and was reached within the
budget.
- Any wrong decision, anywhere, fails the run: every experiment then scores 0.
- A missing or invalid solver manifest also scores 0 everywhere.
- `UNKNOWN`, no answer, a crash, exceeding the budget or the wall-clock
  watchdog leaves the instance unsolved (an answer left by a process that was
  stopped is ignored).
- After two consecutive sizes with no solved instance, the remaining larger
  sizes of that ladder count as unsolved without being run.

## Protocol

The evaluator runs the solvers itself; nothing a solver reports besides the
decision is read.
1. A solver is a directory with `solver.json`:
   `{"name": "...", "command": ["python3", "path/solve.py"]}`.  The evaluators
   score `method/`, `baseline/` and every directory under `methods/`.
2. For each instance the evaluator calls `command + [instance.qlp, answer.json]`
   from the workspace root; the solver writes
   `{"answer": "TRUE" | "FALSE" | "UNKNOWN"}`.
3. **Budget: 6 x 10^10 user-space instructions per instance**, counted by a
   hardware performance counter over the solver's whole process tree
   (threads, child processes and detached descendants alike; Python start-up
   and imports count).  The tree is stopped as soon as it passes the budget.
   The count does not depend on the speed or load of the machine: the same
   solver gets the same result on any node.  For orientation, the reference
   solver runs about 5-6 x 10^9 instructions per CPU second, so the budget is
   roughly 10 s of its CPU time.  A wall-clock watchdog (90 s) only stops
   solvers that wait instead of computing.
4. The solver runs in a sandbox: it can read the workspace (except
   `eval/test/`) and the system, but can write only inside its private
   working directory (`TMPDIR`, also `HOME`), which is deleted after each
   instance; network sockets, System V IPC, message queues and keyrings are
   unavailable, and the performance-counter interface is closed.  Nothing
   carries over from one instance to the next.  Instances of a size are run
   in a random order, one at a time per solver.
5. The solver's environment is fixed by the evaluator (`PYTHONHASHSEED=0`,
   one BLAS/OpenMP thread, `QIP_INSTRUCTION_BUDGET` and `QIP_WALL_LIMIT_S` for
   information).  Multi-threading is allowed but every thread's instructions
   count.
6. `bash scripts/evaluate_train.sh` scores the public train split
   (`scoring/scores_train.json`); `bash scripts/evaluate_test.sh` scores the
   hidden test (`scoring/scores_test.json`).  Both take no arguments.

## Interpretation

Results are reproducible: an unchanged rerun of the reference solver, also on
a different compute node, decided exactly the same instances (instruction
counts differ by about 0.04 % in the median).  Changing only the internal
random seeds of the reference's sub-solvers moved its counts by up to 3
instances per ladder; treat differences of that size as noise.
