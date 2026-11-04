"""Bounded, approved cell interpretations in an append-only derived revision layer."""
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
import re
from typing import Literal

from openpyxl.utils import get_column_letter
from pydantic import Field

from .ingestion import digest
from .models import Model
from .semantics import IDENTIFIER_FIELDS, NUMERIC_FIELDS
from .store import Problem, now, uid

DATE_FIELDS={'sale_date','purchase_date','expected_date','payment_date'}
MODES=['decimal_dot','decimal_comma','thousands_comma','date_iso','date_dmy','date_mdy','identifier_exact']


class CellRepair(Model):
    table_id:str=Field(pattern='^[a-f0-9]{32}$')
    row:int=Field(ge=1,le=1_048_576)
    column:int=Field(ge=1,le=16_384)
    interpretation:Literal['decimal_dot','decimal_comma','thousands_comma','date_iso','date_dmy','date_mdy','identifier_exact']
    replacement:str|None=Field(default=None,max_length=180)
    reference_table_id:str|None=Field(default=None,pattern='^[a-f0-9]{32}$')


class RepairPreview(Model):
    expected_revision:int=Field(ge=0)
    expected_fingerprint:str=Field(pattern='^[a-f0-9]{64}$')
    repairs:list[CellRepair]=Field(min_length=1,max_length=20)


class RepairApproval(RepairPreview):
    preview_hash:str=Field(pattern='^[a-f0-9]{64}$')
    approved:bool=False


class RepairReversal(Model):
    expected_revision:int=Field(ge=1)
    expected_fingerprint:str=Field(pattern='^[a-f0-9]{64}$')
    approved:bool=False
    preview_hash:str|None=Field(default=None,pattern='^[a-f0-9]{64}$')


def correction_state(store,workspace,con=None):
    states=store.list(workspace,'correction_state',con)
    return states[0] if states else {'revision':0}


def overlays(store,workspace,table,con=None):
    """Physical source cells plus their reviewed field meaning identify an overlay."""
    workbook=store.get(workspace,'workbook',table['workbook_id'],con)
    return [r for r in sorted(store.list(workspace,'correction',con),key=lambda r:r['revision'])
            if r['table_id']==table['id'] and r['source_hash']==workbook['sha256']
            and table['fields'].get(str(r['column']))==r['field']]


def issue_id(issue):
    return sha256(json.dumps({k:issue.get(k) for k in ['table_id','row','code','message']},sort_keys=True).encode()).hexdigest()[:20]


def repair_workspace(store,workspace):
    from .actions import fingerprint
    from .mapping import source_rows
    store.workspace(workspace)
    tables={t['id']:t for t in store.list(workspace,'table')}
    books={w['id']:w for w in store.list(workspace,'workbook')}
    quality=store.list(workspace,'quality')
    issues=quality[0]['issues'] if quality else []
    issues=list(issues)
    # Relationship diagnostics are actionable even when a syntactically valid ID
    # has a different spelling. This is evidence only, never an automatic match.
    from .relationships import _key
    from .mapping import identifier
    for link in store.list(workspace,'relationship'):
        if link.get('match_mode')!='normalized-preview' or link.get('status')=='rejected':continue
        left,right=tables.get(link['left_table']),tables.get(link['right_table'])
        if not left or not right or any(t['status']!='confirmed' or not books[t['workbook_id']].get('active',True) for t in [left,right]):continue
        for table,other in [(left,right),(right,left)]:
            column=next((c for c,f in table['fields'].items() if f==link['field']),None)
            other_column=next((c for c,f in other['fields'].items() if f==link['field']),None)
            if not column or not other_column:continue
            targets={identifier(r['values'][other_column]['value']) for r in source_rows(store,workspace,other)}
            normalized={_key(value) for value in targets if value}
            for raw in source_rows(store,workspace,table)[:100]:
                value=identifier(raw['values'][column]['value'])
                if value and value not in targets and _key(value) in normalized:
                    issues.append({'table_id':table['id'],'workbook_id':table['workbook_id'],'sheet':table['sheet'],
                        'row':raw['row'],'severity':'warning','code':'identifier_reconciliation',
                        'message':'Identifier spelling differs from a reviewed table. Choose an exact reference before reconciling.'})
    result=[]
    cache={}
    for issue in issues[:500]:
        table=tables.get(issue['table_id'])
        if not table:continue
        if table['id'] not in cache:
            cache[table['id']]={r['row']:r for r in source_rows(store,workspace,table,original=True)}
        raw=cache[table['id']].get(issue['row'])
        cells=[]
        for col,field in table['fields'].items():
            if field=='ignore' or not raw:continue
            cell=raw['values'][col]
            modes=(MODES[:3] if field in NUMERIC_FIELDS else MODES[3:6] if field in DATE_FIELDS else
                   ['identifier_exact'] if field in IDENTIFIER_FIELDS else [])
            if cell['data_type'] in {'f','e'}:modes=[]
            cells.append({'column':int(col),'field':field,'cell':get_column_letter(int(col))+str(issue['row']),
                          'original_value':cell['value'],'interpretations':modes})
        result.append(issue|{'id':issue_id(issue),'workbook_name':books[table['workbook_id']]['name'],
                             'source_hash':books[table['workbook_id']]['sha256'],'cells':cells})
    return {'revision':correction_state(store,workspace)['revision'],'fingerprint':fingerprint(store,workspace),
            'issues':result,'issue_count':len(issues),'issues_truncated':len(issues)>500,
            'corrections':sorted(store.list(workspace,'correction'),key=lambda c:c['revision'],reverse=True)}


