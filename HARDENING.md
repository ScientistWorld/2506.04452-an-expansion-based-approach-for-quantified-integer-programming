# Hardening report (final iteration)

Paper: *An Expansion-Based Approach for Quantified Integer Programming*
(EQuIPS, CEGAR with expansion). The gym scores QIP **decision solvers**. The
hidden evaluator runs each solver on hidden instances with a 10 s CPU budget
per instance, checks every TRUE/FALSE decision against ground truth that only
`eval/test/` holds, and counts correctly decided instances along two size
ladders taken from the paper's experiments: QRandomParity (Section 5.1) and the
multilevel critical node problem, MCN (Section 5.2).

All "after" numbers below come from job `561eb169-77f`: the frozen reference,
the train split, and the new MCN levels for every audit case. Audit levels the
earlier job `5663aef5-fe0` had already finished on the same instances were
reused through the evaluator's per-level checkpoint, so only the new MCN levels
(80 and 96 nodes) ran again. Full tables are in `hardening/results_table.md`
and `hardening/summary.json`. The intermediate states are kept in
`hardening/ladder_v1/` (the ladder gym left by the previous run of this
iteration, job `e8701c6e-22e`) and `hardening/job1/`.

Ranks are illustrative. Each rank is `Σ_e w_e·|c|·(value − reference)/σ_e`,
where σ is the population standard deviation over the honest cohort: reference
reruns, better and weaker variants, and the baseline. Final σ is 26.6 for
parity and 13.2 for MCN.

## 1. Do better results score higher now?

Yes. A wrong decision now zeroes every metric, CPU time is measured by the
evaluator, and both ladders have room above the reference. The one remaining
weakness is the MCN signal, which is about the size of the node-to-node noise.

| Variant | Original gym (REDTEAM, n10 runtimes) | Ladder v1 (parity/72, MCN/48) | Final (parity/136, MCN/68) | Final rank |
|---|---|---|---|---:|
| Frozen reference (EQuIPS) | median 0.258 s, 49/50 | 53 / 45 | **79 / 56** | 0 |
| Reference reruns (solver seeds 1, 2) | 49–50/50, rank −0.031…−0.008 | 53 / 45, 54 / 46 | 83 / 53, 84 / 55 | −0.001, +0.082 |
| Better: CP-SAT + sound mod-2 presolve | — | 71 / 47 (+0.864) | **114 / 61** | **+0.941** |
| Better: CP-SAT for every subproblem | rank +0.284 (below 3 shortcuts) | 57 / 48 (+0.405) | 91 / 62 | +0.453 |
| Weaker: HiGHS for every subproblem | — | 53 / 42 | 82 / 45 | −0.266 |
| Weaker: 1/10 of the budget | rank −4.65 (1 ms budget) | 41 / 33 | 57 / 20 | −1.588 |
| Exhaustive-enumeration baseline | 50/50 in 1.03 s (solved the whole test) | 13 / 35 | 17 / 38 | −1.943 |

- **Parity.** The better variant gains +35 over the frozen reference and +28
  over the best reference rerun. That is far beyond the reruns' spread of 79–86.
- **MCN.** Both better variants gain +5 or +6 over the frozen reference (61–62
  vs 56). Reference reruns on different nodes spread over 53–56, so this gain
  is only slightly above the noise; see "Not fixed".
- **Weaker variants rank below the reference.** HiGHS-only loses 11 MCN
  instances and stays within noise on parity, because the reference already
  uses HiGHS for the existential subproblems. The tenth-budget variant loses on
  both ladders.
- **The paper's claim holds in its direction.** EQuIPS beats the enumeration
  baseline the method exists to avoid by 79 vs 17 on parity and 56 vs 38 on MCN.

## 2. Major shortcuts: fix, and score before and after

Shortcuts from REDTEAM.md were measured on the original runtime gym. The
previous run of this iteration (ladder v1) replaced that gym with
evaluator-run solvers and ground-truth checks. All of them were re-run through
the final hidden test.

