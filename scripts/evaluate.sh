#!/bin/bash
# Evaluation script for solver result files.
# It only calls code in eval/ and writes scoring/scores.json.

set -e

cd /home/user

# Set PYTHONPATH to find workspace modules and installed packages
export PYTHONPATH="/home/user:/dev/shm/pylibs:$PYTHONPATH"

mkdir -p scoring
RESULTS_FILE="${1:-/home/user/tmp/results/equips_results.json}"

python3 eval/evaluate.py \
    --results-file "$RESULTS_FILE" \
    --scores-output scoring/scores.json

echo "Evaluation complete. Results in scoring/scores.json"
