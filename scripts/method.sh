#!/bin/bash
# Run the paper's proposed method (EQuIPS) and write a raw results file.
#
# Usage:
#   bash scripts/method.sh [output_json]

set -e

cd /home/user

export PYTHONPATH="/home/user:$PYTHONPATH"

if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

python3 - <<'PY'
import importlib

for module_name in ("numpy", "highspy"):
    module = importlib.import_module(module_name)
    print(f"{module_name}={getattr(module, '__version__', 'unknown')}")
PY

OUTPUT_PATH="${1:-/home/user/tmp/results/equips_results.json}"
N_VALUES="${EQUIPS_N_VALUES:-100 200}"
NUM_INSTANCES="${EQUIPS_NUM_INSTANCES:-10}"
TIMEOUT_SECS="${EQUIPS_TIMEOUT_SECS:-120.0}"
SEED="${EQUIPS_SEED:-42}"

mkdir -p "$(dirname "$OUTPUT_PATH")"

python3 method/run_qrandomparity.py \
    --n-values ${N_VALUES} \
    --num-instances "${NUM_INSTANCES}" \
    --timeout "${TIMEOUT_SECS}" \
    --seed "${SEED}" \
    --output "$OUTPUT_PATH"
