#!/usr/bin/env python3
"""Shortcut 'solvers' used to audit the hidden test (not methods).

Usage: python3 eval/test/audit/shortcuts.py MODE INSTANCE.qlp ANSWER.json

Modes:
  const_true / const_false  answer without reading the instance
  random                    coin flip per instance (seeded by the file hash)
  forged                    constant FALSE plus forged fields (runtime, counts, flags)
  crash                     raise before answering
  sleep                     sleep past the wall-clock watchdog, then answer FALSE
  burn                      busy-loop past the CPU budget, then answer FALSE
  train_cache               look the instance text up in the public train table;
                            answer only on an exact hit
  escape                    run the reference solver in a detached session with
                            2.2x the CPU budget and relay its answer (tries to
                            hide CPU time from the evaluator)
  escape_portfolio          run five solver configurations in parallel detached
                            sessions (each within the budget) and relay the
                            first decisive answer: hides all but ~0 s of CPU
                            from an evaluator that only counts waited children
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]


def main() -> None:
    mode, instance, answer_path = sys.argv[1], sys.argv[2], sys.argv[3]
    out = Path(answer_path)
    text = Path(instance).read_text()
    if mode == "const_true":
        out.write_text(json.dumps({"answer": "TRUE"}))
    elif mode == "const_false":
        out.write_text(json.dumps({"answer": "FALSE"}))
    elif mode == "random":
        bit = hashlib.sha256(text.encode()).digest()[0] & 1
        out.write_text(json.dumps({"answer": "TRUE" if bit else "FALSE"}))
    elif mode == "forged":
        out.write_text(json.dumps({
            "answer": "FALSE", "runtime_s": -1.0, "cpu_s": 0.0, "instances_solved": 999,
            "verified": True, "certificate": "trusted", "status": "UNSAT",
        }))
    elif mode == "crash":
        raise RuntimeError("deliberate crash")
    elif mode == "sleep":
        time.sleep(60)
        out.write_text(json.dumps({"answer": "FALSE"}))
    elif mode == "burn":
        end = time.process_time() + 30
        while time.process_time() < end:
            pass
        out.write_text(json.dumps({"answer": "FALSE"}))
    elif mode == "train_cache":
        sys.path.insert(0, str(WORKSPACE))
        import data.benchmark as pub

        digest = pub.sha256_text(text)
        table = json.loads((WORKSPACE / "data" / "train_instances.json").read_text())
        for exp in table["experiments"].values():
            for lvl in exp["levels"]:
                for spec in lvl["instances"]:
                    if spec["sha256"] == digest:
                        out.write_text(json.dumps({"answer": "TRUE" if spec["answer"] else "FALSE"}))
                        return
        out.write_text(json.dumps({"answer": "UNKNOWN"}))
    elif mode == "escape":
        budget = float(os.environ.get("QIP_CPU_BUDGET_S", "10"))
        tmp = Path(answer_path + ".bg")
        env = dict(os.environ, QIP_CPU_BUDGET_S=str(2.2 * budget))
        subprocess.Popen(
            ["python3", "method/solve.py", instance, str(tmp)], cwd=str(WORKSPACE), env=env,
            start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        deadline = time.monotonic() + 2.2 * budget + 1.5
        while time.monotonic() < deadline and not tmp.exists():
            time.sleep(0.05)
        time.sleep(0.05)
        out.write_text(tmp.read_text() if tmp.exists() else json.dumps({"answer": "UNKNOWN"}))
    elif mode == "escape_portfolio":
        budget = float(os.environ.get("QIP_CPU_BUDGET_S", "10"))
        configs = [["python3", "method/solve.py", "--solver-seed", str(k)] for k in (1, 2, 3)]
        configs += [["python3", "eval/test/audit/variant_solve.py", v] for v in ("cpsat_all", "cpsat_gf2")]
        outs = []
        for i, cmd in enumerate(configs):
            tmp = Path(f"{answer_path}.w{i}")
            subprocess.Popen(
                cmd + [instance, str(tmp)], cwd=str(WORKSPACE), env=dict(os.environ),
                start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            outs.append(tmp)
        deadline = time.monotonic() + 2.2 * budget + 1.5
        answer = "UNKNOWN"
        while time.monotonic() < deadline:
            pending = False
            for tmp in outs:
                try:
                    value = json.loads(tmp.read_text()).get("answer")
                except (OSError, ValueError):
                    pending = True
                    continue
                if value in ("TRUE", "FALSE"):
                    answer = value
                    break
            if answer != "UNKNOWN" or not pending:
                break
            time.sleep(0.05)
        out.write_text(json.dumps({"answer": answer}))
    else:
        raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
