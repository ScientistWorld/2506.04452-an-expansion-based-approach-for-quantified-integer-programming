# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-04-04 00:00] - none
- Read the paper thoroughly. Identified it as an algorithms/formal methods paper (not ML) about solving Quantified Integer Programming (QIP) using expansion-based CEGAR.
- Key finding: EQuIPS uses an IP solver (Gurobi in paper, HiGHS for reproduction) as a black box.
- Core claim: EQuIPS outperforms search-based QIP solvers on QRandomParity benchmarks.

### [2026-04-04 00:00] - method_runs
- Implemented EQuIPS algorithm in method/equips.py (the paper's CEGAR-based QIP solver)
- Implemented QRandomParity problem generator in method/qrandomparity.py
- Implemented evaluation script in eval/evaluate.py
- Set up environment with HiGHS (highspy) as the IP solver backend
- Bash environment was stuck (full filesystem CWD) but code was written via Write/Edit tools
- Workspace:  method/equips.py, method/qrandomparity.py, method/__init__.py,
  eval/evaluate.py, scripts/evaluate.sh, scripts/method.sh, scripts/run.sh,
  scripts/reproduce.sh, scoring/reference.json, briefing/*.md, scoring/*.md
