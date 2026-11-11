"""Persistent-report shortcuts using only the public train-evaluator schema.

No hidden IDs, hidden scores, or hidden modules are read by these shortcuts.
All 100 IDs are emitted, so the train/test partition need not be known.
"""
from __future__ import annotations
import copy
import json
from pathlib import Path
from redteam.benchmark import ROOT


def shortcut_reference():
    # Reuse this audit's actual computation, available to an improve-mode agent.
    return json.loads((ROOT / 'redteam/reference_seed0/raw.json').read_text())


def shortcut_baseline():
    # Generated entirely using visible baseline/ and data/ in the baseline run.
    payload = json.loads((ROOT / 'redteam/exhaustive_baseline/raw.json').read_text())
    payload['solver'] = 'search_enumeration'
    return payload


def shortcut_records(status, runtime, timeout=5.0):
    return dict(solver='equips', timeout_s=timeout, num_instances=100, results=[
        dict(n=10, instance_id=i, seed=10042+i, status=status, runtime_s=runtime,
             assignment_found=False) for i in range(100)])
