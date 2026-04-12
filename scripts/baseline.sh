#!/bin/bash
# Run the search-style exact baseline and write a raw results file.
#
# Usage:
#   bash scripts/baseline.sh [output_json]

set -e

cd /home/user

export PYTHONPATH="/home/user:$PYTHONPATH"

if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

OUTPUT_PATH="${1:-/home/user/tmp/results/search_baseline_results.json}"
N_VALUES="${BASELINE_N_VALUES:-10}"
NUM_INSTANCES="${BASELINE_NUM_INSTANCES:-100}"
INSTANCE_START="${BASELINE_INSTANCE_START:-0}"
TIMEOUT_SECS="${BASELINE_TIMEOUT_SECS:-5.0}"
SEED="${BASELINE_SEED:-42}"
RESUME_FLAG="${BASELINE_RESUME:-1}"

mkdir -p "$(dirname "$OUTPUT_PATH")"

BASELINE_ARGS=(
    --n-values ${N_VALUES}
    --num-instances "${NUM_INSTANCES}"
    --instance-start "${INSTANCE_START}"
    --timeout "${TIMEOUT_SECS}"
    --seed "${SEED}"
    --output "$OUTPUT_PATH"
)

if [ "$RESUME_FLAG" = "1" ]; then
    BASELINE_ARGS+=(--resume)
fi

python3 baseline/run_qrandomparity.py \
    "${BASELINE_ARGS[@]}"
