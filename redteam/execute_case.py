"""Install saved outputs just as a future agent would before signalling done."""
from __future__ import annotations
import json
import shutil
import sys
from pathlib import Path

from redteam.benchmark import ROOT, load_method, save

case = sys.argv[1]
folder = ROOT / 'redteam' / case
active = ROOT / 'outputs' / 'redteam_active'
if active.exists():
    shutil.rmtree(active)
active.mkdir(parents=True)
module = load_method(case)
payloads = module.prepare()
if isinstance(payloads, dict):
    payloads = [payloads]
for index, payload in enumerate(payloads):
    save(active / f'{index:02d}_{case}.json', payload)
    save(folder / ('raw.json' if index == 0 else f'companion_{index}.json'), payload)
save(folder / 'installation.json', {
    'case': case, 'files': [str(p) for p in sorted(active.glob('*.json'))],
    'contract': 'no evaluator edits, no environment hooks, only persistent JSON output files',
})
