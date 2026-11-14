# Hardening report (final iteration, second pass)

Paper: *An Expansion-Based Approach for Quantified Integer Programming*
(EQuIPS, CEGAR with expansion). The gym scores QIP **decision solvers**. The
hidden evaluator runs each solver on hidden instances, checks every TRUE/FALSE
decision against ground truth that only `eval/test/` holds, and counts
correctly decided instances along two size ladders from the paper's
experiments:
- QRandomParity (Section 5.1): 136 instances, n = 10…1000;
- the multilevel critical node problem, MCN (Section 5.2): 48 instances,
  16…72 nodes.

This pass fixes the two weaknesses `REVIEW.md` listed for the previous
hardening:
1. solved counts depended on the node's CPU speed;
2. the MCN signal was weak, and an MCN-specific brute force outranked the
   reference on MCN.

It also closes a major shortcut the red team had not found.

**Where the numbers come from.**
- Final results: `hardening/results_table.md` and `hardening/summary.json`,
  logs in `hardening/logs/`.
- Jobs: `ba059b91-381`, `8d8f898b-f06` and `5db58297-5ce`.
- The MCN ladder went through two versions. The intermediate one is kept in
  `hardening/mcn_v3_job1/`.
- The previous pass (CPU-time budget) is kept in `hardening/cpu_budget_round/`.

**How the ranks are computed.** Ranks are illustrative:
`Σ_e w_e·|c|·(value − reference)/σ_e`, where σ is the population standard
deviation over the honest cohort. The cohort is the frozen reference, the
reference reruns and seeds, the better and weaker variants, and the baseline.
Final σ is 22.9 for parity and 9.3 for MCN.

## 0. What changed

**The budget is counted, not timed.** It is 6×10¹⁰ user-space instructions per
instance, over the solver's whole process tree. `eval/test/sandbox.py` (and a
copy in `eval/train/`) attaches a hardware instruction counter
(`PERF_COUNT_HW_INSTRUCTIONS`, `inherit`, `enable_on_exec`) to the solver
before it starts.
- The counter covers every thread, child and detached descendant.
- The tree is killed as soon as the count passes the budget.
- A wall-clock watchdog (90 s) only stops solvers that sleep.
- The budget equals about 10 s of the reference's CPU. It averaged 5.1–6.3×10⁹
  instructions per CPU-second on the job nodes, close to the old 10 s budget.

**The solver runs in a sandbox.** It applies to both evaluators:
- seccomp refuses `perf_event_open`, the perf `prctl`s, System V IPC, POSIX
  message queues, keyrings, non-Unix sockets and foreign syscall ABIs;
- Landlock makes `eval/test/` unreadable, makes everything else read-only, and
  leaves only a private per-instance working directory writable (deleted
  afterwards); on Landlock ABI 6 it also blocks signals and abstract sockets
  to processes outside the sandbox;
- the launcher is a non-dumpable child subreaper;
- ASLR is off;
- the solver's environment is fixed: `PYTHONHASHSEED=0` and one BLAS thread.

**Other evaluator changes.**
- Instances of a size run in a fresh random order every evaluation.
- Each solver runs one instance at a time, and solvers are evaluated
  concurrently.
- The details file records every instance's instruction count and
  correctness, but no instance identity or answer.

**The MCN ladder was rebuilt.** Budgets are now:

| Budget | Range |
|---|---|
| Vaccination | 1–3 |
| Attack | 1–2 |
| Protection | 2–3 |

Graphs have 16–72 nodes, 6 per size, 3 TRUE and 3 FALSE.
- **Ground truth.** The optimum of each graph is exact. The 96 test and train
  graphs were certified as follows:
  - the bitmask minimax solved 81 graphs within its cap (60–180 s);
  - on 57 of those, a CEGAR solver confirmed the decisions at the optimum and
    one above it and never disagreed; on 8 it did not finish, and the other 16
    lie outside the cross-check range (20–56 nodes);
  - a CEGAR binary search, run to completion, certified the remaining 15.
- **Bias.** Graphs that neither tool certified were replaced by a fresh seed
  (up to 6 per slot). That biases slightly toward graphs certifiable with
  roughly 30× the solvers' budget.
