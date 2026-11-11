#!/usr/bin/env python3
"""
Hidden-test evaluator for quantified-integer-programming solvers.

The evaluator runs every solver on disk itself, one hidden instance at a time,
and scores only what it observes:

* Instances are QIP decision problems in QLP format, regenerated here from
  hidden seeds (``instances.json``) by this directory's own generator copy and
  checked against stored text hashes.  The answers live only in this folder.
* Each solver is a directory with a ``solver.json`` manifest
  (``{"name": ..., "command": [...]}``).  The evaluator calls
  ``command + [instance.qlp, answer.json]`` from the workspace root with
  ``QIP_CPU_BUDGET_S`` in the environment, under a CPU-time limit and a
  wall-clock watchdog, and reads ``{"answer": "TRUE" | "FALSE" | "UNKNOWN"}``.
* An instance counts as solved only if the decision is correct and the solver
  process tree used at most the CPU budget (measured by the evaluator).
* Any wrong decisive answer fails the whole run: the solver then scores the
  worst value (0) in every experiment.  A missing/invalid manifest also scores
  the worst value, so a method that is absent never ties a working one.
* Each experiment is a size ladder.  After two consecutive levels with no
  solved instance, the remaining (larger) levels are counted as unsolved
  without running them.

Default solver slots (no ``--solver`` argument): ``method/`` (always scored,
even if broken), ``baseline/`` and every directory under ``methods/``.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
sys.path.insert(0, str(HERE))

import qip_hidden_gen as gen  # noqa: E402

TABLE_PATH = HERE / "instances.json"
EXPERIMENTS = ("qrandomparity_ladder", "mcn_ladder")
METRIC = "instances_solved"
CPU_BUDGET_S = 10.0
WALL_LIMIT_S = 2.0 * CPU_BUDGET_S + 5.0
ZERO_LEVELS_BEFORE_STOP = 2
MAX_ANSWER_BYTES = 1_000_000
NAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")


# --------------------------------------------------------------------------
# Instances
# --------------------------------------------------------------------------


def materialize(experiment: str, size: int, spec: dict) -> str:
    if experiment == "qrandomparity_ladder":
        text, answer = gen.parity_instance(size, spec["kind"], spec["seed"])
        if answer != bool(spec["answer"]):
            raise RuntimeError("hidden table answer disagrees with construction")
    elif experiment == "mcn_ladder":
        text = gen.mcn_instance(size, spec["seed"], spec["threshold"])
    else:
        raise RuntimeError(f"unknown experiment {experiment}")
    if gen.sha256_text(text) != spec["sha256"]:
        raise RuntimeError(f"instance text drifted: {experiment} size={size}")
    return text


def load_ladders() -> dict:
    table = json.loads(TABLE_PATH.read_text())
    ladders = {}
    for exp in EXPERIMENTS:
        levels = []
        for lvl in sorted(table["experiments"][exp]["levels"], key=lambda l: l["size"]):
            items = [(materialize(exp, lvl["size"], spec), bool(spec["answer"])) for spec in lvl["instances"]]
            levels.append((lvl["size"], items))
        ladders[exp] = levels
    return ladders


# --------------------------------------------------------------------------
# Solver discovery
# --------------------------------------------------------------------------


def default_slots() -> list[Path]:
    slots = [WORKSPACE / "method"]
    if (WORKSPACE / "baseline").is_dir():
        slots.append(WORKSPACE / "baseline")
    extra = WORKSPACE / "methods"
    if extra.is_dir():
        slots.extend(sorted(p for p in extra.iterdir() if p.is_dir()))
    return slots


def read_manifest(slot: Path) -> tuple[str, list | None, str | None]:
    fallback = slot.name if NAME_RE.match(slot.name) else "solver"
    path = slot / "solver.json"
    if not path.is_file():
        return fallback, None, "missing solver.json"
    try:
        manifest = json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        return fallback, None, f"unreadable solver.json: {exc}"
    if not isinstance(manifest, dict):
        return fallback, None, "solver.json is not an object"
    name = manifest.get("name", fallback)
    if not isinstance(name, str) or not NAME_RE.match(name):
        return fallback, None, "invalid solver name"
    command = manifest.get("command")
    if not isinstance(command, list) or not command or not all(isinstance(c, str) and c for c in command):
        return name, None, "invalid command"
    return name, command, None


# --------------------------------------------------------------------------
# Running one instance
# --------------------------------------------------------------------------


def _limits() -> None:
    soft = int(math.ceil(CPU_BUDGET_S)) + 1
    resource.setrlimit(resource.RLIMIT_CPU, (soft, soft + 1))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def _children_cpu() -> float:
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime


def _read_answer(path: Path):
    try:
        if not path.is_file() or path.stat().st_size > MAX_ANSWER_BYTES:
            return None
        data = json.loads(path.read_text())
    except Exception:  # noqa: BLE001
        return None
    value = data.get("answer") if isinstance(data, dict) else None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        token = value.strip().upper()
        if token in ("TRUE", "SAT"):
            return True
        if token in ("FALSE", "UNSAT"):
            return False
    return None


def run_instance(command: list, text: str) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="qip_eval_"))
    instance = tmp / "instance.qlp"
    answer_path = tmp / "answer.json"
    instance.write_text(text)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(WORKSPACE) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["QIP_CPU_BUDGET_S"] = str(CPU_BUDGET_S)
    log_path = tmp / "solver.log"
    cpu_before = _children_cpu()
    start = time.monotonic()
    killed = False
    try:
        with log_path.open("wb") as log:
            proc = subprocess.Popen(
                command + [str(instance), str(answer_path)],
                cwd=str(WORKSPACE),
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                preexec_fn=_limits,
            )
            try:
                proc.wait(timeout=WALL_LIMIT_S)
            except subprocess.TimeoutExpired:
                killed = True
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
                proc.wait()
        wall = time.monotonic() - start
        cpu = _children_cpu() - cpu_before
        answer = _read_answer(answer_path)
        tail = ""
        if answer is None:
            raw = log_path.read_bytes()[-400:]
            tail = raw.decode("utf-8", "replace")
        return {
            "answer": answer,
            "cpu_s": cpu,
            "wall_s": wall,
            "killed": killed,
            "returncode": proc.returncode,
            "log_tail": tail,
        }
    except OSError as exc:
        return {"answer": None, "cpu_s": 0.0, "wall_s": 0.0, "killed": False, "returncode": None, "log_tail": str(exc)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------
# Scoring one solver
# --------------------------------------------------------------------------


def evaluate_solver(name: str, command: list | None, error: str | None, ladders: dict) -> dict:
    worst = {exp: 0 for exp in EXPERIMENTS}
    if command is None:
        return {"name": name, "failed": True, "reason": error, "metrics": worst, "levels": {}}
    levels_out: dict = {}
    metrics: dict = {}
    for exp in EXPERIMENTS:
        solved_total = 0
        zero_streak = 0
        levels_out[exp] = []
        for size, items in ladders[exp]:
            if zero_streak >= ZERO_LEVELS_BEFORE_STOP:
                levels_out[exp].append({"size": size, "solved": 0, "skipped": True})
                continue
            solved = 0
            unknown = 0
            cpu_total = 0.0
            for text, truth in items:
                out = run_instance(command, text)
                cpu_total += out["cpu_s"]
                if out["answer"] is None:
                    unknown += 1
                    continue
                if out["answer"] != truth:
                    reason = f"wrong decision on {exp} at size {size}"
                    print(f"  {name}: {reason} -> run failed", flush=True)
                    return {"name": name, "failed": True, "reason": reason, "metrics": worst, "levels": levels_out}
                if out["cpu_s"] <= CPU_BUDGET_S and not out["killed"]:
                    solved += 1
            levels_out[exp].append(
                {"size": size, "solved": solved, "of": len(items), "no_answer": unknown, "cpu_s": round(cpu_total, 2)}
            )
            print(f"  {name}: {exp} size={size}: {solved}/{len(items)} solved", flush=True)
            solved_total += solved
            zero_streak = zero_streak + 1 if solved == 0 else 0
        metrics[exp] = solved_total
    return {"name": name, "failed": False, "reason": None, "metrics": metrics, "levels": levels_out}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--solver", action="append", default=[], help="Solver directory (repeatable).")
    parser.add_argument("--scores-output", default=str(WORKSPACE / "scoring" / "scores_test.json"))
    parser.add_argument("--details-output", default=None, help="Optional per-level diagnostics JSON.")
    args = parser.parse_args()

    ladders = load_ladders()
    slots = [Path(s).resolve() for s in args.solver] if args.solver else default_slots()

    results: dict = {}
    details: dict = {}
    for slot in slots:
        name, command, error = read_manifest(slot)
        key = name
        suffix = 2
        while key in results:
            key = f"{name}_{suffix}"
            suffix += 1
        print(f"Evaluating {key} ({slot})", flush=True)
        res = evaluate_solver(key, command, error, ladders)
        results[key] = res["metrics"]
        details[key] = {k: v for k, v in res.items() if k != "metrics"} | {"metrics": res["metrics"], "slot": str(slot)}
        print(f"  {key}: {res['metrics']}" + (f" (FAILED: {res['reason']})" if res["failed"] else ""), flush=True)

    scores = {
        "experiments": {
            exp: {"results": {name: {METRIC: metrics[exp]} for name, metrics in results.items()}}
            for exp in EXPERIMENTS
        }
    }
    out = Path(args.scores_output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scores, indent=2) + "\n")
    if args.details_output:
        dpath = Path(args.details_output)
        dpath.parent.mkdir(parents=True, exist_ok=True)
        dpath.write_text(json.dumps(details, indent=2) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
