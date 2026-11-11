#!/usr/bin/env python3
"""Run every audit case through the hidden-test evaluator (resumable).

Each case becomes a solver directory under outputs/audit/<case>/solver and is
scored by eval/test/evaluate.py exactly as a method on disk would be.
Results: outputs/audit/<case>/{scores_test.json,details.json,log.txt}.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
OUT = WORKSPACE / "outputs" / "audit"

V = ["python3", "eval/test/audit/variant_solve.py"]
S = ["python3", "eval/test/audit/shortcuts.py"]
D = ["python3", "eval/test/audit/decoders.py"]

# (case, group, command or None for an empty solver slot), in priority order
CASES = [
    ("const_true", "shortcut", S + ["const_true"]),
    ("const_false", "shortcut", S + ["const_false"]),
    ("random_answer", "shortcut", S + ["random"]),
    ("forged_fields", "shortcut", S + ["forged"]),
    ("crash", "shortcut", S + ["crash"]),
    ("train_cache", "shortcut", S + ["train_cache"]),
    ("empty_slot", "shortcut", None),
    ("decoder_gf2", "shortcut", D + ["gf2"]),
    ("decoder_combined", "shortcut", D + ["combined"]),
    ("reference_seed1", "reference", ["python3", "method/solve.py", "--solver-seed", "1"]),
    ("better_cpsat_gf2", "better", V + ["cpsat_gf2"]),
    ("weaker_highs_only", "weaker", V + ["highs_only"]),
    ("decoder_mcn", "shortcut", D + ["mcn"]),
    ("decoder_gf2_strict", "shortcut", D + ["gf2_strict"]),
    ("decoder_combined_strict", "shortcut", D + ["combined_strict"]),
    ("cpu_escape_before", "shortcut_subset", S + ["escape"]),
    ("cpu_escape", "shortcut_subset", S + ["escape"]),
    ("reference_seed2", "reference", ["python3", "method/solve.py", "--solver-seed", "2"]),
    ("better_cpsat_all", "better", V + ["cpsat_all"]),
    ("weaker_tenth_budget", "weaker", V + ["tenth_budget"]),
    ("guess_true_on_timeout", "shortcut", V + ["guess_true_on_timeout"]),
    ("guess_false_on_timeout", "shortcut", V + ["guess_false_on_timeout"]),
    ("cpu_portfolio_before", "shortcut_subset", S + ["escape_portfolio"]),
    ("cpu_portfolio", "shortcut_subset", S + ["escape_portfolio"]),
]

# Subset runs (escape probe): MCN levels from size 28 up, scored by the
# evaluator with and without the CPU-accounting fix (eval_variant.py).
# (wrapper flags, smallest MCN size in the subset)
WRAPPED = {
    "cpu_escape_before": (["--legacy-cpu"], 28),
    "cpu_escape": ([], 28),
    "cpu_portfolio_before": (["--legacy-cpu"], 40),
    "cpu_portfolio": ([], 40),
}

# Results of the previous audit job (same instances on every level they cover):
# finished levels are reused through the evaluator's checkpoint, so only
# levels added since then are run.  Subset cases listed here are copied as is.
PREVIOUS = OUT.parent / "audit_job1"
COPY_AS_IS = {"cpu_escape_before", "cpu_escape"}


def _subset_spec(min_size: int) -> str:
    table = json.loads((WORKSPACE / "eval" / "test" / "instances.json").read_text())
    sizes = [l["size"] for l in table["experiments"]["mcn_ladder"]["levels"] if l["size"] >= min_size]
    return "mcn_ladder:" + ",".join(str(s) for s in sizes) + ";qrandomparity_ladder:"


def _seed_checkpoint(case: str, ckpt_path: Path) -> None:
    details_path = PREVIOUS / case / "details.json"
    if ckpt_path.exists() or not details_path.exists():
        return
    data = {}
    for name, detail in json.loads(details_path.read_text()).items():
        if detail.get("failed"):
            data[f"{name}|failed"] = detail.get("reason")
            continue
        for exp, levels in detail.get("levels", {}).items():
            for record in levels:
                if not record.get("skipped") and "of" in record:
                    data[f"{name}|{exp}|{record['size']}"] = record
    ckpt_path.write_text(json.dumps(data))


def main() -> None:
    only = set(sys.argv[1:])
    deadline = float(os.environ.get("QIP_AUDIT_DEADLINE", "inf"))
    for case, group, command in CASES:
        if only and case not in only:
            continue
        if time.time() > deadline:
            print(f"[audit] {case}: skipped (job time budget)", flush=True)
            continue
        case_dir = OUT / case
        if (case_dir / "scores_test.json").exists():
            print(f"[audit] {case}: done, skipping", flush=True)
            continue
        if case in COPY_AS_IS and (PREVIOUS / case / "scores_test.json").exists():
            shutil.copytree(PREVIOUS / case, case_dir, dirs_exist_ok=True)
            print(f"[audit] {case}: copied from the previous audit job", flush=True)
            continue
        solver_dir = case_dir / "solver"
        solver_dir.mkdir(parents=True, exist_ok=True)
        _seed_checkpoint(case, case_dir / "checkpoint.json")
        if command is not None:
            (solver_dir / "solver.json").write_text(json.dumps({"name": case, "command": command}, indent=1))
        start = time.time()
        evaluator = ["python3", "eval/test/evaluate.py"]
        if case in WRAPPED:
            flags, min_size = WRAPPED[case]
            evaluator = ["python3", "eval/test/audit/eval_variant.py"] + flags + ["--sizes", _subset_spec(min_size), "--"]
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
        (case_dir / "meta.json").write_text(json.dumps({"case": case, "group": group, "command": command, "returncode": rc, "elapsed_s": round(time.time() - start, 1)}, indent=1))
        print(f"[audit] {case} ({group}): rc={rc} in {time.time() - start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
