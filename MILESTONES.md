# Reproduction Milestones

**Current: core_claim_plus**

## Progress Log

### [2026-04-09] - core_claim_plus
- Fixed bugs in baseline/enumerate.py:
  - Variable identification: was using `v.name.startswith('x_')` but QRandomParity uses `x1`, `x2`, etc. (no underscore). Fixed to use `v.name.startswith('x') and v.level == 1`
  - HiGHS addRow: wrong parameter order in multiple calls. Fixed to `(lower, upper, num_nz, indices, values)`
- Added comprehensive evaluation job: EQuIPS at n=10-300 (20 inst), enumeration baseline at n=5-15 (5 inst)
- Demonstrates polynomial (EQuIPS CEGAR) vs exponential (enumeration) scaling

## Stop Justification

