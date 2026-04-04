# EQuIPS method package
#
# Public API:
#   from method import solve_qip, solve_instance, generate_qrandomparity
#
# The solver is in method.equips
# The problem generator is in data.qrandomparity
from data.qrandomparity import (
    QIPProblem, Variable, Constraint, UniversalConstraint,
    Subgame, MultiGame, generate_qrandomparity
)

# Re-export the solver solve function
# (solver is in method/equips.py, imported via __import__ in eval)
__all__ = [
    'QIPProblem', 'Variable', 'Constraint', 'UniversalConstraint',
    'Subgame', 'MultiGame', 'generate_qrandomparity',
]