def _proposals(store,workspace,repairs,con):
    from .mapping import source_rows, identifier
    from .analytics import decimal_value, quoted_cost
    seen=set();result=[]
    for repair in repairs:
        table=store.get(workspace,'table',repair.table_id,con)
        workbook=store.get(workspace,'workbook',table['workbook_id'],con)
        if workbook.get('superseded_by') or table['status']!='confirmed':
            raise Problem('Corrections require a confirmed mapping on an active or candidate snapshot.')
        field=table['fields'].get(str(repair.column))
        key=(table['id'],repair.row,repair.column)
        if key in seen:raise Problem('Each source cell can be corrected once per request.')
        seen.add(key)
        path=store.root/'originals'/f"{workbook['id']}.xlsx"
        if not path.is_file() or digest(path)!=workbook['sha256']:
            raise Problem('Original workbook is missing or changed. Correction refused.',409)
        raw=next((r for r in source_rows(store,workspace,table,con,original=True) if r['row']==repair.row),None)
        effective=next((r for r in source_rows(store,workspace,table,con) if r['row']==repair.row),None)
        if not raw or str(repair.column) not in raw['values'] or not field or field=='ignore':
            raise Problem('Select a mapped source cell inside the reviewed data region.')
        original=raw['values'][str(repair.column)]
        current=effective['values'][str(repair.column)]
        if original['data_type'] in {'f','e'}:
            raise Problem('Formula/error cells require source review; corrections cannot execute or invent formula results.')
        value=str(current['value']).strip() if current['value'] is not None else ''
        mode=repair.interpretation
        reference=None
        if mode in MODES[:3]:
            if field not in NUMERIC_FIELDS:raise Problem('Numeric interpretations require a reviewed numeric meaning.')
            pattern={'decimal_dot':r'\d+(?:\.\d+)?','decimal_comma':r'\d+(?:,\d+)?',
                     'thousands_comma':r'\d{1,3}(?:,\d{3})+(?:\.\d+)?'}[mode]
            if not re.fullmatch(pattern,value):raise Problem('The original value does not match the selected numeric convention.')
            after=value.replace(',','.' if mode=='decimal_comma' else '')
            after=quoted_cost(after) if field=='unit_cost' else str(decimal_value(after,field))
        elif mode in MODES[3:6]:
            if field not in DATE_FIELDS:raise Problem('Date interpretations require a reviewed date meaning.')
            try:after=datetime.strptime(value,{'date_iso':'%Y-%m-%d','date_dmy':'%d/%m/%Y','date_mdy':'%m/%d/%Y'}[mode]).date().isoformat()
            except ValueError:raise Problem('The value does not match the selected date format.') from None
        else:
            if field not in IDENTIFIER_FIELDS or not repair.replacement or not repair.reference_table_id:
                raise Problem('Identifier reconciliation needs an exact replacement and a reviewed reference table.')
            after=identifier(repair.replacement)
            if not after:raise Problem('The reconciled identifier cannot be blank.')
            master=store.get(workspace,'table',repair.reference_table_id,con)
            master_book=store.get(workspace,'workbook',master['workbook_id'],con)
            master_path=store.root/'originals'/f"{master_book['id']}.xlsx"
            if not master_path.is_file() or digest(master_path)!=master_book['sha256']:
                raise Problem('The identifier reference workbook is missing or changed.',409)
            col=next((col for col,meaning in master['fields'].items() if meaning==field),None)
            if master['status']!='confirmed' or not col or master['id']==table['id'] or not master_book.get('active',True):
                raise Problem('Choose a different active, confirmed reference table with the same identifier meaning.')
            matches=[r for r in source_rows(store,workspace,master,con) if r['values'][col]['data_type'] not in {'f','e'} and identifier(r['values'][col]['value'])==after]
            if len(matches)!=1:raise Problem('The reference identifier must match exactly one reviewed source record.')
            reference={'table_id':master['id'],'workbook_id':master_book['id'],'sha256':master_book['sha256'],
                       'sheet':master['sheet'],'cell':get_column_letter(int(col))+str(matches[0]['row'])}
        if current['value']==after:raise Problem('This interpretation would not change the derived value.')
        result.append({'table_id':table['id'],'workbook_id':workbook['id'],'sheet':table['sheet'],'row':repair.row,
            'column':repair.column,'cell':get_column_letter(repair.column)+str(repair.row),'field':field,
            'original_value':original['value'],'before':current['value'],'after':after,'interpretation':mode,
            'source_hash':workbook['sha256'],'mapping_revision':table['revision'],'reference':reference})
    return result


