"""Shortcut: return constant UNSAT, doing no satisfiability reasoning."""
from redteam.benchmark import measure

def shortcut_solve(problem, timeout_s=5.0):
    return {'status':'UNSAT', 'assignment':None}

def prepare():
    return measure('shortcut_constant_unsat', shortcut_solve)
