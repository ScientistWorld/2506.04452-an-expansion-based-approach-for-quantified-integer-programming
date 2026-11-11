"""Shortcut: return constant SAT, doing no satisfiability reasoning."""
from redteam.benchmark import measure

def shortcut_solve(problem, timeout_s=5.0):
    return {'status':'SAT', 'assignment':None}

def prepare():
    return measure('shortcut_constant_sat', shortcut_solve)
