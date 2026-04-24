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
from method.equips import solve_qip

# Re-export the solver solve function
# (solver is in method/equips.py)
__all__ = [
    'solve_qip',
    'QIPProblem', 'Variable', 'Constraint', 'UniversalConstraint',
    'Subgame', 'MultiGame', 'generate_qrandomparity',
]
