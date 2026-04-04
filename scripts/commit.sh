#!/bin/bash
cd /home/user
git add -A
git commit -m "Implement EQuIPS solver and evaluation framework

Key changes:
- method/equips.py: EQuIPS CEGAR-based QIP solver using HiGHS
- data/qrandomparity.py: QRandomParity problem generator
- eval/evaluate.py: Evaluation script
- scripts/test_equips.py: Quick solver test
- scoring/reference.json: Paper reference numbers
- briefing/*.md: Paper briefing documents
- scoring/TARGETS.md, DIRECTION.md, CONSTRAINTS.md: Scoring files
- baseline/enumerate.py: Naive enumeration baseline

Milestone: method_runs (solver executes end-to-end)"
git push
