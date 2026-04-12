#!/bin/bash
# Evaluation script for solver result files.
# It only calls code in eval/ and writes scoring/scores.json.

set -e

cd /home/user

export PYTHONPATH="/home/user:$PYTHONPATH"
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

mkdir -p scoring

RESULTS_ARGS=()
if [ "$#" -eq 0 ]; then
    RESULTS_ARGS+=(--results-file "/home/user/tmp/results/equips_results.json")
else
    for results_file in "$@"; do
        RESULTS_ARGS+=(--results-file "$results_file")
    done
fi

python3 eval/evaluate.py \
    "${RESULTS_ARGS[@]}" \
    --scores-output scoring/scores.json

echo "Evaluation complete. Results in scoring/scores.json"
