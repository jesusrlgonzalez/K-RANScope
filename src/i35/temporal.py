"""Point-in-time access to published, approved maintenance metadata (not a causal explanation)."""
from .core import utc

def eligible_maintenance(window,cell_id,event_time,decision_time):
    e=utc(event_time);d=utc(decision_time);s=utc(window.get('start_utc'));end=utc(window.get('end_utc'));issued=utc(window.get('issued_at_utc'))
    if None in (e,d,s,end,issued):return False
    return (window.get('cell_id')==cell_id and window.get('approved')=='YES'
            and issued<=d and e<=d and s<=e<end)

