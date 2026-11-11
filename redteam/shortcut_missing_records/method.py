"""Shortcut probe: a partially missing batch should receive worst values."""
from redteam.shortcut_helpers import shortcut_records,shortcut_baseline

def prepare():
    payload=shortcut_records('UNSAT',0.0)
    payload['results']=payload['results'][:1]
    return [payload,shortcut_baseline()]