- **Why these ranges.**
  - The attack budget drives the number of scenarios for every exact method,
    including the ground-truth solver.
  - With attack budget 3, ground truth could not be certified beyond 48 nodes.
  - The protection budget is what makes enumeration blow up.
  - All values lie in the paper's range of budget configurations.

**The reference method is unchanged as an algorithm.**
- HiGHS now runs single-threaded, which is the paper's setting. Its thread
  pool otherwise depends on the node's core count.
- `method/solve.py` no longer times itself, because the evaluator enforces the
  budget. This keeps runs deterministic.
- The same two changes apply to the baseline.

**Fixes to the harness.**
- `scripts/run.sh` hung on a bare `wait` that also waited on its own `tee`.
- The sandboxed smoke test was fixed.

## 1. Do better results score higher?

Yes on the combined rank and on parity. On MCN alone, no variant I found beats
the reference by more than the solver-seed noise.

| Variant | Before (previous pass: parity / MCN, rank) | After (parity / MCN) | Paired vs frozen reference (parity, MCN: only variant / only reference) | Rank after |
|---|---|---|---|---:|
| Frozen reference | 79 / 56 | **82 / 32** | — | 0 |
| Unchanged rerun | 83 / 53 and 84 / 55 (other nodes) | 82 / 32 | 0/0, 0/0 | 0.000 |
| Reference, solver seed 1 | 83 / 53 (−0.001) | 85 / 35 | 5/2, 4/1 | +0.207 |
| Reference, solver seed 2 | 84 / 55 (+0.082) | 85 / 31 | 3/0, 1/2 | +0.036 |
| Better: CP-SAT + sound mod-2 presolve | 114 / 61 (+0.941) | **116 / 35** | 35/1, 6/3 | **+1.018** |
| Better: CP-SAT for every subproblem | 91 / 62 (+0.453) | 92 / 35 | 11/1, 6/3 | +0.390 |
| Better?: CP-SAT + minimal responses (new) | — | 92 / 35 | 11/1, 6/3 | +0.390 |
| Better?: minimal responses, HiGHS (new) | — | 82 / 33 | 0/0, 2/1 | +0.043 |
| Weaker: HiGHS for every subproblem | 82 / 45 (−0.266) | 82 / 21 | 0/0, 1/12 | −0.471 |
| Weaker: gives up after 3 s of CPU | 57 / 20 (−1.588, "tenth budget") | 67 / 5 | 0/15, 0/12 | −1.548 |
| Exhaustive-enumeration baseline | 17 / 38 (−1.943) | 17 / 17 | 0/35, 2/17 | −2.342 |

- **Parity.** The mod-2 variant gains 34 (paired 35 vs 1). The reference's
  seed reruns move it by 0 to +3. The CP-SAT variant gains 10 (paired 11 vs 1).
- **MCN.**
  - The CP-SAT variants gain 3 (paired 6 vs 3).
  - Solver seeds alone move the reference by −1 to +3 (paired 4/1 and 1/2).
  - **This is within noise.** The variant has gained in every MCN ladder
    measured (+5/+6, +4, +3), but no single one shows a gain beyond noise.
  - I tried two further candidates: "minimal responses", where the reply to a
    complete opponent move minimises its variables. It was neutral: +0 on top
    of CP-SAT, whose default search already returns near-minimal answers, and
    +1 with HiGHS.
  - See section 7.
- **Weaker variants rank clearly below the reference.** On MCN, HiGHS-only
  loses 12 instances and gains 1.
- **The paper's claim holds in its direction.** EQuIPS beats the enumeration
  the method exists to avoid: 82 vs 17 on parity and 32 vs 17 on MCN.

## 2. REVIEW items

**Same method, same score everywhere (CPU-speed dependence).**
- Previously an unchanged rerun on another node scored 84 vs the stored 79.
- Now an unchanged rerun decided exactly the same 184 instances as the frozen
  run (0 flips). Its parity levels came from the first job's AMD node, and the
  frozen run's mostly from an Intel node (next point).
- The frozen reference was also rerun end to end in a later job.
  - Its parity levels n ≥ 18 ran on an Intel Xeon Gold 6242R node; the first
    frozen run had used an AMD EPYC 9654 node.
  - All 136 parity instances agree: 0 changed outcomes, 82 = 82.
  - Instruction counts differ by a median of 4e-4 (max 0.36 %) across the CPU
    vendors, and by 5e-7 between two AMD nodes.
