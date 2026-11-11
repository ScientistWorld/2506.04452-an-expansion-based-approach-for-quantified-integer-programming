"""Shortcut: empty candidate report disappears while a valid baseline survives."""
from redteam.shortcut_helpers import shortcut_baseline

def prepare():
    return [dict(solver='equips',timeout_s=5.0,results=[]), shortcut_baseline()]