| Shortcut | Before | Fix | After (final hidden test) |
|---|---|---|---|
| Constant SAT answer | +0.324, above the reference with all 50 answers wrong | evaluator checks every decision against hidden ground truth; a wrong one zeroes all metrics; TRUE and FALSE are balanced per size | fails at size 10; 0 / 0 (worst) |
| Constant UNSAT answer (the only answer of the old family) | +0.324 | as above, mixed answers | fails at size 10; 0 / 0 |
| Random answer | — | as above | fails at size 10; 0 / 0 |
| Cache replay of public batch | +0.324 | hidden seeds; the test instances never appear in public data | `train_cache` probe: 0 / 0 |
| Reported zero runtimes | +0.307 | the evaluator runs the solver and measures CPU itself; reported runtimes are not read | not applicable; `forged_fields` probe: fails, 0 / 0 |
| Negative runtimes | +1.148 | as above | not applicable |
| Forged aggregate fields | tie | only the `answer` field is read | fails (its answer is wrong); 0 / 0 |
| Empty or missing candidate report | tie (missing values skipped) | `method/` is always scored; a missing manifest scores 0 everywhere | `empty_slot`: failed, 0 / 0 |
| Candidate hidden outside scanned folders | tie | every solver directory on disk is scored (`method/`, `baseline/`, `methods/*`) | — |
| Crash | evaluation aborted | crash leaves instances unsolved | 0 / 0 |
| Guess FALSE when timing out | — | wrong decision zeroes the run | fails at parity n=64; 0 / 0 |
| Guess TRUE when timing out | — | as above | fails at parity n=18; 0 / 0 |
| Baseline replacement | tie | rank compares with fixed numbers in `scoring/reference.json`; baseline score is not used | — |
| Exhaustive enumeration solves the test | 50/50, every test instance inside the limit | ladders up to parity n=1000 and MCN 96 nodes | 17 / 38, rank −1.943 |
| **Parity decoder** (mod-2 consistency taken as integer feasibility) **+ MCN decoder** | ladder v1: 72 / 48, rank **+0.986**, above every honest variant | two parity kinds per size with a cardinality row over variables the parity system pins: mod-2 consistent, integer infeasible for the FALSE one | **fails at size 10** (wrong decision); 0 / 0 |
| Parity decoder alone | ladder v1: 72 / 0 | as above | fails at size 10; 0 / 0 |
| MCN brute force (problem-specific minimax over budget-sized subsets) | ladder v1: 0 / 48, saturating MCN | MCN ladder extended to 96 nodes with certified optima | 0 / 60, rank −1.659; collapses at 96 nodes (0/4); see "Left" |
| **Parallel CPU escape** (5 solver configurations in detached sessions; answers the first decisive result) | **18** vs reference 15 on MCN 40–96: hides CPU from an evaluator that only counts waited children | evaluator becomes a child subreaper; detached and orphaned descendants are killed, reaped and their CPU counted | **0** vs reference 15 (all of its CPU now counts) |
| Single detached child with 2.2× budget | 22 vs reference 22 on MCN 28–64 (job 1) | same fix | 22 vs 22. It never gained: the per-process CPU limit stopped the child at about 11 s |

Two further small fixes: the hidden table now keeps one text digest per size
instead of a per-instance hash, so a solver cannot look up an instance by hash.
Both evaluators also accept an optional per-level checkpoint so that an
interrupted evaluation resumes; it is off unless passed explicitly.

## 3. Shortcuts left, and why

- **MCN-specific brute force: 60/68, against 56 for the reference.**
  - It recognises the critical-node model in the rows, rebuilds the graph and
    runs an exact minimax over budget-sized subsets. That makes it a decoder of
    the generating model, not a QIP solver.
  - It ties the honest better variants (61, 62). Its whole advantage comes from
    sizes up to 64, where it solves everything.
  - It drops to 0/4 at 96 nodes, where the reference still solves 2/4.
  - Scaling further needs certified optima at 112 nodes or more. There the
    exact minimax needed more than 300 s and the CEGAR solver more than 150 s
    for the first graph tried, so the ladder stops at 96.
  - The separate shortcut grader has to catch model-specific decoders. The
    problem-agnostic brute force, the enumeration baseline, sits far below the
    reference (38).
