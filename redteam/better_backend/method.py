"""Genuine implementation improvement: CP-SAT for every integer subproblem.
The original recursive CEGAR, counterexample checks, and expansion are retained.
"""
import os
from redteam.benchmark import measure

def prepare():
    import method.equips as eq
    os.environ['EQUIPS_MIP_BACKEND'] = 'cp-sat'
    eq._solve_ip_feasible = eq._solve_cp_sat_feasible
    return measure('better_backend', eq.solve_qip)
