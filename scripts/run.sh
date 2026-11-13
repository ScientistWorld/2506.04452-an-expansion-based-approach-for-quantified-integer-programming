#!/bin/bash
# Reproduce the reference end to end and (optionally) audit the hidden test (CPU job).
#
#   1. sandbox self-test: instruction counter, isolation (report only)
#   2. build/verify the instance tables (hidden test + public train); the MCN
#      ladder is built once with exact ground truth (bitmask minimax or CEGAR,
#      in parallel, cached in outputs/), then frozen
#   3. smoke tests of method/ and baseline/ (plain, then through the sandboxed
#      evaluator on the smallest levels)
#   4. frozen reference: `bash scripts/evaluate_test.sh` with no arguments
#      (method/ + baseline/) -> scoring/scores_test.json, and the train split
#      `bash scripts/evaluate_train.sh` -> scoring/scores_train.json
#      (scoring/scores.json is the same protocol; copied), run concurrently
#   5. only with QIP_RUN_AUDIT=1: audit cases (reference reruns, better/weaker
#      variants, shortcuts) through the hidden-test evaluator, in parallel,
#      then a summary in hardening/
# Every stage is skipped when its output already exists, and the evaluations
# checkpoint finished levels, so a killed job resumes where it stopped.  The
# instruction budget makes results independent of node speed and load.

set -uo pipefail
cd /home/user
mkdir -p logs outputs/audit/reference_frozen
exec > >(tee -a logs/run.log) 2>&1
export PYTHONPATH="/home/user${PYTHONPATH:+:$PYTHONPATH}"
JOB_START=$(date +%s)
# stop starting new audit cases after 5 h so the job can finish cleanly
export QIP_AUDIT_DEADLINE=$((JOB_START + 18000))
QIP_RUN_AUDIT=${QIP_RUN_AUDIT:-1}
export QIP_EXTEND_MCN=${QIP_EXTEND_MCN:-1}

echo "=== $(date -u) job start ==="
python3 - <<'PY'
import importlib, os, platform
for name in ("numpy", "highspy", "ortools"):
    try:
        mod = importlib.import_module(name)
        print(name, getattr(mod, "__version__", "?"))
    except Exception as exc:
        print(name, "MISSING", exc)
print("cpus", os.cpu_count(), "affinity", len(os.sched_getaffinity(0)))
try:
    print([l.split(":", 1)[1].strip() for l in open("/proc/cpuinfo") if l.startswith("model name")][0])
except Exception:
    pass
PY

echo "=== sandbox self-test ==="
python3 eval/test/audit/sandbox_check.py

echo "=== instance tables ==="
start=$(date +%s)
QIP_GT_DEADLINE_S=${QIP_GT_DEADLINE_S:-6000} python3 eval/test/build_instances.py ${QIP_EXTEND_MCN:+--extend-mcn} || { echo "instance build failed"; exit 1; }
echo "tables took $(( $(date +%s) - start ))s"

echo "=== smoke test ==="
python3 scripts/smoke_test.py || { echo "smoke test failed: aborting"; exit 1; }
MCN_MIN=$(python3 -c "import json; print(min(l['size'] for l in json.load(open('eval/test/instances.json'))['experiments']['mcn_ladder']['levels']))")
python3 eval/test/audit/eval_variant.py --sizes "qrandomparity_ladder:10;mcn_ladder:${MCN_MIN}" -- \
    --solver method --solver baseline --scores-output outputs/sandbox_smoke.json \
    --details-output outputs/sandbox_smoke_details.json || { echo "sandboxed smoke test crashed"; exit 1; }
python3 - <<'PY' || { echo "sandboxed smoke test: reference solved nothing, aborting"; exit 1; }
import json, sys
s = json.load(open("outputs/sandbox_smoke.json"))["experiments"]
solved = s["qrandomparity_ladder"]["results"]["equips"]["instances_solved"] + s["mcn_ladder"]["results"]["equips"]["instances_solved"]
print("sandboxed smoke: equips solved", solved, "of 14")
sys.exit(0 if solved >= 10 else 1)
PY

if [ ! -f outputs/audit/reference_frozen/scores_test.json ]; then
    (
    echo "=== frozen reference (hidden test, no arguments) ==="
    start=$(date +%s)
    QIP_DETAILS_OUTPUT=outputs/audit/reference_frozen/details.json \
    QIP_CHECKPOINT=outputs/audit/reference_frozen/checkpoint.json \
        bash scripts/evaluate_test.sh > outputs/audit/reference_frozen.log 2>&1
    if [ $? -eq 0 ]; then
        cp scoring/scores_test.json outputs/audit/reference_frozen/scores_test.json
    else
        echo "frozen reference evaluation failed"
    fi
    echo "frozen reference took $(( $(date +%s) - start ))s"
    ) &
fi
if [ ! -f outputs/audit/train_done ]; then
    (
    echo "=== train split (no arguments) ==="
    start=$(date +%s)
    QIP_DETAILS_OUTPUT=outputs/audit/train_details.json \
    QIP_CHECKPOINT=outputs/audit/train_checkpoint.json \
        bash scripts/evaluate_train.sh > outputs/audit/train.log 2>&1 \
        && cp scoring/scores_train.json scoring/scores.json && touch outputs/audit/train_done
    echo "train took $(( $(date +%s) - start ))s"
    ) &
fi

if [ "$QIP_RUN_AUDIT" = "1" ]; then
    echo "=== audit cases ==="
    python3 eval/test/audit/run_audit.py --workers 6
fi
wait
tail -n 40 outputs/audit/reference_frozen.log outputs/audit/train.log

if [ "$QIP_RUN_AUDIT" != "1" ]; then
    echo "=== $(date -u) reference reproduced in $(( $(date +%s) - JOB_START ))s (set QIP_RUN_AUDIT=1 for the audit) ==="
    exit 0
fi

echo "=== analysis ==="
python3 eval/test/audit/analyze.py || true

mkdir -p hardening/logs
rm -f hardening/logs/*.log
cp outputs/audit/reference_frozen.log hardening/logs/ 2>/dev/null || true
cp outputs/audit/train.log hardening/logs/ 2>/dev/null || true
for d in outputs/audit/*/; do
    case=$(basename "$d")
    [ -f "$d/log.txt" ] && cp "$d/log.txt" "hardening/logs/${case}.log"
done
echo "=== $(date -u) done in $(( $(date +%s) - JOB_START ))s ==="
