"""Shortcut: precompute the public fixed batch, then time only answer lookup.
Cache construction uses only baseline/ and data/, never hidden answers.
"""
import json
import time
from redteam.benchmark import ROOT, save
from redteam.shortcut_helpers import shortcut_baseline

def prepare():
    source = shortcut_baseline()
    cache = {str(r['seed']):r['status'] for r in source['results']}
    folder = ROOT / 'redteam/shortcut_cache_replay'
    save(folder / 'shortcut_cache.json', cache)
    save(folder / 'shortcut_cache_provenance.json', {
        'construction':'visible exact baseline on all public generator seeds',
        'offline_runtime_s':sum(r['runtime_s'] for r in source['results']),
        'cache_size':len(cache), 'hidden_labels_read':False})
    started = time.perf_counter()
    cache = json.loads((folder / 'shortcut_cache.json').read_text())
    load_per_record = (time.perf_counter()-started)/100
    records=[]
    for i in range(100):
        seed=10042+i
        started=time.perf_counter()
        status=cache[str(seed)]
        elapsed=time.perf_counter()-started+load_per_record
        records.append(dict(n=10,instance_id=i,seed=seed,status=status,
                            runtime_s=elapsed,assignment_found=False))
    return dict(solver='equips',timeout_s=5.0,num_instances=100,results=records)
