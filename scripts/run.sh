#!/bin/bash
# CPU benchmark job for the EQuIPS reproduction.
#
# Goals:
# 1. Run the repaired EQuIPS solver on the minimum full scored QRandomParity experiment.
# 2. Write tmp/results/equips_n100_results.json incrementally so partial progress survives node loss.
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

RESULTS_FILE="/home/user/tmp/results/equips_n100_results.json"
if [ "${EQUIPS_RESET_RESULTS:-0}" = "1" ]; then
    rm -f "$RESULTS_FILE"
fi

export EQUIPS_N_VALUES="100"
export EQUIPS_TIMEOUT_SECS="30.0"
export EQUIPS_SEED="42"
export EQUIPS_RESUME="1"

for INSTANCE_START in 0 20 40 60 80; do
    export EQUIPS_INSTANCE_START="$INSTANCE_START"
    export EQUIPS_NUM_INSTANCES="20"
    echo "--- Running chunk starting at instance $INSTANCE_START ---"
    bash /home/user/scripts/method.sh "$RESULTS_FILE"
done

bash /home/user/scripts/evaluate.sh "$RESULTS_FILE"

echo "=== DONE ==="
echo "Results written to $RESULTS_FILE and /home/user/scoring/scores.json"
