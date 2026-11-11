#!/usr/bin/env python3
"""Solve one QIP decision instance by exhaustive enumeration (baseline).

Usage: python3 baseline/solve.py INSTANCE.qlp ANSWER.json
Writes {"answer": "TRUE" | "FALSE" | "UNKNOWN"} within QIP_CPU_BUDGET_S.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main() -> None:
    instance, answer_path = sys.argv[1], sys.argv[2]
    budget = float(os.environ.get("QIP_CPU_BUDGET_S", "10"))
    from baseline.enumerate import enumerate_baseline
    from data.qlp import parse_qlp

    problem = parse_qlp(instance)
    remaining = 0.92 * budget - time.process_time() - 0.2
    try:
        result = enumerate_baseline(problem, timeout_s=max(0.2, remaining))
        status = result["status"]
    except NotImplementedError:
        status = "UNKNOWN"
    answer = {"SAT": "TRUE", "UNSAT": "FALSE"}.get(status, "UNKNOWN")
    Path(answer_path).write_text(json.dumps({"answer": answer}) + "\n")


if __name__ == "__main__":
    main()
