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

# Set PYTHONPATH to find highspy (installed via container.def/setup.sh)
export PYTHONPATH="/home/user:$PYTHONPATH"

echo "=== EQuIPS Evaluation ==="
echo "Python: $(python3 --version)"
echo "PYTHONPATH: $PYTHONPATH"

# Test if highspy is importable
if python3 -c "import highspy; h = highspy.Highs(); print('HiGHS works')" 2>&1; then
    echo "HiGHS is available"
else
    echo "HiGHS not found, trying to install..."
    python3 -m pip install --no-cache-dir highspy numpy 2>/dev/null || \
    pip3 install --no-cache-dir highspy numpy 2>/dev/null || true
fi

# Run comprehensive evaluation with paper-scale n values
echo ""
echo "=== Running Comprehensive Evaluation ==="
python3 eval/evaluate.py \
    --n-values 10 20 30 50 100 200 \
    --num-instances 20 \
    --timeout 120.0 \
    --seed 42 \
    --scores-output scoring/scores.json

echo ""
echo "=== Comparison with Paper ==="
echo "Paper EQuIPS n=100: median=0.06s, solved=100/100"
echo "Reproduced EQuIPS n=100: see scoring/scores.json"
echo "Evaluation complete. Results in scoring/scores.json"
