#!/bin/bash
# CPU diagnostic job for the EQuIPS reproduction.
#
# Goals:
# 1. Exercise the lower-overhead equality encoding plus hybrid backend path.
# 2. Persist per-instance recursion/refinement stats for timeout analysis.
# 3. Print a compact summary that will guide the next scored submission.

set -e

cd /home/user

mkdir -p /home/user/logs /home/user/tmp/results
exec > >(tee /home/user/logs/run.log) 2>&1

export PYTHONPATH="/home/user:$PYTHONPATH"
if [ -d "/dev/shm/pylibs" ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi

echo "=== EQuIPS Validation Run ==="
echo "Python: $(python3 --version)"

RESULTS_FILE="/home/user/tmp/results/equips_diagnostic.json"
rm -f "$RESULTS_FILE"

export EQUIPS_N_VALUES="5 20 50 100"
export EQUIPS_NUM_INSTANCES="1"
export EQUIPS_TIMEOUT_SECS="10.0"
export EQUIPS_INSTANCE_START="0"
export EQUIPS_SEED="42"
export EQUIPS_RESUME="0"
export EQUIPS_MIP_BACKEND="auto"

bash /home/user/scripts/method.sh "$RESULTS_FILE"

python3 - <<'PY'
import json
from pathlib import Path

path = Path("/home/user/tmp/results/equips_diagnostic.json")
payload = json.loads(path.read_text())
print("=== Diagnostic Summary ===")
for record in payload.get("results", []):
    stats = record.get("stats") or {}
    print(
        "n={n} status={status} runtime={runtime:.3f}s calls={calls} nested={nested} "
        "iters={iters} refs={refs} depth={depth} outer={outer} subgames={subgames} "
        "max_vars={max_vars} max_cons={max_cons}".format(
            n=record["n"],
            status=record["status"],
            runtime=record["runtime_s"],
            calls=stats.get("recursive_calls", 0),
            nested=stats.get("nested_solves", 0),
            iters=stats.get("abstraction_iterations", 0),
            refs=stats.get("refinements", 0),
            depth=stats.get("max_recursion_depth", 0),
            outer=stats.get("max_outer_vars", 0),
            subgames=stats.get("max_subgames", 0),
            max_vars=stats.get("max_problem_variables", 0),
            max_cons=stats.get("max_problem_constraints", 0),
        )
    )
PY

echo "=== DONE ==="
echo "Diagnostic results written to $RESULTS_FILE"
