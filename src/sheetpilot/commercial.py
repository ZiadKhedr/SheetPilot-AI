"""Reviewed commercial terms and explicitly recorded incoming stock.

Source thresholds keep precedence. All quantities are in reviewed base units;
there are no currency or pack/unit conversions and no inferred supplier orders.
"""
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING
from hashlib import sha256
import json
from typing import Literal

from pydantic import Field

from .ingestion import digest
from .lifecycle import active_tables, active_workbooks, invalidate_pending
from .models import Model
from .store import Problem, now, uid


class SupplierTerm(Model):
    inventory_table_id:str=Field(pattern='^[a-f0-9]{32}$')
    product_id:str=Field(min_length=1,max_length=180)
    quote_table_id:str=Field(pattern='^[a-f0-9]{32}$')
    quote_row:int=Field(ge=1,le=1_048_576)
    lead_time_days:int=Field(ge=1,le=365)
    pack_size:str=Field(min_length=1,max_length=40)
    min_order_quantity:str=Field(min_length=1,max_length=40)
    unit_of_measure:str=Field(min_length=1,max_length=40)
    currency:str=Field(pattern='^[A-Z]{3}$')
    price_basis:Literal['per_base_unit']


class CommercialInput(Model):
    expected_revision:int=Field(ge=0)
    expected_fingerprint:str=Field(pattern='^[a-f0-9]{64}$')
    enabled:bool=True
    planning_date:str
    horizon_days:int=Field(ge=1,le=365)
    terms:list[SupplierTerm]=Field(max_length=100)
    approved:bool=False
    preview_hash:str|None=Field(default=None,pattern='^[a-f0-9]{64}$')


class IncomingInput(Model):
    expected_revision:int=Field(ge=0)
    expected_fingerprint:str=Field(pattern='^[a-f0-9]{64}$')
    request_id:str=Field(pattern='^[a-f0-9]{32}$')
    order_reference:str=Field(min_length=1,max_length=120)
    inventory_table_id:str=Field(pattern='^[a-f0-9]{32}$')
    product_id:str=Field(min_length=1,max_length=180)
    supplier_id:str=Field(min_length=1,max_length=180)
    ordered_quantity:str=Field(min_length=1,max_length=40)
    received_quantity:str=Field(min_length=1,max_length=40)
    unit_of_measure:str=Field(min_length=1,max_length=40)
    currency:str=Field(pattern='^[A-Z]{3}$')
    ordered_date:str
    expected_date:str
    status:Literal['draft','confirmed','partially_received','received','cancelled']
    approved:bool=False


def _date(value,label):
    try:
        parsed=date.fromisoformat(value)
        if parsed.isoformat()!=value or parsed<date(1900,1,1):raise ValueError()
        return parsed
    except (ValueError,TypeError):raise Problem(label+' must be an explicit ISO date (YYYY-MM-DD).') from None


def quantity(value,label,*,positive=False):
    from .analytics import decimal_value
    try:
        number=decimal_value(value,label)
        if number!=number.quantize(Decimal('0.000001')) or positive and number<=0:raise ValueError()
        return number
    except (ValueError,ArithmeticError):raise Problem(label+' must be a finite '+('positive' if positive else 'nonnegative')+' base-unit quantity with at most six decimal places.') from None


def policy_for(store,workspace,con=None):
    return next(iter(store.list(workspace,'commercial_policy',con)),None)


def context_for(store,workspace,all_records=None,override=None):
    from .analytics import records
    tables={t['id']:t for t in active_tables(store,workspace)}
    books={w['id']:w for w in active_workbooks(store,workspace)}
    data=all_records if all_records is not None else records(store,workspace)
    links=[]
    # Kept separate from quoted data: a reviewed quote selection is never a join approval.
    for link in store.list(workspace,'relationship'):
        pair=[tables.get(link[k]) for k in ['left_table','right_table']]
        if (all(pair) and link['status']=='confirmed' and link['field']=='product_id' and link.get('match_mode','exact')=='exact'
                and all(t['status']=='confirmed' for t in pair) and link['revisions']==[t['revision'] for t in pair]):
            links.append({link['left_table'],link['right_table']})
    return {'policy':override if override is not None else policy_for(store,workspace),'tables':tables,'books':books,
            'quotes':[r for r in data if r['entity']=='suppliers'],'inventory':[r for r in data if r['entity']=='inventory'],
            'links':links,'incoming':store.list(workspace,'incoming_order')}


