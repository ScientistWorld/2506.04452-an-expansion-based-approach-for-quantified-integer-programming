#!/bin/bash
# Each named method uses this harness; hidden evaluation is a separate process.
set -euo pipefail
cd /home/user
case_name="$1"
folder="redteam/$case_name"
python3 -m redteam.execute_case "$case_name" > "$folder/method.log" 2>&1
# No arguments: discover ALL reports on disk using the restored gym entry point.
set +e
bash scripts/evaluate_test.sh > "$folder/hidden_test.log" 2>&1
test_exit=$?
set -e
printf '%s\n' "$test_exit" > "$folder/test_exit.txt"
if [ "$test_exit" -eq 0 ]; then
    cp scoring/scores_test.json "$folder/scores_test.json"
else
    # Preserve stale output separately; it is never counted as a successful run.
    if [ -f scoring/scores_test.json ]; then
        cp scoring/scores_test.json "$folder/stale_scores_after_failure.json"
    fi
fi
echo "$case_name hidden-test exit=$test_exit"
