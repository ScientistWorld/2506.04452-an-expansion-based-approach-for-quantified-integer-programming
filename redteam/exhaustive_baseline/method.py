"""Exhaustively enumerate outer existential and universal assignments.
Inner feasibility is checked with the supplied exact IP baseline.
"""
from redteam.benchmark import measure

def prepare():
    from baseline.enumerate import enumerate_baseline
    return measure('exhaustive_baseline', enumerate_baseline)
