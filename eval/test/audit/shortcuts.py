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
"""

from __future__ import annotations

import hashlib
import json
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
    else:
        raise SystemExit(f"unknown mode {mode}")


if __name__ == "__main__":
    main()
