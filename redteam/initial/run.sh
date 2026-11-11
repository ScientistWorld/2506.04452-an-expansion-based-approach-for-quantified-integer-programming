#!/bin/bash
# CPU validation job for the repaired optimization path.
#
# This job runs the solver sanity tests in quick mode, then exercises the
# paper-provided sample `.qlp` instances from the official EQuIPS release to
# verify that the new parser and decision-to-optimization reduction work inside
# the packaged environment.

set -euo pipefail

cd /home/user

mkdir -p /home/user/logs /home/user/tmp/results
exec > >(tee /home/user/logs/run.log) 2>&1

export PYTHONPATH="/home/user:$PYTHONPATH"
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

echo "=== EQuIPS Optimization Validation ==="
echo "Python: $(python3 --version)"
echo "Working directory: $(pwd)"

QLP_RESULTS="/home/user/tmp/results/equips_qlp_examples.json"
rm -f "$QLP_RESULTS"

export EQUIPS_TEST_MODE="quick"
python3 /home/user/scripts/test_equips.py

python3 /home/user/method/run_qlp_instance.py \
    --instance /home/user/data/downloads/EQuIPS/instances/MiniLotSizing.qlp \
    --instance /home/user/data/downloads/EQuIPS/instances/MiniMCN.qlp \
    --timeout 60 \
    --output "$QLP_RESULTS"

python3 /home/user/validate.py

python3 - <<'PY'
import json
from pathlib import Path

path = Path("/home/user/tmp/results/equips_qlp_examples.json")
payload = json.loads(path.read_text())
print("=== qlp_examples ===")
for result in payload.get("results", []):
    print(
        f"  {result['instance_name']}: status={result['status']} "
        f"runtime={result['runtime_s']:.4f}s "
        f"objective={result['optimal_value']}"
    )
PY
