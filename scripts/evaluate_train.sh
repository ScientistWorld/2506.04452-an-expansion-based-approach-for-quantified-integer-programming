#!/bin/bash
# Train-split evaluation: runs every solver on disk on the public train
# instances (data/train_instances.json) and writes scoring/scores_train.json.
# Only code in eval/train/ (and the public data/ generator) is used.  Same
# protocol as the hidden test: sandboxed solver, counted instruction budget.
#
# Usage:
#   bash scripts/evaluate_train.sh                 # method/, baseline/, methods/*
#   bash scripts/evaluate_train.sh DIR [DIR ...]   # only these solver directories

set -euo pipefail

cd /home/user
export PYTHONPATH="/home/user${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p scoring

SOLVER_ARGS=()
for solver_dir in "$@"; do
    SOLVER_ARGS+=(--solver "$solver_dir")
done

python3 eval/train/evaluate.py "${SOLVER_ARGS[@]}" ${QIP_DETAILS_OUTPUT:+--details-output "$QIP_DETAILS_OUTPUT"} ${QIP_CHECKPOINT:+--checkpoint "$QIP_CHECKPOINT"} --scores-output scoring/scores_train.json

echo "Train evaluation complete. Results in scoring/scores_train.json"
