#!/bin/bash
# Run a baseline method from the paper.
#
# Baselines are simple reference methods the paper compares against.
# This script runs a naive enumeration baseline for comparison.
#
# Usage:
#   bash scripts/baseline.sh

set -e

cd /home/user

if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

echo "Running naive enumeration baseline on small QRandomParity instances..."
python3 -c "
import sys
sys.path.insert(0, '/home/user')
from data.qrandomparity import generate_qrandomparity
from baseline.enumerate import enumerate_baseline
import time

print('Baseline: Naive enumeration')
for n in [3, 4, 5]:
    for seed in range(3):
        problem = generate_qrandomparity(n, seed)
        result = enumerate_baseline(problem, timeout_s=5.0)
        print(f'  n={n} seed={seed}: {result[\"status\"]} ({result[\"runtime\"]:.3f}s)')
"

echo "Baseline complete."
