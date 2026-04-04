#!/bin/bash
# Job script submitted via the end-of-turn YAML block.
#
# This runs inside the compute container with:
#   - Your workspace mounted at /home/user
#   - GPU(s) available (not needed for EQuIPS — CPU-based IP solver)
#   - No internet access
#
# EQuIPS is a CPU-based algorithm. Request gpus:0 to save GPU budget.

set -e

cd /home/user

# Set PYTHONPATH to find highspy
# Try multiple possible locations
export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
export PYTHONPATH="$HOME/.local/lib/python3.12/site-packages:$PYTHONPATH"
export PYTHONPATH="/usr/local/lib/python3.12/dist-packages:$PYTHONPATH"

echo "=== EQuIPS Evaluation ==="
echo "Python: $(python3 --version)"
echo "PYTHONPATH: $PYTHONPATH"

# Test if highspy is importable
python3 -c "import highspy; print(f'HiGHS version: {highspy.__version__}')" 2>&1 || echo "highspy not found, checking other locations..."
for p in /dev/shm/pylibs $HOME/.local/lib/python3.12/site-packages /usr/local/lib/python3.12/dist-packages; do
    if [ -d "$p" ]; then
        echo "  Checking $p: $(ls $p | grep -i highspy | head -3)"
    fi
done

# Try to install if not found
if ! python3 -c "import highspy" 2>/dev/null; then
    echo "Installing highspy..."
    pip install highspy numpy --user --quiet 2>&1 || echo "pip install failed"
fi

# Run the solver test
echo ""
echo "=== Running EQuIPS Test ==="
python3 run_solver_test.py

echo ""
echo "=== Running Full Evaluation ==="
bash scripts/evaluate.sh
