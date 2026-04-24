#!/bin/bash
# CPU job for the designer train/test split.
#
# This runs the current EQuIPS method and the exact baseline on the active
# scored QRandomParity benchmark (`n=10`, 100 fixed instances), then evaluates
# the public train slice and held-out test slice.

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

METHOD_RESULTS="/home/user/tmp/results/equips_qrandomparity_n10.json"
BASELINE_RESULTS="/home/user/tmp/results/search_enumeration_qrandomparity_n10.json"
rm -f /home/user/scoring/scores.json /home/user/scoring/scores_train.json /home/user/scoring/scores_test.json
find /home/user/tmp/results -type f -name '*.json' -delete

export EQUIPS_N_VALUES="10"
export EQUIPS_NUM_INSTANCES="100"
export EQUIPS_TIMEOUT_SECS="5.0"
export EQUIPS_INSTANCE_START="0"
export EQUIPS_SEED="42"
export EQUIPS_RESUME="0"
export EQUIPS_MIP_BACKEND="auto"

export BASELINE_N_VALUES="10"
export BASELINE_NUM_INSTANCES="100"
export BASELINE_TIMEOUT_SECS="5.0"
export BASELINE_INSTANCE_START="0"
export BASELINE_SEED="42"
export BASELINE_RESUME="0"

bash /home/user/scripts/method.sh "$METHOD_RESULTS"
bash /home/user/scripts/baseline.sh "$BASELINE_RESULTS"
bash /home/user/scripts/evaluate.sh
bash /home/user/scripts/evaluate_train.sh
bash /home/user/scripts/evaluate_test.sh

python3 - <<'PY'
import json
from pathlib import Path

for name in ("scores.json", "scores_train.json", "scores_test.json"):
    path = Path("/home/user/scoring") / name
    print(f"=== {name} ===")
    scores = json.loads(path.read_text())
    for exp_name, exp in scores.get("experiments", {}).items():
        print(exp_name)
        for method_name, metrics in exp.get("results", {}).items():
            print(
                f"  {method_name}: solved={metrics['instances_solved']} "
                f"median={metrics['median_runtime_s']} "
                f"mean={metrics['mean_runtime_s']} "
                f"p90={metrics['p90_runtime_s']}"
            )
PY
