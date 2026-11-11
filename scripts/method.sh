#!/bin/bash
# Run the proposed method (EQuIPS).
#
# Usage:
#   bash scripts/method.sh INSTANCE.qlp ANSWER.json   # solve one instance
#   bash scripts/method.sh                            # score it on the train split
set -euo pipefail
cd /home/user
export PYTHONPATH="/home/user${PYTHONPATH:+:$PYTHONPATH}"
if [ "$#" -ge 2 ]; then
    QIP_CPU_BUDGET_S="${QIP_CPU_BUDGET_S:-10}" python3 method/solve.py "$1" "$2"
    cat "$2"
else
    mkdir -p tmp
    python3 eval/train/evaluate.py --solver method --scores-output tmp/scores_train_method.json
fi
