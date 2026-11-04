"""Explicit snapshot activation after schema, mapping and stable-key review."""
from collections import defaultdict
from hashlib import sha256
import json

from pydantic import Field, model_validator

from .actions import fingerprint
from .analytics import materialize
from .ingestion import digest
from .lifecycle import invalidate_pending
from .mapping import identifier, source_rows
from .models import Model
from .semantics import IDENTIFIER_FIELDS
from .store import Problem, now


class TablePair(Model):
    previous_table_id: str | None = None
    table_id: str | None = None
    key_fields: list[str] = Field(min_length=1,max_length=4)

    @model_validator(mode='after')
    def one_table(self):
        if not self.previous_table_id and not self.table_id:
            raise ValueError('Select a previous or new table.')
        if len(set(self.key_fields)) != len(self.key_fields):
            raise ValueError('Each key meaning may appear once.')
        return self


class VersionPreview(Model):
    expected_fingerprint: str = Field(pattern='^[a-f0-9]{64}$')
    pairs: list[TablePair] = Field(min_length=1,max_length=100)


class VersionReview(VersionPreview):
    expected_revision: int = Field(ge=0)
    identifiers_confirmed: bool = False


class VersionActivation(Model):
    expected_revision: int = Field(ge=1)
    expected_fingerprint: str = Field(pattern='^[a-f0-9]{64}$')


def version_context(store,workspace,identifier_,con=None):
    candidate=store.get(workspace,'workbook',identifier_,con)
    if not candidate.get('previous_workbook_id'):
        raise Problem('This workbook is not a version update.')
    previous=store.get(workspace,'workbook',candidate['previous_workbook_id'],con)
    tables=[t for t in store.list(workspace,'table',con) if t['workbook_id'] in {previous['id'],candidate['id']}]
    ids={t['id'] for t in tables}
    value={'context':fingerprint(store,workspace,con),'books':[(w['id'],w['sha256'],w.get('active',True)) for w in [previous,candidate]],
           'tables':[(t['id'],t['revision'],t['status']) for t in tables],
           'links':[(r['id'],r['status'],r['revisions']) for r in store.list(workspace,'relationship',con)
                    if r['left_table'] in ids or r['right_table'] in ids]}
    token=sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    reviews=[r for r in store.list(workspace,'version_review',con) if r['workbook_id']==identifier_]
    return {'candidate':candidate,'previous':previous,'tables':tables,'fingerprint':token,
            'review':reviews[-1] if reviews else None}


def _keyed(store,workspace,table,keys,con):
    if not table:return {},[]
    by_field={field:col for col,field in table['fields'].items() if field!='ignore'}
    if table['status']!='confirmed' or set(keys)-set(by_field) or set(keys)-set(IDENTIFIER_FIELDS):
        raise Problem('Stable keys must be explicitly reviewed identifier meanings in both confirmed mappings.')
    groups=defaultdict(list)
    problems=[]
    for raw in source_rows(store,workspace,table,con):
        cells=[raw['values'][by_field[key]] for key in keys]
        key=tuple(identifier(cell['value']) for cell in cells)
        if any(not k for k in key) or any(cell['data_type'] in {'f','e'} for cell in cells):
            problems.append({'table_id':table['id'],'row':raw['row'],'reason':'Missing or formula/error stable identifier.'})
            continue
        value={table['fields'].get(col,'custom:'+str(col)+':'+next(c['label'] for c in table['columns'] if str(c['index'])==col)):
               cell['value'] for col,cell in raw['values'].items() if table['fields'].get(col)!='ignore'}
        groups[key].append({'row':raw['row'],'values':value})
    for key,rows in groups.items():
        if len(rows)>1: problems.append({'table_id':table['id'],'key':list(key),'rows':[r['row'] for r in rows],
                                      'reason':'Ambiguous stable identifier. Choose a genuinely unique composite key or repair the identifiers.'})
    return {key:rows[0] for key,rows in groups.items() if len(rows)==1},problems


