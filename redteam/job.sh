#!/bin/bash
# Single bundled CPU audit job. All actual solver work runs here, not on login.
set -euo pipefail
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
if [ -d /dev/shm/pylibs ]; then
    export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"
fi
mkdir -p redteam
exec > >(tee -a redteam/job.log) 2>&1
python3 - <<'PY'
import hashlib, importlib.metadata, json
from pathlib import Path
from datetime import datetime, timezone
expected=json.loads(Path('redteam/initial/hashes.json').read_text())
for p, digest in expected.items():
    assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==digest, p
versions={p: importlib.metadata.version(p) for p in ['numpy','highspy','ortools']}
Path('redteam/environment.json').write_text(json.dumps({'versions':versions,'started':str(datetime.now(timezone.utc))},indent=2))
print(versions, flush=True)
PY
for case_name in reference_seed0 reference_seed1 reference_seed2 better_backend weaker_budget ablation_no_relaxation exhaustive_baseline shortcut_constant_sat shortcut_constant_unsat shortcut_reported_zero shortcut_negative_times shortcut_timeout_zero shortcut_cache_replay shortcut_empty_results shortcut_unscanned_results shortcut_missing_records shortcut_null_times shortcut_forged_aggregates shortcut_baseline_replacement; do
    echo "Running $case_name"
    if [ -f "redteam/$case_name/test_exit.txt" ]; then
        echo "Already completed; retaining saved run"
    else
        bash "redteam/$case_name/run.sh"
    fi
done
python3 redteam/analyze.py
# Restore only paths written by the audit. Preserve the initial unrelated dirty state.
git restore --source="$(cat redteam/initial/base_commit.txt)" -- scripts/evaluate_test.sh eval scoring/scores_test.json scripts/run.sh
rm -rf outputs/redteam_active
rmdir outputs 2>/dev/null || true
echo 'Audit job complete; review redteam/summary.json and logs.'