def source_key(context,record):
    source=record['source'];table=context['tables'][source['table_id']]
    return {'table_id':table['id'],'workbook_id':table['workbook_id'],'sha256':context['books'][table['workbook_id']]['sha256'],
            'row':source['row'],'mapping_revision':table['revision'],'corrections':source.get('corrections',[])}


def _quote_signature(record):
    return sha256(json.dumps({k:record['data'].get(k) for k in ['product_id','supplier_id','currency','unit_cost','unit_of_measure',
        'lead_time_days','pack_size','min_order_quantity']},sort_keys=True).encode()).hexdigest()


def quote_candidates(context,item):
    return [r for r in context['quotes'] if r['data']['product_id']==item['product_id'] and
            (not item.get('supplier_id') or r['data']['supplier_id']==item['supplier_id']) and
            {item['source']['table_id'],r['source']['table_id']} in context['links']]


def reviewed_selection(context,item,candidates):
    policy=context['policy']
    if not policy or not policy['enabled']:return candidates[0] if len(candidates)==1 else None
    terms=[t for t in policy['terms'] if t['product_id']==item['product_id'] and t['inventory_table_id']==item['source']['table_id']]
    if len(terms)!=1:return None
    term=terms[0]
    selected=[r for r in candidates if r['source']['table_id']==term['quote_table_id'] and r['source']['row']==term['quote_row']]
    return selected[0] if len(selected)==1 else None


def term_for(context,item,quote=None):
    policy=context['policy']
    if not policy or not policy['enabled']:return None,None
    terms=[t for t in policy['terms'] if t['product_id']==item['product_id'] and t['inventory_table_id']==item['source']['table_id']]
    if len(terms)!=1:return None,'Review supplier delivery, base units, pack size and minimum quantity for this product.'
    term=terms[0]
    quote=quote or reviewed_selection(context,item,quote_candidates(context,item))
    if not quote:return None,'Review the product relationship and select an exact supplier quote in supplier planning.'
    if (term.get('inventory_source')!=source_key(context,{'source':item['source']}) or term.get('quote_source')!=source_key(context,quote)
            or term.get('quote_signature')!=_quote_signature(quote)):
        return None,'Source, mapping or corrections changed. Review the supplier terms against the current snapshots.'
    for row in [item,quote['data']]:
        if row.get('unit_of_measure') and row['unit_of_measure'].strip().casefold()!=term['unit_of_measure'].strip().casefold():
            return None,'Source units differ from the reviewed base unit. Explicit unit conversion is not supported.'
        if row.get('currency')!=term['currency']:return None,'Inventory, quote and reviewed commercial currency must match explicitly.'
    return term,None


def incoming_basis(context,item,unit,currency):
    policy=context['policy'];start=_date(policy['planning_date'],'Planning date');end=start+timedelta(days=policy['horizon_days'])
    eligible=Decimal(0);basis=[]
    for incoming in context['incoming']:
        if incoming['product_id']!=item['product_id']:continue
        reasons=[]
        if incoming['status'] not in {'confirmed','partially_received'}:reasons.append('Status is not confirmed or partially received.')
        if incoming['inventory_source']!=source_key(context,{'source':item['source']}):reasons.append('Stock snapshot/mapping/correction needs incoming-order review.')
        if incoming['unit_of_measure'].strip().casefold()!=unit.strip().casefold():reasons.append('Base units do not match.')
        if incoming['currency']!=currency:reasons.append('Currency does not match.')
        receipt=_date(incoming['expected_date'],'Expected receipt date')
        if receipt<start:reasons.append('Receipt date is overdue; review it before counting this order.')
        if receipt>end:reasons.append('Receipt is outside this planning horizon.')
        remaining=quantity(incoming['ordered_quantity'],'Ordered quantity')-quantity(incoming['received_quantity'],'Received quantity')
        if remaining<=0:reasons.append('No unreceived quantity remains.')
        counted=max(Decimal(0),remaining) if not reasons else Decimal(0)
        eligible+=counted
        basis.append({k:incoming[k] for k in ['id','revision','order_reference','supplier_id','ordered_quantity','received_quantity',
            'unit_of_measure','currency','expected_date','status','approved_by','reviewed_at']}|
            {'eligible_quantity':str(counted),'exclusion_reasons':reasons,'inventory_source':incoming['inventory_source']})
    return eligible,basis,start,end


