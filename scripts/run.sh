#!/bin/bash
# CPU job for the designer train/test split.
#
# This runs the existing EQuIPS method on the two reference QRandomParity
# experiments and then evaluates the public train slice and held-out test slice.

set -e

cd /home/user

mkdir -p /home/user/logs /home/user/tmp/results
exec > >(tee /home/user/logs/run.log) 2>&1

export PYTHONPATH="/home/user:$PYTHONPATH"
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

echo "=== Designer Train/Test Evaluation ==="
echo "Python: $(python3 --version)"

RESULTS="/home/user/tmp/results/equips_reference_split_results.json"
rm -f /home/user/scoring/scores_train.json /home/user/scoring/scores_test.json

export EQUIPS_N_VALUES="100 200"
export EQUIPS_NUM_INSTANCES="100"
export EQUIPS_TIMEOUT_SECS="5.0"
export EQUIPS_INSTANCE_START="0"
export EQUIPS_SEED="42"
export EQUIPS_RESUME="1"
export EQUIPS_MIP_BACKEND="auto"

bash /home/user/scripts/method.sh "$RESULTS"
bash /home/user/scripts/evaluate_train.sh "$RESULTS"
bash /home/user/scripts/evaluate_test.sh "$RESULTS"

python3 - <<'PY'
import json
from pathlib import Path

for name in ("scores_train.json", "scores_test.json"):
    path = Path("/home/user/scoring") / name
    print(f"=== {name} ===")
    scores = json.loads(path.read_text())
    for exp_name, exp in scores.get("experiments", {}).items():
        print(exp_name)
        for method_name, metrics in exp.get("results", {}).items():
            print(
                f"  {method_name}: solved={metrics['instances_solved']} "
                f"median={metrics['median_runtime_s']} "
                f"p90={metrics['p90_runtime_s']}"
            )
PY
