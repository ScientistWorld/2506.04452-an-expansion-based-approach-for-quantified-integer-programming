#!/bin/bash
# Run the exhaustive-enumeration baseline.
#
# Usage:
#   bash scripts/baseline.sh INSTANCE.qlp ANSWER.json   # solve one instance
#   bash scripts/baseline.sh                            # score it on the train split
set -euo pipefail
cd /home/user
export PYTHONPATH="/home/user${PYTHONPATH:+:$PYTHONPATH}"
if [ "$#" -ge 2 ]; then
    python3 baseline/solve.py "$1" "$2"
    cat "$2"
else
    mkdir -p tmp
    python3 eval/train/evaluate.py --solver baseline --scores-output tmp/scores_train_baseline.json
fi
