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

METHOD_RESULTS="/home/user/tmp/results/equips_results.json"
BASELINE_RESULTS="/home/user/tmp/results/search_baseline_results.json"

bash scripts/method.sh "$METHOD_RESULTS"
bash scripts/baseline.sh "$BASELINE_RESULTS"
bash scripts/evaluate.sh "$METHOD_RESULTS" "$BASELINE_RESULTS"
