"""Shortcut: fail every task but choose a zero reported timeout/capping value."""
from redteam.shortcut_helpers import shortcut_records

def prepare():
    return shortcut_records('TIMEOUT', 0.0, timeout=0.0)