def _apply(store,workspace,proposals,actor,con):
    from .analytics import materialize
    from .mapping import invalidate_relationships
    state=correction_state(store,workspace,con)
    revision=state['revision']+1
    saved=[]
    for value in proposals:
        saved.append(store.put(workspace,'correction',value|{'revision':revision,'approved_at':now(),'approved_by':actor},con))
        if value['field'] in IDENTIFIER_FIELDS:invalidate_relationships(store,workspace,value['table_id'],con)
    store.put(workspace,'correction_state',state|{'revision':revision},con)
    rows,issues=materialize(store,workspace,con)
    return saved,rows,issues


def _summary(rows):
    from .analytics import sales_metrics
    return {'records':len(rows),'inventory_units':str(sum((Decimal(r['data']['stock_quantity']) for r in rows if r['entity']=='inventory'),Decimal(0))),
            'revenue':sales_metrics([r['data'] for r in rows if r['entity']=='sales'])['revenue']}


def _simulate(store,workspace,proposals,body,con):
    from .analytics import materialize
    con.execute('SAVEPOINT repair_preview')
    try:
        before,old_issues=materialize(store,workspace,con)
        _,after,new_issues=_apply(store,workspace,proposals,'preview-only',con)
        def key(r):return (r['source']['table_id'],r['source']['row'])
        left={key(r):r['data'] for r in before};right={key(r):r['data'] for r in after}
        changed=[{'table_id':k[0],'row':k[1],'before':left.get(k),'after':right.get(k)} for k in sorted(left.keys()|right.keys()) if left.get(k)!=right.get(k)]
        value={'proposals':proposals,'before':_summary(before),'after':_summary(after),
               'issues_before':len(old_issues),'issues_after':len(new_issues),'affected_records':changed[:100],
               'affected_count':len(changed),'expected_revision':body.expected_revision,'fingerprint':body.expected_fingerprint,
               'relationships_need_review':any(p['field'] in IDENTIFIER_FIELDS for p in proposals)}
        value['preview_hash']=sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        return value
    finally:
        con.execute('ROLLBACK TO repair_preview');con.execute('RELEASE repair_preview')


