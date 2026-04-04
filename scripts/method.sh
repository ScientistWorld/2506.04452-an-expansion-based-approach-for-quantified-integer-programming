#!/bin/bash
# Run the paper's proposed method (EQuIPS).
#
# Usage:
#   bash scripts/method.sh

set -e

cd /home/user

# Set PYTHONPATH to find highspy
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

# Run EQuIPS on QRandomParity benchmark
python3 scripts/test_equips.py
