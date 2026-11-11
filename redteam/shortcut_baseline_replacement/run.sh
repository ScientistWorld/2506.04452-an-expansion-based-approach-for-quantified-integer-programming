#!/bin/bash
set -euo pipefail
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
if [ -d /dev/shm/pylibs ]; then export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"; fi
if [ ! -f redteam/reference_seed0/raw.json ]; then bash redteam/reference_seed0/run.sh; fi
if [ ! -f redteam/exhaustive_baseline/raw.json ]; then bash redteam/exhaustive_baseline/run.sh; fi
bash redteam/run_case.sh shortcut_baseline_replacement