- The enumeration baseline also agrees on all 56 instances it ran: 17 = 17.

**MCN brute force no longer outranks the reference.**
- The MCN-specific brute force (`decoder_mcn`: rebuilds the graph from the
  rows, exact minimax over budget-sized choices) scored 60 vs the reference's
  56 before.
- It now scores **20 vs 32** (rank −2.659). It solves everything up to 24
  nodes, then collapses: 3/6 at 32 nodes, 2/6 at 40, 1/6 at 48–64 and 0/6 at
  72. The reference solves 3–4 of 6 at every size from 24 to 72.
- On the intermediate ladder (budgets 1–3 for all three players, up to 48
  nodes) it still won, 45 vs 41. That is why the attack budget was limited and
  the protection budget raised (`hardening/mcn_v3_job1/`).
- The other half of this item, a better solver separating beyond noise on MCN,
  is not achieved (section 1).

## 3. Major shortcuts: fix, and score before and after

"Before" for the new probes means the same evaluator without this pass's
isolation (`eval/test/audit/eval_variant.py --legacy`: no seccomp, no
Landlock, fixed instance order). It was run on the three largest sizes of each
ladder, where the reference solves 4 parity and 11 MCN instances.

| Shortcut | Before | Fix | After |
|---|---|---|---|
| **Call-order counter** (new; the previous evaluator was open to it). Keeps a per-size call count in a workspace file and answers from the public per-level answer pattern (parity F,T,T,T,F,F,T,F; MCN T,T,T,F,F,F), without solving. | **24/24 parity, 18/18 MCN** on those levels (reference 4 / 11). On the full ladders it would be perfect. | Fresh random order per evaluation. Solver writes only in a private per-instance directory, deleted afterwards. No IPC, keyrings or sockets. | 0 / 0, rank −3.515 |
| **Reading the hidden table** (`read_hidden`: reads `eval/test/instances.json`, rebuilds the instances with the hidden generator, answers by matching) | **24/24, 18/18** (left to the grader by the previous pass) | Landlock: `eval/test/` unreadable for the solver, in train and test alike | 0 / 0 |
| CPU-speed dependence (same solver, other node) | 79 vs 84 parity, 53–56 MCN | counted instruction budget | identical across nodes and CPU vendors (section 2) |
| Hiding work from the counter: `perf_disable` (`prctl(PR_TASK_PERF_EVENTS_DISABLE)`, then the reference) | not exploitable: the `prctl` only reaches counters the process owns, not the launcher's | additionally refused by seccomp | 4 / 10 (reference 4 / 11) |
| Detached child doing the work | its CPU was counted only after the subreaper fix (last pass) | instructions inherited by every descendant; subreaper kills and counts | 4 / 10 (reference 4 / 11) |
| Portfolio of 5 configurations in detached processes | 18 vs reference 15 (old CPU accounting) | all instructions of all processes count | 0 / 2 (reference 4 / 11) |
| MCN-specific brute force | 60 vs 56 on MCN | MCN ladder rebuilt (section 0) | 20 vs 32 |
| Constant / random / forged answers, guessing TRUE or FALSE on timeout | already failed (wrong decision zeroes the run) | unchanged | fail: 0 / 0 |
| Train-table lookup, crash, empty slot | 0 | unchanged | 0 / 0 |

## 4. Shortcuts left, and why

**Combined family decoders** (`decoder_combined_strict`).
- It combines an XOR decoder on parity with the MCN brute force on MCN. It
  scores 102 / 20, rank **+0.009**.
- That is a tie with the reference, below both of the reference's own
  seed reruns (+0.036, +0.207). The previous pass had it at +0.640.
- Its parity half (`decoder_gf2_strict`, 102 / 0, rank −0.847) has two steps:
  - expand the single universal bit;
  - run Gaussian elimination over GF(2) on XOR-shaped rows, abstaining on any
    cardinality row.
- That is sound XOR reasoning, the capability the paper credits for QFUN_cms.
  The general version inside the QIP solver (the mod-2 presolve variant)
  scores 116 and ranks +1.018.
- Its MCN half recognises the critical-node model in the rows and rebuilds the
  graph. That is a model-specific decoder for the grader to flag.
- Neither half pays alone. Together they only tie.

