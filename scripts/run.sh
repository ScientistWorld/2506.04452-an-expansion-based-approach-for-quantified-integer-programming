#!/bin/bash
# Validation job for the EQuIPS reproduction.
#
# Goals:
# 1. Run the repaired EQuIPS solver on the scored QRandomParity settings.
# 2. Write tmp/results/equips_results.json.
# 3. Convert results into scoring/scores.json.

set -e

cd /home/user

export PYTHONPATH="/home/user:/dev/shm/pylibs:$PYTHONPATH"

echo "=== EQuIPS Validation Run ==="
echo "Python: $(python3 --version)"

mkdir -p /home/user/tmp/results

bash /home/user/scripts/method.sh
bash /home/user/scripts/evaluate.sh

echo "=== DONE ==="
echo "Results written to tmp/results/equips_results.json and scoring/scores.json"