- **XOR-recognising GF(2) decoder** (`decoder_gf2_strict`: Gaussian elimination
  over XOR-encoded rows, abstaining on any cardinality row).
  - It is sound on the rows it answers and gets 102/136 parity; combined with
    the MCN brute force it ranks +0.640.
  - That is above the reference but below the general variant built on the same
    idea, a sound mod-2 presolve inside the solver (114, +0.941).
  - A decoder that also checks cardinality rows against the values the parity
    system pins would reach 136. That is a model-specific decoder again, left to
    the grader.
- **Reading `eval/test/` at solve time.** A solver runs in the same filesystem
  and could read the hidden table. Preventing that needs OS-level sandboxing,
  which the container doesn't provide. Any solver that opens files under
  `eval/test/` is an obvious cheat for the grader.

## 4. Reference score before and after

| | Original gym | Ladder v1 | Final |
|---|---|---|---|
| Frozen reference | median 0.258 s, 49/50 solved (n=10) | 53/72 parity, 45/48 MCN | **79/136 parity, 56/68 MCN** |
| Train split | — | 52/72, 43/48 | 80/136, 43/68 |
| Baseline (test) | median 1.03 s, 50/50 | 13/72, 35/48 | 17/136, 38/68 |

The reproduced method itself (`method/`) is unchanged.
`scoring/scores_test.json` and `scoring/scores_train.json` come from the
reference runs alone (`method/` and `baseline/`, no arguments). The paper's
reported results in `scoring/reference.json` (`_paper_reported`) are
unchanged.

## 5. Headroom check

- **Parity.** The reference sits at 79/136, not at the bound. The best variant
  reaches 114. It still loses instances from n = 128 up and on the FALSE
  cardinality kind at large n.
- **MCN.** The reference sits at 56/68, not at the bound. The best variants
  reach 61–62 and lose instances at 56–96 nodes.
- **No simple variant reaches the bound** on either ladder.
- **What was added this round:**
  - Parity sizes up to n = 1000, the paper's Table 1 range, at 8 instances per
    size.
  - Two cardinality kinds per size.
  - MCN sizes 48–96. Optima were certified by a hidden CEGAR solver, which
    agreed with the exact minimax on 12/12 graphs of 32–40 nodes, and above 64
    nodes by the exact minimax, which agreed with the CEGAR optima on 24/24
    graphs of 48–64 nodes.
- The MCN ladder is the paper's own weak spot: EQuIPS solves 465 MCN instances
  against 475 for MCN_CR.

## 6. Weights

Unchanged: parity 0.6, MCN 0.4, coefficient 1 each. QRandomParity carries the
paper's central claims (Section 5.1, Table 1, Figure 2, the encoding
comparison). MCN is the secondary optimization showcase.

## 7. Not fixed / limitations, stated plainly

- **The MCN gain is about the size of the noise.** The MCN ladder can show a
  +5/+6 gain for a better solver, but reference reruns on different compute
  nodes spread over 53–56. Parity reruns spread over 79–86. The cause is that
  counts under a CPU budget depend on node speed: job `5663aef5-fe0` ran on
  several heterogeneous nodes (40, 96 and 192 cores) because of repeated node
  failures. I did not add CPU-speed calibration.
- **Train and test MCN differ for the reference: 43 on train vs 56 on test.**
  Parity agrees (80 vs 79), and the generator parameters agree in distribution.
  - The gap was already 43 vs 54 in job `5663aef5-fe0` on sizes up to 64, so it
    is mostly per-graph hardness variance with only 4 graphs per size.
  - Node timing also moved the reference by 5 on the same train instances (38
    vs 43 on sizes up to 40, across two runs).
  - I did not redraw train graphs to match, since that would select train
    instances by the reference's performance.
- **The MCN brute force still outranks the reference on the MCN metric** (60 vs
  56); see section 3.
- **The paper's backend (Gurobi) and its scale are not reproduced.** The
  backend is HiGHS/CP-SAT. The budget is 10 s CPU per instance instead of
  1800 s; the paper's parity sizes (up to n = 1000) are now included, and MCN
  graphs reach 96 nodes against the paper's 100.
- **The new MCN levels mix two compute nodes in the audit.** Audit cases reused
  their job-1 results on the levels job 1 had finished (same instances, same
  code), so their totals combine two nodes, like the reference reruns.
