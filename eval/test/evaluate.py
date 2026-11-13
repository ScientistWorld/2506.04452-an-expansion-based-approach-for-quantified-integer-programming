#!/usr/bin/env python3
"""
Hidden-test evaluator for quantified-integer-programming solvers.

The evaluator runs every solver on disk itself, one hidden instance at a time,
and scores only what it observes:

* Instances are QIP decision problems in QLP format, regenerated here from
  hidden seeds (``instances.json``) by this directory's own generator copy and
  checked against one stored text digest per level.  The answers live only in
  this folder, which the solver cannot read while it runs.
* Each solver is a directory with a ``solver.json`` manifest
  (``{"name": ..., "command": [...]}``).  The evaluator calls
  ``command + [instance.qlp, answer.json]`` from the workspace root inside the
  sandbox of ``sandbox.py`` and reads ``{"answer": "TRUE" | "FALSE" | "UNKNOWN"}``.
* Budget: ``BUDGET_INSTRUCTIONS`` user-space instructions per instance,
  counted by a hardware counter over the solver's whole process tree (threads,
  children, detached descendants).  The count does not depend on the speed or
  load of the machine, so a rerun anywhere gives the same result.  The tree is
  killed when it passes the budget; a wall-clock watchdog (``WALL_LIMIT_S``)
  only guards against solvers that wait instead of computing.
* An instance counts as solved only if the solver finished within the budget
  and its decision is correct.  Any wrong decision fails the whole run: the
  solver then scores the worst value (0) in every experiment.  A
  missing/invalid manifest also scores 0, so a method that is absent never
  ties a working one.  An answer left by a solver that was killed (budget or
  watchdog) is ignored.
* Instances of a level are run in an order drawn at random for every
  evaluation; the solver may write only inside its private working directory,
  which is deleted after the instance, so nothing carries over between runs.
* Each experiment is a size ladder.  After two consecutive levels with no
  solved instance, the remaining (larger) levels are counted as unsolved
  without running them.

Default solver slots (no ``--solver`` argument): ``method/`` (always scored,
even if broken), ``baseline/`` and every directory under ``methods/``.
Solvers are evaluated concurrently (each one instance at a time); the
counted budget makes this independent of the machine's load.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
sys.path.insert(0, str(HERE))

import qip_hidden_gen as gen  # noqa: E402

TABLE_PATH = HERE / "instances.json"
SANDBOX = HERE / "sandbox.py"
EXPERIMENTS = ("qrandomparity_ladder", "mcn_ladder")
METRIC = "instances_solved"
BUDGET_INSTRUCTIONS = 60_000_000_000
WALL_LIMIT_S = 90.0
CPU_LIMIT_S = 120
ZERO_LEVELS_BEFORE_STOP = 2
MAX_ANSWER_BYTES = 1_000_000
MAX_WORKERS = 8
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
    return text


def load_ladders() -> dict:
    table = json.loads(TABLE_PATH.read_text())
    ladders = {}
    for exp in EXPERIMENTS:
        levels = []
        for lvl in sorted(table["experiments"][exp]["levels"], key=lambda l: l["size"]):
            items = []
            digest = hashlib.sha256()
            for spec in lvl["instances"]:
                text = materialize(exp, lvl["size"], spec)
                digest.update(gen.sha256_text(text).encode())
                items.append((text, bool(spec["answer"])))
            if digest.hexdigest() != lvl["digest"]:
                raise RuntimeError(f"instance text drifted: {exp} size={lvl['size']}")
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


def solver_env(run_dir: Path) -> dict:
    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(run_dir),
        "TMPDIR": str(run_dir),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONPATH": str(WORKSPACE),
        "PYTHONHASHSEED": "0",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "QIP_INSTRUCTION_BUDGET": str(BUDGET_INSTRUCTIONS),
        "QIP_WALL_LIMIT_S": str(WALL_LIMIT_S),
    }
    if os.environ.get("LD_LIBRARY_PATH"):
        env["LD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]
    return env


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


def run_instance(command: list, text: str, scratch: Path) -> dict:
    run_dir = Path(tempfile.mkdtemp(prefix="run_", dir=str(scratch)))
    try:
        instance = run_dir / "instance.qlp"
        answer_path = run_dir / "answer.json"
        log_path = scratch / (run_dir.name + ".log")
        instance.write_text(text)
        job = {
            "command": command + [str(instance), str(answer_path)],
            "cwd": str(WORKSPACE),
            "env": solver_env(run_dir),
            "log": str(log_path),
            "budget": BUDGET_INSTRUCTIONS,
            "wall_limit_s": WALL_LIMIT_S,
            "cpu_limit_s": CPU_LIMIT_S,
            "hide": [str(HERE), str(scratch)],
            "writable": [str(run_dir)],
        }
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(SANDBOX)], input=json.dumps(job), capture_output=True, text=True,
                timeout=WALL_LIMIT_S + 120,
            )
            lines = [l for l in proc.stdout.splitlines() if l.strip()]
            res = json.loads(lines[-1]) if lines else None
        except (subprocess.TimeoutExpired, ValueError, OSError):
            res = None
        if not isinstance(res, dict) or not isinstance(res.get("instructions"), int):
            return {"error": "sandbox failed", "instructions": None, "answer": None}
        finished = not res["over_budget"] and not res["wall_killed"]
        res["answer"] = _read_answer(answer_path) if finished else None
        if res["answer"] is None:
            try:
                res["log_tail"] = log_path.read_bytes()[-300:].decode("utf-8", "replace")
            except OSError:
                pass
        return res
    finally:
        shutil.rmtree(run_dir, ignore_errors=True)
        try:
            (scratch / (run_dir.name + ".log")).unlink()
        except OSError:
            pass


# --------------------------------------------------------------------------
# Scoring one solver
# --------------------------------------------------------------------------


class Checkpoint:
    """Optional per-level progress file so an interrupted evaluation resumes
    where it stopped (the same instances; only finished levels are reused)."""

    _lock = threading.Lock()

    def __init__(self, path):
        self.path = Path(path) if path else None
        self.data = {}
        if self.path and self.path.exists():
            self.data = json.loads(self.path.read_text())

    def get(self, key):
        return self.data.get(key)

    def put(self, key, value) -> None:
        if self.path:
            with self._lock:
                self.data[key] = value
                self.path.parent.mkdir(parents=True, exist_ok=True)
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps(self.data))
                tmp.replace(self.path)


def _record(out: dict, truth: bool) -> dict:
    """Per-instance record (no instance identity, no answer)."""
    rec = {
        "instructions": out.get("instructions"),
        "correct": None if out.get("answer") is None else out["answer"] == truth,
        "over_budget": out.get("over_budget"),
        "wall_killed": out.get("wall_killed"),
        "cpu_s": out.get("cpu_s"),
        "wall_s": out.get("wall_s"),
        "mode": out.get("mode"),
    }
    if out.get("error"):
        rec["error"] = out["error"]
    if out.get("log_tail") and out.get("answer") is None and not out.get("over_budget"):
        rec["log_tail"] = out["log_tail"][-200:]
    return rec


def evaluate_solver(name: str, command: list | None, error: str | None, ladders: dict, scratch: Path,
                    ckpt: Checkpoint | None = None, log=print) -> dict:
    worst = {exp: 0 for exp in EXPERIMENTS}
    ckpt = ckpt or Checkpoint(None)
    if command is None:
        return {"name": name, "failed": True, "reason": error, "metrics": worst, "levels": {}}
    if ckpt.get(f"{name}|failed"):
        reason = ckpt.get(f"{name}|failed")
        log(f"  {name}: {reason} -> run failed (resumed)")
        return {"name": name, "failed": True, "reason": reason, "metrics": worst, "levels": {}}
    rng = random.SystemRandom()
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
            done = ckpt.get(f"{name}|{exp}|{size}")
            if done is not None and done.get("of") == len(items):
                levels_out[exp].append(done)
                log(f"  {name}: {exp} size={size}: {done['solved']}/{len(items)} solved (resumed)")
                solved_total += done["solved"]
                zero_streak = zero_streak + 1 if done["solved"] == 0 else 0
                continue
            order = list(range(len(items)))
            rng.shuffle(order)
            records: list = [None] * len(items)
            solved = 0
            for idx in order:
                text, truth = items[idx]
                out = run_instance(command, text, scratch)
                records[idx] = _record(out, truth)
                if out.get("answer") is None:
                    continue
                if out["answer"] != truth:
                    reason = f"wrong decision on {exp} at size {size}"
                    log(f"  {name}: {reason} -> run failed")
                    ckpt.put(f"{name}|failed", reason)
                    return {"name": name, "failed": True, "reason": reason, "metrics": worst, "levels": levels_out}
                solved += 1
            counts = [r["instructions"] for r in records if r["instructions"] is not None]
            record = {
                "size": size, "solved": solved, "of": len(items),
                "instructions_total": sum(counts), "modes": sorted({r["mode"] for r in records if r.get("mode")}),
                "instances": records,
            }
            levels_out[exp].append(record)
            ckpt.put(f"{name}|{exp}|{size}", record)
            note = ""
            if any(r.get("error") for r in records):
                note += " [sandbox errors]"
            if "cpu" in record["modes"]:
                note += " [no instruction counter: CPU-time fallback]"
            log(f"  {name}: {exp} size={size}: {solved}/{len(items)} solved{note}")
            solved_total += solved
            zero_streak = zero_streak + 1 if solved == 0 else 0
        metrics[exp] = solved_total
    return {"name": name, "failed": False, "reason": None, "metrics": metrics, "levels": levels_out}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--solver", action="append", default=[], help="Solver directory (repeatable).")
    parser.add_argument("--scores-output", default=str(WORKSPACE / "scoring" / "scores_test.json"))
    parser.add_argument("--details-output", default=None, help="Optional per-level diagnostics JSON.")
    parser.add_argument("--checkpoint", default=None, help="Optional per-level progress file (resume after interruption).")
    args = parser.parse_args()

    ladders = load_ladders()
    slots = [Path(s).resolve() for s in args.solver] if args.solver else default_slots()

    entries = []
    taken: set = set()
    for slot in slots:
        name, command, error = read_manifest(slot)
        key = name
        suffix = 2
        while key in taken:
            key = f"{name}_{suffix}"
            suffix += 1
        taken.add(key)
        entries.append((key, slot, command, error))

    print_lock = threading.Lock()

    def log(msg: str) -> None:
        with print_lock:
            print(msg, flush=True)

    scratch = Path(tempfile.mkdtemp(prefix="qip_eval_"))
    ckpt = Checkpoint(args.checkpoint)
    results: dict = {}
    details: dict = {}
    try:
        def work(entry):
            key, slot, command, error = entry
            log(f"Evaluating {key} ({slot})")
            res = evaluate_solver(key, command, error, ladders, scratch, ckpt, log)
            log(f"  {key}: {res['metrics']}" + (f" (FAILED: {res['reason']})" if res["failed"] else ""))
            return key, slot, res

        workers = max(1, min(MAX_WORKERS, len(entries), len(os.sched_getaffinity(0))))
        threads_out: dict = {}
        errors: list = []
        sem = threading.Semaphore(workers)

        def guarded(entry):
            with sem:
                try:
                    key, slot, res = work(entry)
                    threads_out[key] = (slot, res)
                except BaseException as exc:  # noqa: BLE001 - re-raised below
                    errors.append(exc)

        threads = [threading.Thread(target=guarded, args=(e,)) for e in entries]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if errors:
            raise errors[0]
        for key, slot, _command, _error in entries:
            slot_, res = threads_out[key]
            results[key] = res["metrics"]
            details[key] = {k: v for k, v in res.items() if k != "metrics"} | {"metrics": res["metrics"], "slot": str(slot_)}
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

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
        dpath.write_text(json.dumps({"budget_instructions": BUDGET_INSTRUCTIONS, "solvers": details}, indent=1) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
