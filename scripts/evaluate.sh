#!/bin/bash
# Development evaluation on the public train split; writes scoring/scores.json.
# Same protocol and code path as scripts/evaluate_train.sh.
#
# Usage:
#   bash scripts/evaluate.sh                 # method/, baseline/, methods/*
#   bash scripts/evaluate.sh DIR [DIR ...]   # only these solver directories

set -euo pipefail

cd /home/user
export PYTHONPATH="/home/user${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p scoring

SOLVER_ARGS=()
for solver_dir in "$@"; do
    SOLVER_ARGS+=(--solver "$solver_dir")
done

python3 eval/evaluate.py "${SOLVER_ARGS[@]}" --scores-output scoring/scores.json

echo "Evaluation complete. Results in scoring/scores.json"
