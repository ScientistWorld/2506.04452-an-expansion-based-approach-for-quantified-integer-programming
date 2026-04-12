#!/bin/bash
# Reproduce the paper's results end-to-end.
#
# This script runs inside the compute container and should call
# the paper's method and the shared evaluator. Baselines are optional
# in this workspace and are not part of the default scored workflow.
#
# Assumes:
#   - Container is built (environment/container.sif)
#   - Data and models are downloaded (via scripts/download.sh)
#   - Working directory is /home/user
#
# This is the "gold standard" reproduction —
# You do not need to run this, but keep this in good shape
# so other agents can easily run a full loop of reproduction and get the paper's numbers.

set -e

cd /home/user

# Set PYTHONPATH for highspy
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

python3 - <<'PY'
import importlib

for module_name in ("numpy", "highspy"):
    module = importlib.import_module(module_name)
    print(f"{module_name}={getattr(module, '__version__', 'unknown')}")
PY

RESULTS_FILE="/home/user/tmp/results/equips_results.json"
bash scripts/method.sh "$RESULTS_FILE"
bash scripts/evaluate.sh "$RESULTS_FILE"