def preview_version(store,workspace,identifier_,body,con=None):
    context=version_context(store,workspace,identifier_,con)
    if context['fingerprint']!=body.expected_fingerprint:
        raise Problem('Snapshot or reviews changed. Refresh the version comparison.',409)
    if context['candidate'].get('active',False) or not context['previous'].get('active',True):
        raise Problem('This candidate can only replace its still-active previous snapshot.',409)
    old={t['id']:t for t in context['tables'] if t['workbook_id']==context['previous']['id']}
    new={t['id']:t for t in context['tables'] if t['workbook_id']==identifier_}
    if any(t['status'] not in {'confirmed','ignored'} for t in new.values()):
        raise Problem('Review or explicitly exclude every table in the new snapshot before comparing records.')
    seen_old,seen_new=set(),set()
    changes,problems=[],[]
    for pair in body.pairs:
        for key,lookup,seen in [(pair.previous_table_id,old,seen_old),(pair.table_id,new,seen_new)]:
            if key and (key not in lookup or key in seen):
                raise Problem('Table pairs must reference unique tables in these two snapshots.')
            if key: seen.add(key)
        before,after=old.get(pair.previous_table_id),new.get(pair.table_id)
        if before and after and before['entity']!=after['entity']:
            raise Problem('Paired tables must use the same reviewed business entity.')
        left,errors=_keyed(store,workspace,before,pair.key_fields,con)
        right,other_errors=_keyed(store,workspace,after,pair.key_fields,con)
        problems.extend(errors+other_errors)
        added=sorted(right.keys()-left.keys())
        removed=sorted(left.keys()-right.keys())
        changed=sorted(k for k in left.keys() & right.keys() if left[k]['values']!=right[k]['values'])
        def columns(t):return [c['label'] for c in t['columns']] if t else []
        changes.append({'previous_table_id':pair.previous_table_id,'table_id':pair.table_id,'key_fields':pair.key_fields,
            'schema':{'before':columns(before),'after':columns(after),'mapping_changed':bool(before and after and before['fields']!=after['fields'])},
            'counts':{'added':len(added),'removed':len(removed),'changed':len(changed),'unchanged':len(left.keys()&right.keys())-len(changed)},
            'examples':([{'kind':'added','key':list(k),'after':right[k]} for k in added[:30]]+
                        [{'kind':'removed','key':list(k),'before':left[k]} for k in removed[:30]]+
                        [{'kind':'changed','key':list(k),'before':left[k],'after':right[k]} for k in changed[:30]])})
    if seen_old!={t['id'] for t in old.values() if t['status']=='confirmed'} or seen_new!={t['id'] for t in new.values() if t['status']=='confirmed'}:
        raise Problem('Pair every confirmed previous/new table, explicitly marking added or removed tables. Excluded tables need no pair.')
    return {'fingerprint':context['fingerprint'],'changes':changes,'blockers':problems[:100],
            'blocker_count':len(problems),'can_review':not problems,
            'message':'Exact reviewed keys only. Row movement is not a record change. Originals remain preserved.'}


def review_version(store,workspace,identifier_,body,actor):
    if not body.identifiers_confirmed:
        raise Problem('Explicitly confirm that the selected keys are stable record identifiers.')
    with store.connection(immediate=True) as con:
        context=version_context(store,workspace,identifier_,con)
        revision=context['review']['revision'] if context['review'] else 0
        if revision!=body.expected_revision:raise Problem('Version review changed. Refresh before saving.',409)
        result=preview_version(store,workspace,identifier_,body,con)
        if result['blocker_count']:raise Problem('Ambiguous or missing identifiers block activation. Resolve them explicitly.')
        value={
            'workbook_id':identifier_,'previous_workbook_id':context['previous']['id'],'revision':revision+1,
            'fingerprint':result['fingerprint'],'pairs':[p.model_dump() for p in body.pairs],
            'comparison':result,'approved_by':actor,'approved_at':now(),'status':'reviewed'}
        if context['review']:value['id']=context['review']['id']
        review=store.put(workspace,'version_review',value,con)
        store.event(workspace,'version.reviewed','Reviewed stable identifiers and snapshot differences.',
                    {'workbook_id':identifier_,'review_revision':review['revision'],'comparison':result,'actor':actor},con)
        return review


def activate_version(store,workspace,identifier_,body,actor):
    with store.connection(immediate=True) as con:
        context=version_context(store,workspace,identifier_,con)
        candidate,previous,review=context['candidate'],context['previous'],context['review']
        if candidate.get('active',False) and review and review['status']=='activated' and review['revision']==body.expected_revision:
            return candidate
        if (not review or review['revision']!=body.expected_revision or review['status']!='reviewed'
                or review['fingerprint']!=context['fingerprint'] or body.expected_fingerprint!=context['fingerprint']):
            raise Problem('Version or reviews changed. Compare and review this snapshot again before activation.',409)
        preview_version(store,workspace,identifier_,VersionPreview(expected_fingerprint=context['fingerprint'],pairs=[TablePair(**p) for p in review['pairs']]),con)
        for book in (previous,candidate):
            path=store.root/'originals'/f"{book['id']}.xlsx"
            if not path.is_file() or digest(path)!=book['sha256']:
                raise Problem('An original source hash changed. Activation refused.',409)
        previous.update(active=False,superseded_by=identifier_)
        candidate.update(active=True,activated_at=now(),activated_by=actor)
        store.put(workspace,'workbook',previous,con)
        store.put(workspace,'workbook',candidate,con)
        old_ids={t['id'] for t in context['tables'] if t['workbook_id']==previous['id']}
        for relation in store.list(workspace,'relationship',con):
            if relation['left_table'] in old_ids or relation['right_table'] in old_ids:
                relation['status']='stale'
                store.put(workspace,'relationship',relation,con)
        review['status']='activated'
        store.put(workspace,'version_review',review,con)
        invalidate_pending(store,workspace,'A reviewed workbook snapshot was activated. Regenerate pending proposals and rerun analyses.',con)
        materialize(store,workspace,con)
        store.event(workspace,'version.activated','Activated reviewed snapshot; previous original and historical outputs preserved.',
                    {'workbook_id':identifier_,'previous_workbook_id':previous['id'],'sha256':candidate['sha256'],
                     'review_revision':review['revision'],'actor':actor},con)
        return candidate
