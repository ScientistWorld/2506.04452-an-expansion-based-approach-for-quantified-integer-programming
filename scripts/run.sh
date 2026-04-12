#!/bin/bash
# CPU benchmark job for the EQuIPS reproduction.
#
# Goals:
# 1. Run the repaired EQuIPS solver on the minimum full-size scored QRandomParity setting.
# 2. Write tmp/results/equips_results.json.
# 3. Convert results into scoring/scores.json.

set -e

cd /home/user

export PYTHONPATH="/home/user:$PYTHONPATH"
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

echo "=== EQuIPS Validation Run ==="
echo "Python: $(python3 --version)"

mkdir -p /home/user/tmp/results

export EQUIPS_N_VALUES="100"
export EQUIPS_NUM_INSTANCES="100"
export EQUIPS_TIMEOUT_SECS="300.0"
export EQUIPS_SEED="42"

bash /home/user/scripts/method.sh
bash /home/user/scripts/evaluate.sh

echo "=== DONE ==="
echo "Results written to tmp/results/equips_results.json and scoring/scores.json"
