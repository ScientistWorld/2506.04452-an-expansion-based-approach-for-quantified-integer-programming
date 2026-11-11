"""Clearly weaker solver: original algorithm allowed only 1 ms per instance.
The benchmark timeout and scoring cap remain 5 s, preserving the fixed contract.
"""
from redteam.benchmark import measure, seeded_reference

def prepare():
    return measure('weaker_budget', seeded_reference(0), budget=0.001)
