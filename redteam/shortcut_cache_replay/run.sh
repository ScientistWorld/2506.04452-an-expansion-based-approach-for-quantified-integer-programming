#!/bin/bash
set -euo pipefail
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
if [ -d /dev/shm/pylibs ]; then export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"; fi
if [ ! -f redteam/exhaustive_baseline/raw.json ]; then bash redteam/exhaustive_baseline/run.sh; fi
bash redteam/run_case.sh shortcut_cache_replay
