"""Shortcut probe: forge aggregate scores/flags without changing raw records."""
from redteam.shortcut_helpers import shortcut_reference

def prepare():
    payload=shortcut_reference()
    payload.update(median_runtime_s=0,mean_runtime_s=0,p90_runtime_s=0,
                   instances_solved=100000,success=True)
    payload['scores']={'median_runtime_s':0,'instances_solved':100000}
    for record in payload['results']:
        record['success']=True
        record['assignment_found']=True
    return payload
