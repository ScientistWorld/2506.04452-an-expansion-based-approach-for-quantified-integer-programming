# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-04-09] - core_claim (wrapped up)
- Workspace fully implemented and validated
- EQuIPS solver, evaluation framework, baseline all working
- **Blocker**: Container build fails due to persistent transient registry errors
  - Tried: mirror.gcr.io, docker.io, gcr.io/google-appengine, ghcr.io, public.ecr.aws, mcr.microsoft.com
  - Error: "invalid character 's' after top-level value" (JSON parse failure in registry response)
  - The existing container.sif (built Apr 5, 108MB) works fine — only rebuilds fail
- Paper already validated in prior sessions — code and results are sound

## Stop Justification

Container rebuilds persistently fail with transient "registry response malformed" errors across all registries tried. This is an external infrastructure issue, not a code or configuration problem. The existing `container.sif` built successfully on Apr 5. All workspace code (EQuIPS solver, evaluation, baseline, data generators) is complete and validated — `core_claim` was achieved in prior sessions.

## What Was Achieved (prior sessions)

- EQuIPS algorithm implemented (CEGAR-based QIP solver)
- QRandomParity procedural benchmark generator
- Evaluation framework with scoring/scores.json
- Baseline enumeration (with bugs fixed)
- QIPProblem, Variable, Constraint data classes
- HiGHS IP solver integration
- Paper's QRandomParity encoding verified (SAT for all n values)
- EQuIPS polynomial scaling demonstrated (n=10-200)
