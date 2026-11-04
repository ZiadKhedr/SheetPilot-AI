"""Navigation hints computed from current reviewed backend state."""
from .actions import fingerprint, procurement_readiness
from .analytics import records


def next_steps(store, workspace):
    store.workspace(workspace)
    books = [w for w in store.list(workspace, 'workbook') if w.get('active', True)]
    book_ids = {w['id'] for w in books}
    tables = [t for t in store.list(workspace, 'table') if t['workbook_id'] in book_ids]
    table_ids = {t['id'] for t in tables}
    pending = [t for t in tables if t['status'] not in {'confirmed', 'ignored'}]
    confirmed = {t['id']: t for t in tables if t['status'] == 'confirmed'}
    links = [r for r in store.list(workspace, 'relationship') if {r['left_table'], r['right_table']} <= table_ids]
    unresolved = [r for r in links if r['status'] != 'rejected' and (r['status'] != 'confirmed'
        or r['revisions'] != [confirmed.get(r['left_table'], {}).get('revision'), confirmed.get(r['right_table'], {}).get('revision')])]
    quality = store.list(workspace, 'quality')
    issues = [q for q in (quality[0]['issues'] if quality else []) if q.get('severity') == 'error']
    mirror = records(store, workspace)
    currency_gaps = {r['source']['table_id'] for r in mirror if r['entity'] in {'sales', 'inventory', 'suppliers'} and not r['data'].get('currency')}
    readiness = procurement_readiness(store, workspace)
    snapshot = fingerprint(store, workspace)
    runs = [r for r in store.list(workspace, 'run') if r['status'] == 'completed' and r.get('input_fingerprint') == snapshot]
    actions = [a for a in store.list(workspace, 'action') if a['status'] == 'pending']
    items = []
    def item(key, title, status, explanation, targets):
        items.append(dict(id=key, title=title, status=status, explanation=explanation, targets=targets))
    def target(label, href): return {'label':label, 'href':href}
    item('upload', 'Upload files', 'done' if books else 'ready',
         f'{len(books)} active workbook snapshots.' if books else 'Upload sales, stock or supplier Excel files to begin.',
         [target('Excel files', '/files')])
    item('mappings', 'Review mappings', 'blocked' if not books else 'ready' if pending or not tables else 'done',
         f'{len(pending)} tables still need explicit mapping review.' if pending else 'Select a table region first.' if books and not tables
         else 'Active tables have been reviewed or explicitly excluded.' if tables else 'Upload a workbook first.',
         [target(f"{t['sheet']} · {t['ref']}", '/mapping#table-'+t['id']) for t in pending] or
         [target('Mapping review' if tables else 'Select a region', '/mapping' if tables else '/structure')])
    relationships_ready = bool(confirmed) and not pending
    needs_discovery = len(confirmed) > 1 and not links
    item('relationships', 'Confirm relationships', 'blocked' if not relationships_ready else 'ready' if unresolved or needs_discovery else 'done',
         'Confirm the source mappings first.' if not relationships_ready else
         f'{len(unresolved)} relationships need review; shared identifiers never self-confirm.' if unresolved else
         'Discover shared identifiers, then review the proposed links.' if needs_discovery else
         'Current relationship decisions are reviewed; only confirmed exact links can support operations.',
         [target(r['field']+' relationship', '/mapping#relationship-'+r['id']) for r in unresolved] or [target('Review relationships', '/mapping#relationships')])
    blockers = issues or currency_gaps or readiness['blockers']
    item('quality', 'Resolve data blockers', 'blocked' if not confirmed else 'ready' if blockers else 'done',
         'Confirm a mapping to run data checks.' if not confirmed else
         f'{len(issues)} excluded/error rows, {len(currency_gaps)} tables needing currency, {len(readiness["blockers"])} purchasing prerequisites.' if blockers
         else 'No current row errors, missing commercial currencies or purchasing blockers were found.',
         [target('Review source issues', '/analytics#quality')] +
         [target('Review currency', '/mapping#table-'+t) for t in sorted(currency_gaps)] +
         [target(b['message'], '/mapping#table-'+b['inventory_table_id']) for b in readiness['blockers'][:20]])
    can_analyze = bool(mirror) and not pending
    item('analysis', 'Run analysis', 'done' if runs else 'ready' if can_analyze else 'blocked',
         'A completed job matches the current source and review fingerprint.' if runs else
         'Run a specialist job on the reviewed records. Purchasing checks explain any remaining blockers.' if can_analyze else
         'Review usable source tables before running an analysis.',
         [target('View latest current analysis', '/agents#run-'+runs[-1]['id'])] if runs else [target('Choose an agent job', '/agents')])
    item('proposals', 'Review purchase proposals', 'ready' if actions else 'done' if runs else 'blocked',
         f'{len(actions)} pending proposals require human review. Stale proposals must be regenerated.' if actions else
         'No pending purchase proposals. Generating a document never records incoming stock.' if runs else
         'Run purchase preparation after reviewing its prerequisites; approval is always separate.',
         [target('Review proposal '+a['id'][:8], '/approvals#action-'+a['id']) for a in actions] or [target('Approval center', '/approvals')])
    return {'fingerprint':snapshot, 'items':items}
