#!/usr/bin/env python3
"""Run every audit case through the hidden-test evaluator (resumable, parallel).

Each case becomes a solver directory under outputs/audit/<case>/solver and is
scored by eval/test/evaluate.py exactly as a method on disk would be.  The
audit solvers (variant_solve.py, equips_copy.py, shortcuts.py, decoders.py and,
for the MCN decoder, a copy of the hidden generator module) are copied into
that directory, because the solver sandbox cannot read eval/test/.
Results: outputs/audit/<case>/{scores_test.json,details.json,log.txt,meta.json}.

Cases run concurrently (one evaluator process per case, each running its
solver one instance at a time); the instruction budget makes the results
independent of the machine's load.

Usage: python3 eval/test/audit/run_audit.py [--workers N] [CASE ...]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_DIR = HERE.parent
WORKSPACE = HERE.parents[2]
OUT = WORKSPACE / "outputs" / "audit"
AUDIT_FILES = ["variant_solve.py", "equips_copy.py", "shortcuts.py", "decoders.py"]

# (case, group, tool or None for a plain command, arguments, legacy evaluator, subset)
# tool: "V" variant_solve.py, "S" shortcuts.py, "D" decoders.py, "M" method/solve.py
CASES = [
    ("reference_rerun", "reference", "M", [], False, None),
    ("reference_seed1", "reference", "M", ["--solver-seed", "1"], False, None),
    ("reference_seed2", "reference", "M", ["--solver-seed", "2"], False, None),
    ("better_cpsat_gf2", "better", "V", ["cpsat_gf2"], False, None),
    ("better_cpsat_all", "better", "V", ["cpsat_all"], False, None),
    ("weaker_highs_only", "weaker", "V", ["highs_only"], False, None),
    ("weaker_short_timeout", "weaker", "V", ["short_timeout"], False, None),
    ("decoder_mcn", "shortcut", "D", ["mcn"], False, None),
    ("decoder_combined_strict", "shortcut", "D", ["combined_strict"], False, None),
    ("decoder_gf2_strict", "shortcut", "D", ["gf2_strict"], False, None),
    ("decoder_gf2", "shortcut", "D", ["gf2"], False, None),
    ("const_true", "shortcut", "S", ["const_true"], False, None),
    ("const_false", "shortcut", "S", ["const_false"], False, None),
    ("random_answer", "shortcut", "S", ["random"], False, None),
    ("forged_fields", "shortcut", "S", ["forged"], False, None),
    ("crash", "shortcut", "S", ["crash"], False, None),
    ("train_cache", "shortcut", "S", ["train_cache"], False, None),
    ("empty_slot", "shortcut", None, [], False, None),
    ("guess_true_on_timeout", "shortcut", "V", ["guess_true_on_timeout"], False, None),
    ("guess_false_on_timeout", "shortcut", "V", ["guess_false_on_timeout"], False, None),
    ("read_hidden", "shortcut", "S", ["read_hidden"], False, None),
    ("call_counter", "shortcut", "S", ["call_counter"], False, None),
    ("perf_disable", "shortcut_subset", "S", ["perf_disable"], False, "large"),
    ("detached_child", "shortcut_subset", "S", ["detached_child"], False, "large"),
    ("portfolio", "shortcut_subset", "S", ["portfolio"], False, "large"),
    # the same shortcuts scored without this round's isolation ("before")
    ("read_hidden_before", "shortcut_subset", "S", ["read_hidden"], True, "large"),
    ("call_counter_before", "shortcut_subset", "S", ["call_counter"], True, "large"),
]


def _subset_spec(kind: str) -> str:
    """'large': the three largest sizes of each ladder."""
    table = json.loads((TEST_DIR / "instances.json").read_text())
    parts = []
    for exp in ("qrandomparity_ladder", "mcn_ladder"):
        sizes = sorted(l["size"] for l in table["experiments"][exp]["levels"])
        parts.append(exp + ":" + ",".join(str(s) for s in sizes[-3:]))
    return ";".join(parts)


def _command(case: str, tool, args: list) -> list:
    rel = f"outputs/audit/{case}/solver"
    if tool == "M":
        return ["python3", "method/solve.py"] + args
    script = {"V": "variant_solve.py", "S": "shortcuts.py", "D": "decoders.py"}[tool]
    return ["python3", f"{rel}/{script}"] + args


def run_case(case, group, tool, args, legacy, subset, deadline) -> None:
    case_dir = OUT / case
    if (case_dir / "scores_test.json").exists():
        print(f"[audit] {case}: done, skipping", flush=True)
        return
    if time.time() > deadline:
        print(f"[audit] {case}: skipped (job time budget)", flush=True)
        return
    solver_dir = case_dir / "solver"
    solver_dir.mkdir(parents=True, exist_ok=True)
    command = None
    if tool is not None:
        for name in AUDIT_FILES:
            shutil.copy2(HERE / name, solver_dir / name)
        if tool == "D":
            shutil.copy2(TEST_DIR / "qip_hidden_gen.py", solver_dir / "qip_hidden_gen.py")
        command = _command(case, tool, args)
        (solver_dir / "solver.json").write_text(json.dumps({"name": case, "command": command}, indent=1))
    if "call_counter" in args:
        (OUT / ".call_counter.json").unlink(missing_ok=True)
    evaluator = ["python3", str(TEST_DIR / "evaluate.py")]
    if legacy or subset:
        evaluator = ["python3", str(HERE / "eval_variant.py")]
        if legacy:
            evaluator.append("--legacy")
        if subset:
            evaluator += ["--sizes", _subset_spec(subset)]
        evaluator.append("--")
    start = time.time()
    with (case_dir / "log.txt").open("w") as log:
        rc = subprocess.call(
            evaluator + [
                "--solver", str(solver_dir),
                "--scores-output", str(case_dir / "scores_test.json.tmp"),
                "--details-output", str(case_dir / "details.json"),
                "--checkpoint", str(case_dir / "checkpoint.json"),
            ],
            cwd=str(WORKSPACE), stdout=log, stderr=subprocess.STDOUT,
        )
    if rc == 0:
        (case_dir / "scores_test.json.tmp").rename(case_dir / "scores_test.json")
    meta = {"case": case, "group": group, "command": command, "legacy_evaluator": legacy, "subset": subset,
            "returncode": rc, "elapsed_s": round(time.time() - start, 1)}
    (case_dir / "meta.json").write_text(json.dumps(meta, indent=1))
    print(f"[audit] {case} ({group}): rc={rc} in {time.time() - start:.0f}s", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("cases", nargs="*")
    args = parser.parse_args()
    deadline = float(os.environ.get("QIP_AUDIT_DEADLINE", "inf"))
    todo = [c for c in CASES if not args.cases or c[0] in args.cases]
    # call_counter cases share one counter file: run them one after the other
    counters = [c for c in todo if "call_counter" in c[3]]
    others = [c for c in todo if "call_counter" not in c[3]]
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(run_case, *c, deadline) for c in others]
        futures.append(pool.submit(lambda: [run_case(*c, deadline) for c in counters]))
        for f in futures:
            f.result()


if __name__ == "__main__":
    sys.exit(main())
