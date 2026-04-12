#!/bin/bash
# CPU benchmark job for the scaled core-claim reproduction.
#
# This submission runs the paper's EQuIPS algorithm and a search-style exact
# baseline on the same QRandomParity batch, then writes scoring/scores.json.
# Result JSON files are preserved across retries so interrupted jobs can resume.

set -e

cd /home/user

mkdir -p /home/user/logs /home/user/tmp/results
exec > >(tee /home/user/logs/run.log) 2>&1

export PYTHONPATH="/home/user:$PYTHONPATH"
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

echo "=== Scaled EQuIPS Benchmark ==="
echo "Python: $(python3 --version)"

METHOD_RESULTS="/home/user/tmp/results/equips_results.json"
BASELINE_RESULTS="/home/user/tmp/results/search_baseline_results.json"
rm -f /home/user/scoring/scores.json

export EQUIPS_N_VALUES="10"
export EQUIPS_NUM_INSTANCES="100"
export EQUIPS_TIMEOUT_SECS="5.0"
export EQUIPS_INSTANCE_START="0"
export EQUIPS_SEED="42"
export EQUIPS_RESUME="1"
export EQUIPS_MIP_BACKEND="auto"

export BASELINE_N_VALUES="10"
export BASELINE_NUM_INSTANCES="100"
export BASELINE_TIMEOUT_SECS="5.0"
export BASELINE_INSTANCE_START="0"
export BASELINE_SEED="42"
export BASELINE_RESUME="1"

bash /home/user/scripts/method.sh "$METHOD_RESULTS"
bash /home/user/scripts/baseline.sh "$BASELINE_RESULTS"
bash /home/user/scripts/evaluate.sh "$METHOD_RESULTS" "$BASELINE_RESULTS"

python3 - <<'PY'
import json
from pathlib import Path

scores = json.loads(Path("/home/user/scoring/scores.json").read_text())
print("=== Score Summary ===")
for exp_name, exp in scores.get("experiments", {}).items():
    print(exp_name)
    for method_name, metrics in exp.get("results", {}).items():
        print(
            f"  {method_name}: solved={metrics['instances_solved']} "
            f"median_runtime_s={metrics['median_runtime_s']}"
        )
PY
