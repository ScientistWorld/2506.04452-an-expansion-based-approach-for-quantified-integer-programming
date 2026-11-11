#!/bin/bash
# Hardening job: score the reference end to end and audit the hidden test.
#
#   1. verify instance tables (hidden test + public train) and generator parity
#   2. frozen reference: `bash scripts/evaluate_test.sh` with no arguments
#      (method/ + baseline/) -> scoring/scores_test.json
#   3. train split: `bash scripts/evaluate_train.sh` -> scoring/scores_train.json
#      (scoring/scores.json is the same protocol; copied)
#   4. audit cases (reruns, better/weaker variants, shortcuts) through the
#      hidden-test evaluator, then a summary in hardening/
# Every stage is skipped when its output already exists, so a killed job resumes.

set -uo pipefail
cd /home/user
mkdir -p logs outputs/audit
exec > >(tee -a logs/run.log) 2>&1
export PYTHONPATH="/home/user${PYTHONPATH:+:$PYTHONPATH}"

echo "=== $(date -u) hardening job ==="
python3 - <<'PY'
import importlib
for name in ("numpy", "highspy", "ortools"):
    try:
        mod = importlib.import_module(name)
        print(name, getattr(mod, "__version__", "?"))
    except Exception as exc:
        print(name, "MISSING", exc)
import os
print("cpus", os.cpu_count())
PY

python3 eval/test/build_instances.py || { echo "instance build/check failed"; exit 1; }

echo "=== smoke test ==="
python3 scripts/smoke_test.py || { echo "smoke test failed: aborting"; exit 1; }

if [ ! -f outputs/audit/reference_frozen/scores_test.json ]; then
    echo "=== frozen reference (hidden test, no arguments) ==="
    start=$(date +%s)
    bash scripts/evaluate_test.sh 2>&1 | tee outputs/audit/reference_frozen.log
    mkdir -p outputs/audit/reference_frozen
    cp scoring/scores_test.json outputs/audit/reference_frozen/scores_test.json
    echo "frozen reference took $(( $(date +%s) - start ))s"
fi

if [ ! -f outputs/audit/train_done ]; then
    echo "=== train split (no arguments) ==="
    start=$(date +%s)
    bash scripts/evaluate_train.sh 2>&1 | tee outputs/audit/train.log && cp scoring/scores_train.json scoring/scores.json && touch outputs/audit/train_done
    echo "train took $(( $(date +%s) - start ))s"
fi

echo "=== audit cases ==="
python3 eval/test/audit/run_audit.py

echo "=== analysis ==="
python3 eval/test/audit/analyze.py || true

mkdir -p hardening/logs
cp outputs/audit/reference_frozen.log hardening/logs/ 2>/dev/null || true
cp outputs/audit/train.log hardening/logs/ 2>/dev/null || true
for d in outputs/audit/*/; do
    case=$(basename "$d")
    [ -f "$d/log.txt" ] && cp "$d/log.txt" "hardening/logs/${case}.log"
done
echo "=== $(date -u) done ==="