def _check_revision(store,workspace,body,con):
    from .actions import fingerprint
    if correction_state(store,workspace,con)['revision']!=body.expected_revision or fingerprint(store,workspace,con)!=body.expected_fingerprint:
        raise Problem('Data or correction revision changed. Refresh and preview again.',409)


def _preview(store,workspace,body,con):
    _check_revision(store,workspace,body,con)
    return _simulate(store,workspace,_proposals(store,workspace,body.repairs,con),body,con)


def preview_repairs(store,workspace,body):
    with store.connection(immediate=True) as con:return _preview(store,workspace,body,con)


def approve_repairs(store,workspace,body,actor):
    from .lifecycle import invalidate_pending
    if not body.approved:raise Problem('Explicit human approval of the correction preview is required.')
    with store.connection(immediate=True) as con:
        result=_preview(store,workspace,body,con)
        if result['preview_hash']!=body.preview_hash:raise Problem('The correction preview changed. Preview again.',409)
        saved,_,_=_apply(store,workspace,result['proposals'],actor,con)
        invalidate_pending(store,workspace,'Approved data correction changed derived records. Rerun analyses and regenerate pending proposals.',con)
        store.event(workspace,'correction.approved','Approved derived corrections; original workbook cells preserved.',
                    {'revision':body.expected_revision+1,'corrections':saved,'preview':result,'actor':actor},con)
        return {'revision':body.expected_revision+1,'corrections':saved,'preview':result}


def _reversal(store,workspace,identifier,body,con):
    from .mapping import source_rows
    _check_revision(store,workspace,body,con)
    original=store.get(workspace,'correction',identifier,con)
    history=[c for c in store.list(workspace,'correction',con) if all(c[k]==original[k] for k in ['table_id','row','column'])]
    if max(history,key=lambda c:c['revision'])['id']!=identifier:
        raise Problem('A later correction already covers this cell. Reverse the latest revision first.',409)
    table=store.get(workspace,'table',original['table_id'],con)
    workbook=store.get(workspace,'workbook',original['workbook_id'],con)
    path=store.root/'originals'/f"{workbook['id']}.xlsx"
    if (workbook.get('superseded_by') or not path.is_file() or digest(path)!=original['source_hash']
            or table['status']!='confirmed' or table['fields'].get(str(original['column']))!=original['field']):
        raise Problem('This correction belongs to a historical, remapped or changed source snapshot.',409)
    effective=next((r for r in source_rows(store,workspace,table,con) if r['row']==original['row']),None)
    if not effective or effective['values'][str(original['column'])]['value']!=original['after']:
        raise Problem('The current derived value no longer matches this correction.',409)
    proposal={k:v for k,v in original.items() if k not in {'id','created','revision','approved_at','approved_by'}}
    proposal.update(before=original['after'],after=original['before'],interpretation='audited_reversal',reverses=identifier)
    return proposal


def preview_reversal(store,workspace,identifier,body):
    with store.connection(immediate=True) as con:
        return _simulate(store,workspace,[_reversal(store,workspace,identifier,body,con)],body,con)


def reverse_correction(store,workspace,identifier,body,actor):
    from .lifecycle import invalidate_pending
    if not body.approved:raise Problem('Explicit approval of the reversal is required.')
    with store.connection(immediate=True) as con:
        proposal=_reversal(store,workspace,identifier,body,con)
        preview=_simulate(store,workspace,[proposal],body,con)
        if preview['preview_hash']!=body.preview_hash:raise Problem('Preview the reversal before approving its current totals.',409)
        saved,_,_=_apply(store,workspace,[proposal],actor,con)
        invalidate_pending(store,workspace,'A data correction was reversed. Rerun analyses and regenerate pending proposals.',con)
        store.event(workspace,'correction.reversed','Reversed a derived correction through an additional audited revision.',
                    {'reverses':identifier,'correction':saved[0],'preview':preview,'actor':actor},con)
        return saved[0]
