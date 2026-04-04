#!/bin/bash
# Evaluation script — the standard way to evaluate work in this environment.
#
# This script must be SELF-CONTAINED using only code in eval/.
# Do NOT import from method/ — evaluate.sh must work even when the
# paper's method code is hidden from a scientist agent.
#
# OUTPUT CONTRACT: This script MUST write scoring/scores.json containing
# a JSON dict nested by experiment.
# This file is read by the system for automated comparison.

set -e

cd /home/user

# Set PYTHONPATH to find highspy and workspace modules
export PYTHONPATH="/home/user:/dev/shm/pylibs:$PYTHONPATH"

mkdir -p scoring

# Run the evaluation on QRandomParity
python3 eval/evaluate.py \
    --n-values 10 20 30 50 \
    --num-instances 10 \
    --timeout 30.0 \
    --seed 42 \
    --scores-output scoring/scores.json

echo "Evaluation complete. Results in scoring/scores.json"
