#!/bin/bash
# Train-slice evaluation script for solver result files.
# It only calls code in eval/train/ and writes scoring/scores_train.json.

set -e

cd /home/user

export PYTHONPATH="/home/user:$PYTHONPATH"
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

mkdir -p scoring

RESULTS_ARGS=()
if [ "$#" -eq 0 ]; then
    while IFS= read -r results_file; do
        RESULTS_ARGS+=(--results-file "$results_file")
    done < <(
        python3 - <<'PY'
import json
from pathlib import Path

roots = [
    Path("/home/user/tmp/results"),
    Path("/home/user/checkpoints"),
    Path("/home/user/outputs"),
]

seen = set()
for root in roots:
    if not root.exists():
        continue
    for path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if {"solver", "timeout_s", "results"} <= set(payload):
            resolved = str(path.resolve())
            if resolved not in seen:
                print(resolved)
                seen.add(resolved)
PY
    )
else
    for results_file in "$@"; do
        RESULTS_ARGS+=(--results-file "$results_file")
    done
fi

if [ "${#RESULTS_ARGS[@]}" -eq 0 ]; then
    echo "No solver result files found for train evaluation." >&2
    exit 1
fi

python3 eval/train/evaluate.py \
    "${RESULTS_ARGS[@]}" \
    --scores-output scoring/scores_train.json

echo "Train evaluation complete. Results in scoring/scores_train.json"
