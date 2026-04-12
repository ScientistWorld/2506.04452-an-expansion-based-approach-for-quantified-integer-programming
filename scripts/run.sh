#!/bin/bash
# CPU benchmark job for the EQuIPS reproduction.
#
# Goals:
# 1. Run the repaired EQuIPS solver on the full scored QRandomParity slice.
# 2. Write tmp/results/equips_results.json.
# 3. Convert results into scoring/scores.json.

set -e

cd /home/user

mkdir -p /home/user/logs /home/user/tmp/results
exec > >(tee /home/user/logs/run.log) 2>&1

export PYTHONPATH="/home/user:$PYTHONPATH"
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

echo "=== EQuIPS Validation Run ==="
echo "Python: $(python3 --version)"

RESULTS_FILE="/home/user/tmp/results/equips_results.json"

export EQUIPS_N_VALUES="100 200"
export EQUIPS_NUM_INSTANCES="100"
export EQUIPS_TIMEOUT_SECS="300.0"
export EQUIPS_SEED="42"

bash /home/user/scripts/method.sh "$RESULTS_FILE"
bash /home/user/scripts/evaluate.sh "$RESULTS_FILE"

echo "=== DONE ==="
echo "Results written to $RESULTS_FILE and /home/user/scoring/scores.json"
