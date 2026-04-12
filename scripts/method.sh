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
import importlib.util

for module_name in ("numpy", "highspy"):
    module = importlib.import_module(module_name)
    print(f"{module_name}={getattr(module, '__version__', 'unknown')}")

if importlib.util.find_spec("ortools") is not None:
    module = importlib.import_module("ortools")
    print(f"ortools={getattr(module, '__version__', 'unknown')}")
else:
    print("ortools=not-installed")
PY

OUTPUT_PATH="${1:-/home/user/tmp/results/equips_results.json}"
N_VALUES="${EQUIPS_N_VALUES:-10}"
NUM_INSTANCES="${EQUIPS_NUM_INSTANCES:-100}"
INSTANCE_START="${EQUIPS_INSTANCE_START:-0}"
TIMEOUT_SECS="${EQUIPS_TIMEOUT_SECS:-5.0}"
SEED="${EQUIPS_SEED:-42}"
RESUME_FLAG="${EQUIPS_RESUME:-1}"
export EQUIPS_MIP_BACKEND="${EQUIPS_MIP_BACKEND:-auto}"

mkdir -p "$(dirname "$OUTPUT_PATH")"

METHOD_ARGS=(
    --n-values ${N_VALUES}
    --num-instances "${NUM_INSTANCES}"
    --instance-start "${INSTANCE_START}"
    --timeout "${TIMEOUT_SECS}"
    --seed "${SEED}"
    --output "$OUTPUT_PATH"
)

if [ "$RESUME_FLAG" = "1" ]; then
    METHOD_ARGS+=(--resume)
fi

python3 method/run_qrandomparity.py \
    "${METHOD_ARGS[@]}"