def apply_rules(context,item,term):
    incoming,basis,start,end=incoming_basis(context,item,term['unit_of_measure'],term['currency'])
    stock=quantity(item['stock_quantity'],'Stock quantity');target=quantity(item['target_stock'],'Target stock')
    point=quantity(item['reorder_point'],'Reorder point');position=stock+incoming
    need=max(Decimal(0),target-position) if position<point else Decimal(0)
    pack=quantity(term['pack_size'],'Pack size',positive=True);minimum=quantity(term['min_order_quantity'],'Minimum order quantity')
    minimum_applied=max(need,minimum) if need else Decimal(0)
    packs=(minimum_applied/pack).to_integral_value(rounding=ROUND_CEILING) if need else Decimal(0)
    ordered=packs*pack
    if ordered>Decimal('1000000000'):raise Problem('Pack/MOQ rounding exceeds the supported quantity limit.')
    commercial={'origin':'human-reviewed supplier terms and separately recorded incoming orders','policy_revision':context['policy']['revision'],
        'reviewed_by':context['policy']['approved_by'],'reviewed_at':context['policy']['reviewed_at'],
        'planning_date':start.isoformat(),'horizon_end':end.isoformat(),'horizon_days':context['policy']['horizon_days'],
        'expected_supplier_receipt':(start+timedelta(days=term['lead_time_days'])).isoformat(),
        'lead_time_days':term['lead_time_days'],'unit_of_measure':term['unit_of_measure'],'price_basis':term['price_basis'],
        'currency':term['currency'],'threshold_source':item['threshold_source'],'reorder_point':str(point),'target_stock':str(target),
        'on_hand':str(stock),'eligible_incoming':str(incoming),'inventory_position':str(position),'net_requirement':str(need),
        'pack_size':str(pack),'minimum_order_quantity':str(minimum),'after_minimum':str(minimum_applied),
        'pack_count':str(packs),'final_quantity':str(ordered),'incoming_orders':basis,
        'inventory_source':term['inventory_source'],'quote_source':term['quote_source'],'quote_signature':term['quote_signature'],
        'observed_source_terms':term['observed_source_terms'],
        'calculation':f"Position {stock} + eligible incoming {incoming} = {position}; reorder below {point}. "
                      f"Net target requirement {need}; minimum {minimum}; ceil({minimum_applied} / pack {pack}) × {pack} = {ordered} {term['unit_of_measure']}."}
    return str(ordered),commercial


