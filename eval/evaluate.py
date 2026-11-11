"""Development evaluator: the train-split protocol, writing scoring/scores.json.

Thin wrapper around ``eval/train/evaluate.py`` (same instances, same rules).
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

if __name__ == "__main__":
    if "--scores-output" not in sys.argv:
        sys.argv += ["--scores-output", str(Path(__file__).resolve().parents[1] / "scoring" / "scores.json")]
    runpy.run_path(str(Path(__file__).resolve().parent / "train" / "evaluate.py"), run_name="__main__")
