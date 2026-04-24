# Reproduction Checklist

Check off items as you complete them. Order doesn't matter - work however makes sense for this paper.

## Briefing
- [x] `briefing/problem.md` (method-agnostic)
- [x] `briefing/evaluation.md` (method-agnostic)
- [x] `briefing/method.md`
- [x] `briefing/overview.md`

## Scoring
- [x] `scoring/reference.json` - paper's reported numbers
- [x] Workspace validated via `python validate.py` (passes with patched validator)
- [x] `scoring/scores.json` - reproduced numbers from the repaired post-audit run
- [x] `scoring/TARGETS.md` - primary and constraint targets for the scored benchmark
- [x] `scoring/CONSTRAINTS.md` - what a scientist must hold fixed
- [x] `scoring/EXPERIMENTS.md` - experiment purposes aligned with `scores.json`
- [x] `scoring/DIRECTION.md` - research direction scope

## Code
- [x] Evaluation code in `eval/`
- [x] Method implementation in `method/`
- [x] Baseline implementation in `baseline/`
- [x] Data/problem generator in `data/`

## Scripts
- [x] `scripts/evaluate.sh`
- [x] `scripts/reproduce.sh`
- [x] `scripts/download.sh` (idempotent, size comment at top)
- [x] `scripts/baseline.sh`
- [x] `scripts/method.sh`
- [x] `scripts/run.sh`

## Environment
- [x] `environment/container.def` + `environment/setup.sh`

## Data
- [x] Dataset: QRandomParity generated procedurally (no external data needed)
- [x] Official upstream EQuIPS sample `.qlp` instances wired through `scripts/download.sh`

## Milestones
- [x] `method_runs` - EQuIPS implemented and wired into the benchmark scripts
- [x] `core_claim` - minimum experiment supports central claim
- [ ] `core_claim_plus` - additional settings beyond the minimum
- [ ] `secondary_claims`
- [ ] `majority`
- [ ] `near_complete`
- [ ] `full`
