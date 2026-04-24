# Verification Report

## Initial Assessment
The workspace started in a mostly usable `core_claim` state. The solver and
benchmark artifacts were already present, `validate.py --compare` passed, and
the claimed scored result in `scoring/scores.json` matched persisted raw result
files for the active `qrandomparity_n10` benchmark. The main remaining checks
were gym packaging quality: method leakage in scientist-facing docs, scoring
weights, and root-folder cleanliness.

## Issues Found
- Minor: `scoring/TARGETS.md`, `scoring/CONSTRAINTS.md`, and
  `scoring/DIRECTION.md` leaked the paper method name into scientist-facing gym
  guidance.
- Minor: `scoring/reference.json` gave the active scored target a tiny weight
  while the unscored paper-context experiments held almost all the mass, which
  was a poor rubric for future gym expansion.
- Minor: stray `core.*` crash dumps were left at the workspace root.
- Minor: `CHECKLIST.md` referenced `python run_validator.py`, but the actual
  validator entrypoint is `python validate.py`.

## Fixes Applied
- Rewrote the scientist-facing scoring docs to describe the benchmark and
  allowed research space without naming the paper’s solver.
- Reweighted `scoring/reference.json` to prioritize the active scored target:
  `qrandomparity_n10` now has weight `0.7`, while the reference-only context
  experiments `qrandomparity_n100` and `qrandomparity_n200` each have weight
  `0.15`.
- Removed the stray root-level crash dumps.
- Corrected the validator command in `CHECKLIST.md`.
- Re-ran:
  - `python3 validate.py --compare`
  - `bash scripts/download.sh`
  - `bash scripts/evaluate.sh`
  - `bash scripts/evaluate_train.sh`
  - `bash scripts/evaluate_test.sh`

## Final Judgment
This workspace is ready to serve as a research gym at the claimed `core_claim`
milestone. Improve-mode agents have a working implementation, persisted raw
results, reusable scoring, and train/test evaluation. From-scratch agents can
use the problem definition, data generator, and evaluation stack without being
told the paper method. The main limitation is that the scored target is a
scaled replacement benchmark rather than the paper’s larger QRandomParity
settings, so this is a valid but reduced-scope gym.

- Milestone: core_claim
- Ready for gym use: yes
- Confidence: medium
- Key limitation: The active scored benchmark is the scaled `qrandomparity_n10` slice, not the paper-scale `n=100+` settings.
