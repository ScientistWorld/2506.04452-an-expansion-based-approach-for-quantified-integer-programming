#!/bin/bash
# Hidden-test evaluation: runs every solver on disk on the hidden instances and
# writes scoring/scores_test.json. Only code in eval/test/ is used.
#
# Usage:
#   bash scripts/evaluate_test.sh                 # method/, baseline/, methods/*
#   bash scripts/evaluate_test.sh DIR [DIR ...]   # only these solver directories
#
# A solver directory holds solver.json: {"name": ..., "command": [...]}.
# The evaluator calls `command + [instance.qlp, answer.json]` from the
# workspace root and measures CPU time itself.
# Optional: QIP_DETAILS_OUTPUT=path writes per-level diagnostics;
# QIP_CHECKPOINT=path lets an interrupted run resume finished levels.

set -euo pipefail

cd /home/user
export PYTHONPATH="/home/user${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p scoring

SOLVER_ARGS=()
for solver_dir in "$@"; do
    SOLVER_ARGS+=(--solver "$solver_dir")
done

python3 eval/test/evaluate.py "${SOLVER_ARGS[@]}" ${QIP_DETAILS_OUTPUT:+--details-output "$QIP_DETAILS_OUTPUT"} ${QIP_CHECKPOINT:+--checkpoint "$QIP_CHECKPOINT"} --scores-output scoring/scores_test.json

echo "Test evaluation complete. Results in scoring/scores_test.json"
