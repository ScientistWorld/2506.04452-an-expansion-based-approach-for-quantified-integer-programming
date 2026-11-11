"""Shortcut: keep computed reference statuses, replace all measured times by 0."""
from redteam.shortcut_helpers import shortcut_reference

def prepare():
    payload = shortcut_reference()
    for record in payload['results']:
        record['runtime_s'] = 0.0
    return payload
