#!/usr/bin/env python3
"""Run every audit case through the hidden-test evaluator (resumable).

Each case becomes a solver directory under outputs/audit/<case>/solver and is
scored by eval/test/evaluate.py exactly as a method on disk would be.
Results: outputs/audit/<case>/{scores_test.json,details.json,log.txt}.
"""

from __future__ import annotations

import json
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

# (case, group, command or None for an empty solver slot)
CASES = [
    ("const_true", "shortcut", S + ["const_true"]),
    ("const_false", "shortcut", S + ["const_false"]),
    ("random_answer", "shortcut", S + ["random"]),
    ("forged_fields", "shortcut", S + ["forged"]),
    ("crash", "shortcut", S + ["crash"]),
    ("train_cache", "shortcut", S + ["train_cache"]),
    ("empty_slot", "shortcut", None),
    ("decoder_gf2", "shortcut", D + ["gf2"]),
    ("decoder_mcn", "shortcut", D + ["mcn"]),
    ("decoder_combined", "shortcut", D + ["combined"]),
    ("reference_seed1", "reference", ["python3", "method/solve.py", "--solver-seed", "1"]),
    ("reference_seed2", "reference", ["python3", "method/solve.py", "--solver-seed", "2"]),
    ("better_gf2_presolve", "better", V + ["gf2_presolve"]),
    ("better_cpsat_all", "better", V + ["cpsat_all"]),
    ("better_cpsat_gf2", "better", V + ["cpsat_gf2"]),
    ("weaker_tenth_budget", "weaker", V + ["tenth_budget"]),
    ("weaker_lb_initial_move", "weaker", V + ["lb_initial_move"]),
    ("weaker_highs_only", "weaker", V + ["highs_only"]),
    ("guess_false_on_timeout", "shortcut", V + ["guess_false_on_timeout"]),
    ("guess_true_on_timeout", "shortcut", V + ["guess_true_on_timeout"]),
]


def main() -> None:
    only = set(sys.argv[1:])
    for case, group, command in CASES:
        if only and case not in only:
            continue
        case_dir = OUT / case
        if (case_dir / "scores_test.json").exists():
            print(f"[audit] {case}: done, skipping", flush=True)
            continue
        solver_dir = case_dir / "solver"
        solver_dir.mkdir(parents=True, exist_ok=True)
        if command is not None:
            (solver_dir / "solver.json").write_text(json.dumps({"name": case, "command": command}, indent=1))
        start = time.time()
        with (case_dir / "log.txt").open("w") as log:
            rc = subprocess.call(
                [
                    "python3", "eval/test/evaluate.py",
                    "--solver", str(solver_dir),
                    "--scores-output", str(case_dir / "scores_test.json.tmp"),
                    "--details-output", str(case_dir / "details.json"),
                ],
                cwd=str(WORKSPACE), stdout=log, stderr=subprocess.STDOUT,
            )
        if rc == 0:
            (case_dir / "scores_test.json.tmp").rename(case_dir / "scores_test.json")
        (case_dir / "meta.json").write_text(json.dumps({"case": case, "group": group, "command": command, "returncode": rc, "elapsed_s": round(time.time() - start, 1)}, indent=1))
        print(f"[audit] {case} ({group}): rc={rc} in {time.time() - start:.0f}s", flush=True)


if __name__ == "__main__":
    main()
