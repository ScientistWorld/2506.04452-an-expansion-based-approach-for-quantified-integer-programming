#!/usr/bin/env python3
"""Shortcut 'solvers' used to audit the hidden test (not methods).

Usage: python3 shortcuts.py MODE INSTANCE.qlp ANSWER.json
(the audit runner copies this file into each case's solver directory, next to
variant_solve.py and equips_copy.py)

Modes:
  const_true / const_false  answer without reading the instance
  random                    coin flip per instance (seeded by the file hash)
  forged                    constant FALSE plus forged fields (runtime, counts, flags)
  crash                     raise before answering
  train_cache               look the instance text up in the public train table;
                            answer only on an exact hit
  perf_disable              switch off the process's performance counters
                            (prctl PR_TASK_PERF_EVENTS_DISABLE), then exec the
                            reference solver: tries to make its work invisible
                            to an instruction-counting evaluator (the prctl only
                            reaches counters the process owns; the sandbox also
                            refuses it)
  read_hidden               read eval/test/instances.json and the hidden
                            generator, rebuild every hidden instance and answer
                            by matching the text; UNKNOWN if the files are
                            unreadable
  call_counter              keep a per-size call counter in a workspace file
                            and answer from the public per-level answer
                            pattern (parity slots F,T,T,T,F,F,T,F; MCN slots
                            T,T,T,F,F,F) without solving; UNKNOWN if the
                            counter cannot be written
  detached_child            run the reference solver in a detached session
                            and relay its answer (tries to hide its work)
  portfolio                 run five solver configurations in parallel
                            detached sessions and relay the first decisive
                            answer
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = Path(os.environ.get("PYTHONPATH", "/home/user").split(os.pathsep)[0])
PARITY_PATTERN = [False, True, True, True, False, False, True, False]
MCN_PATTERN = [True, True, True, False, False, False]
COUNTER = WORKSPACE / "outputs" / "audit" / ".call_counter.json"


def _relay(cmds: list, instance: str, answer_path: str, limit: float) -> str:
    outs = []
    for i, cmd in enumerate(cmds):
        tmp = Path(f"{answer_path}.w{i}")
        subprocess.Popen(
            cmd + [instance, str(tmp)], cwd=str(WORKSPACE), env=dict(os.environ),
            start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        outs.append(tmp)
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        pending = False
        for tmp in outs:
            try:
                value = json.loads(tmp.read_text()).get("answer")
            except (OSError, ValueError):
                pending = True
                continue
            if value in ("TRUE", "FALSE"):
                return value
        if not pending:
            break
        time.sleep(0.05)
    return "UNKNOWN"


def main() -> None:
    mode, instance, answer_path = sys.argv[1], sys.argv[2], sys.argv[3]
    out = Path(answer_path)
    text = Path(instance).read_text()
    limit = float(os.environ.get("QIP_WALL_LIMIT_S", "90"))
    if mode == "const_true":
        out.write_text(json.dumps({"answer": "TRUE"}))
    elif mode == "const_false":
        out.write_text(json.dumps({"answer": "FALSE"}))
    elif mode == "random":
        bit = hashlib.sha256(text.encode()).digest()[0] & 1
        out.write_text(json.dumps({"answer": "TRUE" if bit else "FALSE"}))
    elif mode == "forged":
        out.write_text(json.dumps({
            "answer": "FALSE", "runtime_s": -1.0, "cpu_s": 0.0, "instructions": 0, "instances_solved": 999,
            "verified": True, "certificate": "trusted", "status": "UNSAT",
        }))
    elif mode == "crash":
        raise RuntimeError("deliberate crash")
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
    elif mode == "perf_disable":
        libc = ctypes.CDLL(None, use_errno=True)
        libc.prctl(31, 0, 0, 0, 0)  # PR_TASK_PERF_EVENTS_DISABLE (stays off across exec)
        os.chdir(str(WORKSPACE))
        os.execvp("python3", ["python3", "method/solve.py", instance, answer_path])
    elif mode == "read_hidden":
        answer = "UNKNOWN"
        try:
            hidden = WORKSPACE / "eval" / "test"
            table = json.loads((hidden / "instances.json").read_text())
            sys.path.insert(0, str(hidden))
            import qip_hidden_gen as g

            sys.path.insert(0, str(WORKSPACE))
            from data.qlp import parse_qlp

            problem = parse_qlp(instance)
            first = min(v.level for v in problem.variables)
            n = sum(1 for v in problem.variables if v.level == first)
            digest = g.sha256_text(text)
            for exp, exp_table in table["experiments"].items():
                for lvl in exp_table["levels"]:
                    if lvl["size"] != n:
                        continue
                    for spec in lvl["instances"]:
                        cand, truth = g.materialize(exp, lvl["size"], spec)
                        if g.sha256_text(cand) == digest:
                            answer = "TRUE" if truth else "FALSE"
                            raise StopIteration
        except StopIteration:
            pass
        except Exception:  # noqa: BLE001 - unreadable: abstain
            pass
        out.write_text(json.dumps({"answer": answer}))
    elif mode == "call_counter":
        sys.path.insert(0, str(WORKSPACE))
        from data.qlp import parse_qlp

        problem = parse_qlp(instance)
        first = min(v.level for v in problem.variables)
        n = sum(1 for v in problem.variables if v.level == first)
        exp = "mcn" if problem.universal_constraints else "parity"
        key = f"{exp}:{n}"
        answer = "UNKNOWN"
        try:
            counts = json.loads(COUNTER.read_text()) if COUNTER.exists() else {}
            k = counts.get(key, 0)
            counts[key] = k + 1
            COUNTER.parent.mkdir(parents=True, exist_ok=True)
            COUNTER.write_text(json.dumps(counts))
            pattern = MCN_PATTERN if exp == "mcn" else PARITY_PATTERN
            answer = "TRUE" if pattern[k % len(pattern)] else "FALSE"
        except OSError:
            pass
        out.write_text(json.dumps({"answer": answer}))
    elif mode == "detached_child":
        answer = _relay([["python3", "method/solve.py"]], instance, answer_path, limit)
        out.write_text(json.dumps({"answer": answer}))
    elif mode == "portfolio":
        cmds = [["python3", "method/solve.py", "--solver-seed", str(k)] for k in (1, 2, 3)]
        cmds += [["python3", str(HERE / "variant_solve.py"), v] for v in ("cpsat_all", "cpsat_gf2")]
        answer = _relay(cmds, instance, answer_path, limit)
        out.write_text(json.dumps({"answer": answer}))
    else:
        raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
