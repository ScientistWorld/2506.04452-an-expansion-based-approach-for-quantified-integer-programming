"""Reference CEGAR method, solver seed 2; benchmark seed remains 42."""
from redteam.benchmark import measure, seeded_reference

def prepare():
    return measure('reference_seed2', seeded_reference(2))