def _candidate_policy(store,workspace,body,con):
    from .actions import fingerprint
    current=policy_for(store,workspace,con)
    if (current['revision'] if current else 0)!=body.expected_revision or fingerprint(store,workspace,con)!=body.expected_fingerprint:
        raise Problem('Source or commercial policy revision changed. Refresh and preview again.',409)
    planning_date=_date(body.planning_date,'Planning date')
    if planning_date>date.today():raise Problem('Use the reviewed stock snapshot date, no later than today.')
    context=context_for(store,workspace);seen=set();terms=[]
    if body.enabled and not body.terms:raise Problem('Select and review at least one supplier quote and its commercial terms.')
    for value in body.terms:
        if not value.unit_of_measure.strip():raise Problem('Review an explicit nonempty base unit.')
        key=(value.inventory_table_id,value.product_id)
        if key in seen:raise Problem('Select one reviewed supplier quote per inventory product.')
        seen.add(key)
        stock=[r for r in context['inventory'] if r['source']['table_id']==value.inventory_table_id and r['product_id']==value.product_id]
        quotes=[r for r in context['quotes'] if r['source']['table_id']==value.quote_table_id and r['source']['row']==value.quote_row]
        if len(stock)!=1 or len(quotes)!=1:raise Problem('Choose a unique active inventory row and exact reviewed supplier quote.')
        item,quote=stock[0],quotes[0]
        if quote['data']['product_id']!=value.product_id or item['data'].get('supplier_id') and item['data']['supplier_id']!=quote['data']['supplier_id']:
            raise Problem('The selected quote does not match the inventory product/supplier.')
        if not quote['source'].get('quote_precision_checked'):raise Problem('Confirm the supplier mapping again to refresh original quote precision.')
        for record in [item,quote]:
            source=source_key(context,record);path=store.root/'originals'/f"{source['workbook_id']}.xlsx"
            if not path.is_file() or digest(path)!=source['sha256']:raise Problem('A referenced source workbook is missing or changed.',409)
            if record['data'].get('currency')!=value.currency:raise Problem('Stock, supplier quote and reviewed currency must explicitly match.')
            unit=record['data'].get('unit_of_measure')
            if unit and unit.strip().casefold()!=value.unit_of_measure.strip().casefold():raise Problem('Source and reviewed base units differ. No implicit conversion is allowed.')
        pack=quantity(value.pack_size,'Pack size',positive=True);minimum=quantity(value.min_order_quantity,'Minimum order quantity')
        terms.append(value.model_dump()|{'pack_size':str(pack),'min_order_quantity':str(minimum),
            'inventory_source':source_key(context,item),'quote_source':source_key(context,quote),
            'supplier_id':quote['data']['supplier_id'],'quote_signature':_quote_signature(quote),
            'observed_source_terms':{k:quote['data'].get(k) for k in ['lead_time_days','pack_size','min_order_quantity','unit_of_measure']}})
    return {'id':current['id'] if current else uid(),'revision':body.expected_revision+1,'enabled':body.enabled,
            'planning_date':planning_date.isoformat(),'horizon_days':body.horizon_days,'terms':terms,
            'approved_by':'preview','reviewed_at':'preview'}


def _policy_preview(store,workspace,body,con):
    from .actions import procurement_readiness
    candidate=_candidate_policy(store,workspace,body,con)
    readiness=procurement_readiness(store,workspace,commercial_override=candidate)
    # A new policy's UUID and approval time are assigned only on save.
    basis={k:v for k,v in candidate.items() if k not in {'id','approved_by','reviewed_at'}}
    value={'policy':basis,'readiness':readiness,'fingerprint':body.expected_fingerprint}
    value['preview_hash']=sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return value,candidate


def preview_policy(store,workspace,body):
    with store.connection(immediate=True) as con:return _policy_preview(store,workspace,body,con)[0]


def save_policy(store,workspace,body,actor):
    if not body.approved:raise Problem('Review units, price basis, stock date, supplier terms and incoming eligibility before approving this policy.')
    with store.connection(immediate=True) as con:
        preview,candidate=_policy_preview(store,workspace,body,con)
        if preview['preview_hash']!=body.preview_hash:raise Problem('Preview the current supplier policy before saving its review.',409)
        candidate.update(approved_by=actor,reviewed_at=now())
        saved=store.put(workspace,'commercial_policy',candidate,con)
        invalidate_pending(store,workspace,'Reviewed supplier planning terms changed. Rerun analyses and regenerate pending proposals.',con)
        store.event(workspace,'commercial.policy_reviewed','Reviewed supplier terms, explicit base units and receipt horizon.',
                    {'policy':saved,'preview':preview,'actor':actor},con)
        return saved


