"""Ablate the paper's optional existential relaxation initialization heuristic."""
from redteam.benchmark import measure, seeded_reference

def prepare():
    solve = seeded_reference(0)
    import method.equips as eq
    eq._existential_relaxation_move = lambda mg, time_limit_s=None: {v.name:v.lower for v in mg.outer_vars}
    return measure('ablation_no_relaxation', solve)