**Isolation gaps the sandbox does not cover.**
- Work done on other machines or accelerators is not counted. Network sockets
  are refused, and the hidden test runs on a CPU job.
- Covert channels through `/proc` (for example process names) between solvers
  evaluated concurrently. Instances of one solver never run concurrently, so
  this needs two cooperating solver directories.
- On a kernel without hardware counters the launcher falls back to CPU time ×
  5×10⁹ per second, and logs it (`mode: "cpu"` in details). Results would
  then depend on the node again. Every job node in this pass had the counter.
- On a kernel without Landlock (ABI < 1) the read and write restrictions are
  absent. Every job node had ABI 6.

## 5. Reference score before and after

| | Previous pass (CPU budget) | This pass (instruction budget) |
|---|---|---|
| Frozen reference, test | 79 / 136 parity, 56 / 68 MCN | **82 / 136 parity, 32 / 48 MCN** |
| Frozen reference, train | 80 / 136, 43 / 68 | 82 / 136, 34 / 48 |
| Baseline, test | 17 / 136, 38 / 68 | 17 / 136, 17 / 48 |

**Which runs produced the score files.**
- `scoring/scores_test.json` comes from the end-to-end run of `method/` and
  `baseline/` with the final code (job `8d8f898b-f06`).
- `scoring/scores_train.json` and `scoring/scores.json` come from that job's
  train run.
- The paper's reported results in `scoring/reference.json`
  (`_paper_reported`) are unchanged. Only the scale note mentions the new
  budget.

**Train and test now agree:** 82 / 82 on parity and 34 / 32 on MCN. Before,
MCN was 43 / 56.

## 6. Headroom

| Ladder | Reference | Best variant | Room above the reference |
|---|---|---|---|
| Parity | 82 / 136 | 116 | the best variant still misses 20 instances, all at n ≥ 128 |
| MCN | 32 / 48 | 35 | instances the reference misses, solved by other methods (below) |

**MCN details.**
- The brute force solves 5 instances that the reference misses.
- Ground truth is certified on every graph up to 72 nodes by exact solvers with
  roughly 30× the budget.
- No metric is at its bound, and no simple variant reaches the bound.
- The problem-agnostic brute force, the enumeration baseline, sits far below
  on both ladders (rank −2.342).

## 7. Not fixed / limitations, stated plainly

- **MCN does not separate a better solver beyond noise.**
  - The best MCN variants gain +3 of 48 against a seed spread of −1…+3.
  - The REVIEW asked to scale the ladder until a better solver separates. I
    rebuilt and scaled it twice, to 72 nodes with harder budgets for
    enumeration.
  - Ground truth could not be certified at 80 nodes within the caps (200 s per
    decision, 6 seeds per slot).
  - No MCN-specific improvement I tried moved the frontier more than solver
    seeds do. A future agent has to find a genuinely better MCN strategy. The
    combined rank does separate: +0.39 and +1.02 against seed reruns at +0.04
    and +0.21.
- **The MCN budget ranges are a design choice.** They are vaccination 1–3,
  attack 1–2 and protection 2–3. They keep ground truth certifiable at larger
  graphs and make enumeration of the players' choices impractical. With
  attack budget 3 the reference was weaker than the MCN brute force, which is
  consistent with the paper's own MCN ranking (EQuIPS second to MCN_CR).
- **Counts can differ slightly across CPU vendors.** Instruction counts differ
  by about 0.04 % between Intel and AMD, through library code paths chosen per
  CPU. An instance within 0.4 % of the budget could flip. None did in 120
  cross-vendor comparisons.
- **The audit reused parity levels across jobs.** Audit cases took their
  parity levels from the first job (same code, same instances). Only their MCN
  levels ran again after the ladder changed. The frozen reference and the
  train split were rerun end to end.
- **Neither the paper's backend nor its scale is reproduced.** The paper used
  Gurobi with 1800 s per instance. This gym uses HiGHS/CP-SAT and about 10 s of
  CPU-equivalent per instance.

## 8. Weights

Weights are unchanged: parity 0.6, MCN 0.4, coefficient 1 each.
QRandomParity carries the paper's central claims (Section 5.1, Table 1,
Figure 2, encoding comparison). MCN is the secondary optimisation showcase.
MCN is not given more weight, because it separates honest improvements less
sharply than parity.