def save_incoming(store,workspace,body,actor,identifier=None):
    from .actions import fingerprint
    with store.connection(immediate=True) as con:
        previous=store.get(workspace,'incoming_order',identifier,con) if identifier else None
        orders=store.list(workspace,'incoming_order',con)
        repeated=next((r for r in orders if r.get('request_id')==body.request_id),None)
        content={k:v for k,v in body.model_dump().items() if k not in {'request_id','expected_revision','expected_fingerprint','approved'}}
        request_hash=sha256(json.dumps(content,sort_keys=True).encode()).hexdigest()
        if repeated:
            if repeated['request_hash']!=request_hash:raise Problem('This request identifier was used for different incoming-order data.',409)
            return repeated
        if not body.approved:raise Problem('Explicitly review this supplier-order record. A generated workbook is not a confirmed order.')
        if not body.order_reference.strip() or not body.unit_of_measure.strip():raise Problem('Order reference and reviewed base unit cannot be blank.')
        if (previous['revision'] if previous else 0)!=body.expected_revision or fingerprint(store,workspace,con)!=body.expected_fingerprint:
            raise Problem('Incoming order or workspace revision changed. Refresh before saving.',409)
        context=context_for(store,workspace)
        if not context['policy'] or not context['policy']['enabled']:raise Problem('Review and enable supplier planning before recording incoming stock.')
        stock=[r for r in context['inventory'] if r['product_id']==body.product_id and r['source']['table_id']==body.inventory_table_id]
        if len(stock)!=1:raise Problem('Select a unique active reviewed inventory record.')
        term,error=term_for(context,stock[0]['data']|{'source':stock[0]['source']})
        if error:raise Problem(error)
        for source in [term['inventory_source'],term['quote_source']]:
            path=store.root/'originals'/f"{source['workbook_id']}.xlsx"
            if not path.is_file() or digest(path)!=source['sha256']:
                raise Problem('A referenced source workbook changed. Incoming-order review refused.',409)
        if body.currency!=term['currency'] or body.unit_of_measure.strip().casefold()!=term['unit_of_measure'].strip().casefold():
            raise Problem('Incoming currency/base units must match the reviewed product. No conversion is assumed.')
        suppliers=[r for r in context['quotes'] if r['product_id']==body.product_id and r['data']['supplier_id']==body.supplier_id and r['data']['currency']==body.currency]
        if not suppliers:raise Problem('The explicit supplier/product/currency is not present in reviewed supplier records.')
        ordered=quantity(body.ordered_quantity,'Ordered quantity',positive=True);received=quantity(body.received_quantity,'Received quantity')
        if received>ordered:raise Problem('Received quantity cannot exceed the ordered quantity.')
        if body.status in {'draft','confirmed'} and received or body.status=='partially_received' and not Decimal(0)<received<ordered or body.status=='received' and received!=ordered:
            raise Problem('Order status and received quantity disagree. Review the actual supplier-order state.')
        ordered_date=_date(body.ordered_date,'Order date');expected=_date(body.expected_date,'Expected receipt date')
        if expected<ordered_date:raise Problem('Expected receipt cannot precede the order date.')
        identity=(body.order_reference.strip(),body.product_id,body.supplier_id)
        if any(r['id']!=identifier and (r['order_reference'],r['product_id'],r['supplier_id'])==identity for r in orders):
            raise Problem('This supplier order/reference and product already exist. Edit that record instead of duplicating incoming stock.',409)
        if not previous and len(orders)>=1000:raise Problem('This local workspace supports at most 1,000 incoming-order lines.')
        saved=store.put(workspace,'incoming_order',content|{'id':identifier or uid(),'order_reference':identity[0],
            'ordered_quantity':str(ordered),'received_quantity':str(received),'revision':body.expected_revision+1,
            'inventory_source':source_key(context,stock[0]),'policy_revision':context['policy']['revision'],
            'request_id':body.request_id,'request_hash':request_hash,'approved_by':actor,'reviewed_at':now()},con)
        invalidate_pending(store,workspace,'A reviewed incoming-order record changed. Rerun analyses and regenerate pending proposals.',con)
        store.event(workspace,'incoming.reviewed','Recorded a separately reviewed supplier-order line; no stock receipt was inferred from workbook generation.',
                    {'before':previous,'after':saved,'actor':actor},con)
        return saved
