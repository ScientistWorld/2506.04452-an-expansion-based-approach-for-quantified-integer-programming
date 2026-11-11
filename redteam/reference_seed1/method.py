"""Reference CEGAR method, solver seed 1; benchmark seed remains 42."""
from redteam.benchmark import measure, seeded_reference

def prepare():
    return measure('reference_seed1', seeded_reference(1))
