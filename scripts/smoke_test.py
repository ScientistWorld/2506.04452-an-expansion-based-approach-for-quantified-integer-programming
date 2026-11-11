#!/usr/bin/env python3
"""Quick end-to-end check of method/ and baseline/ on small train instances.

Exits non-zero if a solver crashes or returns a wrong decision.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKSPACE))

import data.benchmark as bench  # noqa: E402


def main() -> int:
    table = json.loads((WORKSPACE / "data" / "train_instances.json").read_text())
    picks = []
    for exp, level_idx, inst_ids in (("qrandomparity_ladder", 0, range(8)), ("mcn_ladder", 0, range(4)), ("mcn_ladder", 3, range(2))):
        lvl = table["experiments"][exp]["levels"][level_idx]
        for j in inst_ids:
            picks.append((exp, lvl["size"], lvl["instances"][j]))
    status = 0
    env = dict(os.environ, QIP_CPU_BUDGET_S="10", PYTHONPATH=str(WORKSPACE))
    for solver in (["python3", "method/solve.py"], ["python3", "baseline/solve.py"]):
        for exp, size, spec in picks:
            text, truth = bench.materialize(exp, size, spec)
            with tempfile.TemporaryDirectory() as tmp:
                inst = Path(tmp) / "instance.qlp"
                ans = Path(tmp) / "answer.json"
                inst.write_text(text)
                start = time.time()
                proc = subprocess.run(solver + [str(inst), str(ans)], cwd=WORKSPACE, env=env, capture_output=True, text=True, timeout=60)
                answer = json.loads(ans.read_text())["answer"] if ans.exists() else None
            verdict = "ok"
            if proc.returncode != 0 or answer is None:
                verdict = "CRASH"
                status = 1
            elif answer in ("TRUE", "FALSE") and (answer == "TRUE") != truth:
                verdict = "WRONG"
                status = 1
            print(f"{solver[1]:<20} {exp:<22} size={size:<4} {spec['kind']:<12} truth={truth!s:<5} answer={answer} "
                  f"{time.time() - start:5.1f}s {verdict}", flush=True)
            if verdict == "CRASH":
                print(proc.stdout[-1500:], proc.stderr[-1500:], flush=True)
    return status


if __name__ == "__main__":
    sys.exit(main())
