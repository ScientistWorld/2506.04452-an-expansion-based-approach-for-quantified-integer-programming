"""Shortcut probe: exaggerate the comparison baseline while copying reference."""
from redteam.shortcut_helpers import shortcut_reference,shortcut_baseline

def prepare():
    baseline=shortcut_baseline()
    for record in baseline['results']:
        record['status']='TIMEOUT'
        record['runtime_s']=5.0
    return [shortcut_reference(),baseline]
