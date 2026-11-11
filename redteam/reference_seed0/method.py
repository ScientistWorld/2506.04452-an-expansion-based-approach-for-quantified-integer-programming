"""Reference CEGAR method, solver seed 0; benchmark seed remains 42."""
from redteam.benchmark import measure, seeded_reference

def prepare():
    return measure('reference_seed0', seeded_reference(0))
