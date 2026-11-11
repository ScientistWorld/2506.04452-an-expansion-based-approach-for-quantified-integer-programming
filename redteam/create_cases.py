"""Author the standalone case scripts; no experiment computation is done here."""
from pathlib import Path
root = Path('/home/user/redteam')
cases = {}
for seed in range(3):
    cases[f'reference_seed{seed}'] = f'''"""Reference CEGAR method, solver seed {seed}; benchmark seed remains 42."""
from redteam.benchmark import measure, seeded_reference

def prepare():
    return measure('reference_seed{seed}', seeded_reference({seed}))
'''
cases['better_backend'] = '''"""Genuine implementation improvement: CP-SAT for every integer subproblem.
The original recursive CEGAR, counterexample checks, and expansion are retained.
"""
import os
from redteam.benchmark import measure

def prepare():
    import method.equips as eq
    os.environ['EQUIPS_MIP_BACKEND'] = 'cp-sat'
    eq._solve_ip_feasible = eq._solve_cp_sat_feasible
    return measure('better_backend', eq.solve_qip)
'''
cases['weaker_budget'] = '''"""Clearly weaker solver: original algorithm allowed only 1 ms per instance.
The benchmark timeout and scoring cap remain 5 s, preserving the fixed contract.
"""
from redteam.benchmark import measure, seeded_reference

def prepare():
    return measure('weaker_budget', seeded_reference(0), budget=0.001)
'''
cases['ablation_no_relaxation'] = '''"""Ablate the paper's optional existential relaxation initialization heuristic."""
from redteam.benchmark import measure, seeded_reference

def prepare():
    solve = seeded_reference(0)
    import method.equips as eq
    eq._existential_relaxation_move = lambda mg, time_limit_s=None: {v.name:v.lower for v in mg.outer_vars}
    return measure('ablation_no_relaxation', solve)
'''
cases['exhaustive_baseline'] = '''"""Exhaustively enumerate outer existential and universal assignments.
Inner feasibility is checked with the supplied exact IP baseline.
"""
from redteam.benchmark import measure

def prepare():
    from baseline.enumerate import enumerate_baseline
    return measure('exhaustive_baseline', enumerate_baseline)
'''
for status in ['SAT','UNSAT']:
    case = f'shortcut_constant_{status.lower()}'
    cases[case] = f'''"""Shortcut: return constant {status}, doing no satisfiability reasoning."""
from redteam.benchmark import measure

def shortcut_solve(problem, timeout_s=5.0):
    return {{'status':'{status}', 'assignment':None}}

def prepare():
    return measure('{case}', shortcut_solve)
'''
cases['shortcut_reported_zero'] = '''"""Shortcut: keep computed reference statuses, replace all measured times by 0."""
from redteam.shortcut_helpers import shortcut_reference

def prepare():
    payload = shortcut_reference()
    for record in payload['results']:
        record['runtime_s'] = 0.0
    return payload
'''
cases['shortcut_negative_times'] = '''"""Shortcut: impossible negative runtimes with unverified UNSAT statuses."""
from redteam.shortcut_helpers import shortcut_records

def prepare():
    return shortcut_records('UNSAT', -1.0)
'''
cases['shortcut_timeout_zero'] = '''"""Shortcut: fail every task but choose a zero reported timeout/capping value."""
from redteam.shortcut_helpers import shortcut_records

def prepare():
    return shortcut_records('TIMEOUT', 0.0, timeout=0.0)
'''
cases['shortcut_cache_replay'] = '''"""Shortcut: precompute the public fixed batch, then time only answer lookup.
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
'''
cases['shortcut_empty_results'] = '''"""Shortcut: empty candidate report disappears while a valid baseline survives."""
from redteam.shortcut_helpers import shortcut_baseline

def prepare():
    return [dict(solver='equips',timeout_s=5.0,results=[]), shortcut_baseline()]
'''
cases['shortcut_unscanned_results'] = '''"""Shortcut: save a genuine failed candidate outside evaluator discovery roots."""
from redteam.benchmark import ROOT,save
from redteam.shortcut_helpers import shortcut_baseline,shortcut_records

def prepare():
    save(ROOT/'redteam/shortcut_unscanned_results/shortcut_unscanned_candidate.json',
         shortcut_records('ERROR',5.0))
    return shortcut_baseline()
'''
cases['shortcut_missing_records'] = '''"""Shortcut probe: a partially missing batch should receive worst values."""
from redteam.shortcut_helpers import shortcut_records,shortcut_baseline

def prepare():
    payload=shortcut_records('UNSAT',0.0)
    payload['results']=payload['results'][:1]
    return [payload,shortcut_baseline()]
'''
cases['shortcut_null_times'] = '''"""Shortcut probe: null runtimes should never avoid a failed-run penalty."""
from redteam.shortcut_helpers import shortcut_records

def prepare():
    return shortcut_records('UNSAT',None)
'''
cases['shortcut_forged_aggregates'] = '''"""Shortcut probe: forge aggregate scores/flags without changing raw records."""
from redteam.shortcut_helpers import shortcut_reference

def prepare():
    payload=shortcut_reference()
    payload.update(median_runtime_s=0,mean_runtime_s=0,p90_runtime_s=0,
                   instances_solved=100000,success=True)
    payload['scores']={'median_runtime_s':0,'instances_solved':100000}
    for record in payload['results']:
        record['success']=True
        record['assignment_found']=True
    return payload
'''
cases['shortcut_baseline_replacement'] = '''"""Shortcut probe: exaggerate the comparison baseline while copying reference."""
from redteam.shortcut_helpers import shortcut_reference,shortcut_baseline

def prepare():
    baseline=shortcut_baseline()
    for record in baseline['results']:
        record['status']='TIMEOUT'
        record['runtime_s']=5.0
    return [shortcut_reference(),baseline]
'''
for case,source in cases.items():
    folder=root/case
    folder.mkdir(exist_ok=True)
    (folder/'method.py').write_text(source)
    dependencies=[]
    if case in {'shortcut_reported_zero','shortcut_forged_aggregates','shortcut_baseline_replacement'}:
        dependencies.append('reference_seed0')
    if case in {'shortcut_cache_replay','shortcut_empty_results','shortcut_unscanned_results','shortcut_missing_records','shortcut_baseline_replacement'}:
        dependencies.append('exhaustive_baseline')
    script='#!/bin/bash\nset -euo pipefail\ncd /home/user\nexport PYTHONPATH="/home/user:${PYTHONPATH:-}"\n'
    script+='if [ -d /dev/shm/pylibs ]; then export PYTHONPATH="/dev/shm/pylibs:$PYTHONPATH"; fi\n'
    for dep in dependencies:
        script+=f'if [ ! -f redteam/{dep}/raw.json ]; then bash redteam/{dep}/run.sh; fi\n'
    script+=f'bash redteam/run_case.sh {case}\n'
    (folder/'run.sh').write_text(script)
    (folder/'run.sh').chmod(0o755)
print(f'Created {len(cases)} runnable audit methods')
