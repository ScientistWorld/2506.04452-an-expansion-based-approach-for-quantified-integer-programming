#!/usr/bin/env python3
"""Audit-only wrapper around eval/test/evaluate.py (not used for scoring).

Usage: python3 eval/test/audit/eval_variant.py [--legacy] [--sizes SPEC] -- EVALUATOR_ARGS...

  --legacy       score without this round's isolation: the solver sandbox
                 installs no seccomp filter and no Landlock ruleset (the solver
                 can pause its performance counter, read eval/test/ and keep
                 files between runs), and instances run in table order instead
                 of a fresh random order.  Used to measure shortcuts "before".
  --sizes SPEC   only keep these ladder levels, e.g.
                 "mcn_ladder:24,28;qrandomparity_ladder:10,14" (empty list = none)

Used to measure a shortcut before and after an evaluator fix on the same
instances, without adding a switch to the evaluator itself.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALUATOR = HERE.parent / "evaluate.py"
WORKSPACE = HERE.parents[2]

LEGACY_SANDBOX = """import sys
sys.path.insert(0, {test_dir!r})
import sandbox as sb
sb.install_seccomp = lambda: True
sb.build_landlock_ruleset = lambda hidden, writable: None
sb.main()
"""


class _NoShuffle:
    def shuffle(self, seq) -> None:
        return None


def main() -> None:
    argv = sys.argv[1:]
    split = argv.index("--") if "--" in argv else len(argv)
    own, rest = argv[:split], argv[split + 1:]
    legacy = "--legacy" in own
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
        path = WORKSPACE / "outputs" / "audit" / "legacy_sandbox.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(LEGACY_SANDBOX.format(test_dir=str(HERE.parent)))
        ev.SANDBOX = path
        ev.random.SystemRandom = _NoShuffle
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
