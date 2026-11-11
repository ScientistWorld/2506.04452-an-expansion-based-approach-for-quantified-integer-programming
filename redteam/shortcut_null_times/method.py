"""Shortcut probe: null runtimes should never avoid a failed-run penalty."""
from redteam.shortcut_helpers import shortcut_records

def prepare():
    return shortcut_records('UNSAT',None)
