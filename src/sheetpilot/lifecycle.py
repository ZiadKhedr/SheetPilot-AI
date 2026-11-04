"""Shared active-snapshot and invalidation rules; historical sources remain stored."""
from .store import now


def active_workbooks(store, workspace, con=None):
    return [w for w in store.list(workspace, 'workbook', con) if w.get('active', True)]


def active_tables(store, workspace, con=None):
    ids = {w['id'] for w in active_workbooks(store, workspace, con)}
    return [t for t in store.list(workspace, 'table', con) if t['workbook_id'] in ids]


def invalidate_pending(store, workspace, reason, con):
    for action in store.list(workspace, 'action', con):
        if action['status'] == 'pending':
            action.update(status='conflicted', invalidated_at=now(), invalidation_reason=reason)
            action['validation'] = [*action['validation'], reason]
            store.put(workspace, 'action', action, con)
            store.event(workspace, 'action.conflicted', reason, {'action_id':action['id']}, con)
    for run in store.list(workspace, 'run', con):
        if run['status'] in {'completed','needs_review'}:
            run.update(stale=True, invalidated_at=now(), invalidation_reason=reason)
            store.put(workspace, 'run', run, con)
