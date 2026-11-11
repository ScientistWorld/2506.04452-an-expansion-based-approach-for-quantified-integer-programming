#!/bin/bash
# Reproduce the reference end to end inside the compute container:
# score the proposed method and the baseline on the train split and, when the
# hidden test folder is present, on the hidden test.
set -euo pipefail
cd /home/user
bash scripts/evaluate_train.sh
if [ -f eval/test/instances.json ]; then
    bash scripts/evaluate_test.sh
fi
