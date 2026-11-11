#!/bin/bash
# Reproduce the reference end to end and audit the hidden test (CPU job).
#
#   1. build/verify the instance tables (hidden test + public train); the MCN
#      ladder is extended once with exact ground truth (CEGAR, then bitmask
#      minimax for the largest sizes), then frozen
#   2. smoke test of method/ and baseline/
#   3. frozen reference: `bash scripts/evaluate_test.sh` with no arguments
#      (method/ + baseline/) -> scoring/scores_test.json
#   4. train split: `bash scripts/evaluate_train.sh` -> scoring/scores_train.json
#      (scoring/scores.json is the same protocol; copied)
#   5. audit cases (reference reruns, better/weaker variants, shortcuts)
#      through the hidden-test evaluator, then a summary in hardening/
# Every stage is skipped when its output already exists, and the evaluations
# checkpoint finished levels, so a killed job resumes where it stopped.

set -uo pipefail
cd /home/user
mkdir -p logs outputs/audit/reference_frozen
exec > >(tee -a logs/run.log) 2>&1
export PYTHONPATH="/home/user${PYTHONPATH:+:$PYTHONPATH}"
JOB_START=$(date +%s)
# stop starting new audit cases after 5 h 15 min so the job can finish cleanly
export QIP_AUDIT_DEADLINE=$((JOB_START + 18900))

echo "=== $(date -u) job start ==="
python3 - <<'PY'
import importlib, os
for name in ("numpy", "highspy", "ortools"):
    try:
        mod = importlib.import_module(name)
        print(name, getattr(mod, "__version__", "?"))
    except Exception as exc:
        print(name, "MISSING", exc)
print("cpus", os.cpu_count(), "affinity", len(os.sched_getaffinity(0)))
PY

echo "=== instance tables ==="
start=$(date +%s)
if ! QIP_GT_DEADLINE_S=${QIP_GT_DEADLINE_S:-4800} python3 eval/test/build_instances.py; then
    echo "instance build stopped abnormally: freezing the MCN extension as built"
    python3 eval/test/build_instances.py --freeze-extension || { echo "instance build/check failed"; exit 1; }
fi
echo "tables took $(( $(date +%s) - start ))s"

echo "=== smoke test ==="
python3 scripts/smoke_test.py || { echo "smoke test failed: aborting"; exit 1; }

if [ ! -f outputs/audit/reference_frozen/scores_test.json ]; then
    echo "=== frozen reference (hidden test, no arguments) ==="
    start=$(date +%s)
    QIP_DETAILS_OUTPUT=outputs/audit/reference_frozen/details.json \
    QIP_CHECKPOINT=outputs/audit/reference_frozen/checkpoint.json \
        bash scripts/evaluate_test.sh 2>&1 | tee outputs/audit/reference_frozen.log
    if [ "${PIPESTATUS[0]}" -eq 0 ]; then
        cp scoring/scores_test.json outputs/audit/reference_frozen/scores_test.json
    else
        echo "frozen reference evaluation failed"
    fi
    echo "frozen reference took $(( $(date +%s) - start ))s"
fi

if [ ! -f outputs/audit/train_done ]; then
    echo "=== train split (no arguments) ==="
    start=$(date +%s)
    QIP_DETAILS_OUTPUT=outputs/audit/train_details.json \
    QIP_CHECKPOINT=outputs/audit/train_checkpoint.json \
        bash scripts/evaluate_train.sh 2>&1 | tee outputs/audit/train.log \
        && cp scoring/scores_train.json scoring/scores.json && touch outputs/audit/train_done
    echo "train took $(( $(date +%s) - start ))s"
fi

echo "=== audit cases ==="
python3 eval/test/audit/run_audit.py

echo "=== analysis ==="
python3 eval/test/audit/analyze.py || true

mkdir -p hardening/logs
rm -f hardening/logs/*.log
cp outputs/audit/reference_frozen.log hardening/logs/ 2>/dev/null || true
cp outputs/audit/train.log hardening/logs/ 2>/dev/null || true
cp outputs/audit/train_details.json hardening/train_details.json 2>/dev/null || true
for d in outputs/audit/*/; do
    case=$(basename "$d")
    [ -f "$d/log.txt" ] && cp "$d/log.txt" "hardening/logs/${case}.log"
done
echo "=== $(date -u) done in $(( $(date +%s) - JOB_START ))s ==="
