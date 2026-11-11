#!/bin/bash
set -euo pipefail
cd /home/user
export PYTHONPATH="/home/user:${PYTHONPATH:-}"
if [ -d /dev/shm/pylibs ]; then export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"; fi
bash redteam/run_case.sh shortcut_constant_sat
