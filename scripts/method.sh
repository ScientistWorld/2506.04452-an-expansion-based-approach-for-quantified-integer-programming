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

OUTPUT_PATH="${1:-/home/user/tmp/results/equips_results.json}"
mkdir -p "$(dirname "$OUTPUT_PATH")"

python3 method/run_qrandomparity.py \
    --n-values 100 200 \
    --num-instances 10 \
    --timeout 120.0 \
    --seed 42 \
    --output "$OUTPUT_PATH"
