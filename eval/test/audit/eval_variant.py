#!/usr/bin/env python3
"""Audit-only wrapper around eval/test/evaluate.py (not used for scoring).

Usage: python3 eval/test/audit/eval_variant.py [--legacy-cpu] [--sizes SPEC] -- EVALUATOR_ARGS...

  --legacy-cpu   score with the pre-fix CPU accounting: no subreaper and no
                 reaping of detached descendants (their CPU time is not seen)
  --sizes SPEC   only keep these ladder levels, e.g.
                 "mcn_ladder:28,32,36;qrandomparity_ladder:" (empty list = none)

Used to measure a shortcut before and after an evaluator fix on the same
instances, without adding a switch to the evaluator itself.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALUATOR = HERE.parent / "evaluate.py"


def main() -> None:
    argv = sys.argv[1:]
    split = argv.index("--") if "--" in argv else len(argv)
    own, rest = argv[:split], argv[split + 1:]
    legacy = "--legacy-cpu" in own
    sizes = None
    if "--sizes" in own:
        spec = own[own.index("--sizes") + 1]
        sizes = {}
        for part in spec.split(";"):
            exp, _, vals = part.partition(":")
            sizes[exp] = {int(v) for v in vals.split(",") if v}

    module_spec = importlib.util.spec_from_file_location("hidden_evaluate", EVALUATOR)
    ev = importlib.util.module_from_spec(module_spec)
    sys.modules["hidden_evaluate"] = ev
    module_spec.loader.exec_module(ev)

    if legacy:
        ev._become_subreaper = lambda: None
        ev._reap_strays = lambda: None
    if sizes is not None:
        original = ev.load_ladders

        def subset():
            ladders = original()
            return {exp: [(s, items) for s, items in levels if s in sizes.get(exp, set())] for exp, levels in ladders.items()}

        ev.load_ladders = subset
        ev.ZERO_LEVELS_BEFORE_STOP = 10**6  # a subset ladder is scored level by level
    sys.argv = [str(EVALUATOR)] + rest
    ev.main()


if __name__ == "__main__":
    main()
