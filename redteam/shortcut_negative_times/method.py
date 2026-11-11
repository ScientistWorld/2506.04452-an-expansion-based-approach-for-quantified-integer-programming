"""Shortcut: impossible negative runtimes with unverified UNSAT statuses."""
from redteam.shortcut_helpers import shortcut_records

def prepare():
    return shortcut_records('UNSAT', -1.0)
