"""Run real solvers on the public, fixed batch. Never imports hidden eval code."""
from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path

ROOT = Path('/home/user')


def save(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False) + '\n')


def measure(case, solve, budget=5.0, preparation=None):
    from data.qrandomparity import generate_qrandomparity

    folder = ROOT / 'redteam' / case
    payload = dict(benchmark='qrandomparity', solver='equips', timeout_s=5.0,
                   n_values=[10], num_instances=100, results=[])
    if preparation:
        preparation()
    for i in range(100):
        seed = 42 + 1000 * 10 + i
        problem = generate_qrandomparity(n=10, seed=seed)
        started = time.perf_counter()
        try:
            answer = solve(problem, timeout_s=budget)
        except Exception as exc:
            answer = dict(status='ERROR', error=repr(exc))
        elapsed = time.perf_counter() - started
        record = dict(n=10, instance_id=i, seed=seed, status=answer['status'],
                      runtime_s=elapsed, assignment_found=answer.get('assignment') is not None,
                      stats=answer.get('stats'))
        if 'error' in answer:
            record['error'] = answer['error']
        payload['results'].append(record)
        save(folder / 'raw.json', payload)
        print(f'{case} {i:02d} {record["status"]} {elapsed:.6f}', flush=True)
    save(folder / 'provenance.json', dict(data_seed=42, seed_schedule='42+1000*n+instance_id',
                                         solver_budget_s=budget, reported_timeout_s=5.0,
                                         timing='perf_counter around actual solve, generation excluded as in reference'))
    return payload


def seeded_reference(seed):
    """Keep all inputs fixed; vary backend solver seeds, not benchmark seeds."""
    import method.equips as eq
    import os
    os.environ['EQUIPS_MIP_BACKEND'] = 'auto'
    if seed:
        original_highs = eq._new_highs
        original_cp = eq.cp_model.CpSolver

        def highs(time_limit_s=None):
            model = original_highs(time_limit_s)
            model.setOptionValue('random_seed', seed)
            return model

        def cp():
            solver = original_cp()
            solver.parameters.random_seed = seed
            return solver

        eq._new_highs = highs
        eq.cp_model.CpSolver = cp
    return eq.solve_qip


def load_method(case):
    path = ROOT / 'redteam' / case / 'method.py'
    spec = importlib.util.spec_from_file_location('audit_method', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
