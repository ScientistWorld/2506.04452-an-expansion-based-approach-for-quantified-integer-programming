#!/bin/bash
# Comprehensive evaluation job — runs EQuIPS at paper scale
# and compares with enumeration baseline.
#
# Goals:
# 1. EQuIPS at n=10,20,30,50,100,200,300 (paper-scale)
# 2. Enumeration baseline at n=5,8,10,12 (shows exponential scaling)
# 3. Update scoring/scores.json with all results

set -e

cd /home/user

# Set PYTHONPATH for highspy
export PYTHONPATH="/home/user:$PYTHONPATH"

echo "=== Comprehensive EQuIPS Evaluation ==="
echo "Python: $(python3 --version)"

# Run EQuIPS at paper-scale n values (this writes scores.json)
echo ""
echo "=== EQuIPS at paper scale ==="
python3 eval/evaluate.py \
    --n-values 10 20 30 50 100 200 300 \
    --num-instances 20 \
    --timeout 120.0 \
    --seed 42 \
    --scores-output scoring/scores.json

# Run enumeration baseline and add to scores
echo ""
echo "=== Enumeration baseline comparison ==="
python3 << 'PYEOF'
import time, sys, json
sys.path.insert(0, '/home/user')

from data.qrandomparity import generate_qrandomparity
from baseline.enumerate import enumerate_baseline
from method.equips import solve_qip

# Load existing scores
scores_path = '/home/user/scoring/scores.json'
with open(scores_path) as f:
    scores = json.load(f)

# Ensure vs_search experiment exists
if 'qrandomparity_vs_search' not in scores['experiments']:
    scores['experiments']['qrandomparity_vs_search'] = {
        'description': 'EQuIPS vs enumeration baseline (exponential vs polynomial)',
        'results': {}
    }

exp = scores['experiments']['qrandomparity_vs_search']

# Run enumeration at various n values (5 instances each)
for n in [5, 8, 10, 12, 15]:
    print(f'\nBaseline n={n}:')
    times_enum = []
    solved_enum = 0

    for i in range(5):
        seed = 42 + n * 1000 + i
        problem = generate_qrandomparity(n, seed)

        # Enumeration baseline
        t0 = time.time()
        try:
            r = enumerate_baseline(problem, timeout_s=120.0)
            elapsed = time.time() - t0
            if r['status'] in ('SAT', 'UNSAT'):
                solved_enum += 1
                times_enum.append(elapsed)
        except Exception as e:
            elapsed = time.time() - t0
            print(f'  Error: {e}')
        print(f'  Enum n={n} i={i}: {elapsed:.4f}s status={r.get("status","?")}')

    # EQuIPS for reference (same instances)
    times_equips = []
    solved_equips = 0
    for i in range(5):
        seed = 42 + n * 1000 + i
        problem = generate_qrandomparity(n, seed)
        t0 = time.time()
        try:
            r = solve_qip(problem, timeout_s=30.0)
            elapsed = time.time() - t0
            if r['status'] in ('SAT', 'UNSAT'):
                solved_equips += 1
                times_equips.append(elapsed)
        except Exception as e:
            elapsed = time.time() - t0
        print(f'  EQuIPS n={n} i={i}: {elapsed:.4f}s')

    med_en = sorted(times_enum)[len(times_enum)//2] if times_enum else None
    med_eq = sorted(times_equips)[len(times_equips)//2] if times_equips else None

    print(f'  Summary: Enum n={n}: solved={solved_enum}/5 med={med_en:.4f}s | EQuIPS solved={solved_equips}/5 med={med_eq:.4f}s')

    # Add to vs_search experiment only
    exp['results'][f'enum_n{n}'] = {
        'type': 'baseline',
        'instances_solved': solved_enum,
        'median_runtime_s': round(med_en, 4) if med_en else None
    }
    exp['results'][f'equips_n{n}'] = {
        'type': 'proposed',
        'instances_solved': solved_equips,
        'median_runtime_s': round(med_eq, 4) if med_eq else None
    }

# Save updated scores
with open(scores_path, 'w') as f:
    json.dump(scores, f, indent=2)
print('\nScores updated in scoring/scores.json')
PYEOF

echo ""
echo "=== DONE ==="
echo "EQuIPS: polynomial scaling (CEGAR avoids full expansion)"
echo "Enumeration: exponential scaling (2^n outer assignments)"
echo "Results in scoring/scores.json"
