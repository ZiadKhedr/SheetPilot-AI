"""Validate the saved Excel pack, optionally through isolated SheetPilot services.

Never imports sheetpilot.api (it initializes the live default store), never reads
.env, and never creates a provider. --app uses only temporary private stores.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile
from uuid import uuid4
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter, range_boundaries

D=Decimal


def money(value):
    return str(D(value).quantize(D('.01'),rounding=ROUND_HALF_UP))


class Checks:
    def __init__(self): self.count=0; self.sections=[]
    def check(self,condition,message):
        self.count+=1
        if not condition: raise AssertionError(message)
    def equal(self,actual,expected,message): self.check(actual==expected,f'{message}: {actual!r} != {expected!r}')
    def section(self,name): self.sections.append(dict(name=name,status='passed')); print('PASS '+name,flush=True)


def read_tables(root,manifest,checks):
    tables={}
    books={}
    files=sorted({t['workbook'] for t in manifest['tables']})
    checks.equal(len(files),9,'workbook count')
    max_grid=0
    for name in files:
        path=root/name
        metadata=next(w for w in manifest['workbooks'] if w['path']==name)
        checks.equal(sha256(path.read_bytes()).hexdigest(),metadata['sha256'],f'{name} source hash')
        checks.equal(path.stat().st_size,metadata['size_bytes'],f'{name} recorded size')
        checks.check(0 < path.stat().st_size < 10*1024*1024,f'{name} size')
        with ZipFile(path) as z:
            checks.check(z.testzip() is None,f'{name} ZIP integrity')
            checks.check(not any('vbaproject' in n.lower() or 'externallink' in n.lower() for n in z.namelist()),f'{name} no macros/external links')
        book=load_workbook(path,data_only=False,keep_links=False)
        books[name]=book
        checks.check(len(book.worksheets)<=30,f'{name} sheet limit')
        grids=[]
        for ws in book:
            grid=ws.max_row*ws.max_column
            grids.append(grid);max_grid=max(max_grid,grid)
            checks.check(grid<90000,f'{name}/{ws.title} full bounding grid < 90000')
            for row in ws:
                for cell in row:
                    checks.check(cell.data_type not in {'f','e'},f'{name}/{ws.title}/{cell.coordinate} literal values only')
                    if isinstance(cell.value,(int,float)):
                        checks.check(abs(D(str(cell.value)))<=D(10)**9,f'{name}/{cell.coordinate} numeric limit')
        checks.check(sum(grids)<=200000,f'{name} workbook grid limit')
    for t in manifest['tables']:
        ws=books[t['workbook']][t['sheet']]
        left,top,right,bottom=range_boundaries(t['region'])
        checks.equal(top,t['header_row'],f'{t["id"]} header row')
        checks.equal(bottom-top,t['data_rows'],f'{t["id"]} row count')
        checks.equal(right-left+1,len(t['columns']),f'{t["id"]} physical columns')
        checks.check(bool(ws.freeze_panes),f'{t["id"]} frozen headers')
        checks.equal(ws.auto_filter.ref,t['region'],f'{t["id"]} contiguous filter')
        checks.check(all(m.max_row < top for m in ws.merged_cells.ranges),f'{t["id"]} no merged business cells')
        fields=[]
        for c in t['columns']:
            checks.equal(ws[c['header_cell']].value,c['source_label'],f'{t["id"]} header cell {c["header_cell"]}')
            checks.equal(ws[c['header_cell']].column,c['source_column_index'],f'{t["id"]} physical index')
            fields.append(c['canonical_field'] or c['custom_name'])
        rows=[]
        for r in range(top+1,bottom+1):
            values={}
            for c,field in zip(t['columns'],fields):
                cell=ws.cell(r,c['source_column_index']);v=cell.value
                if isinstance(v,datetime):v=v.date()
                if field.endswith('_id') or field in {'barcode','postal_code','phone'}:
                    checks.check(v is None or isinstance(v,str),f'{t["id"]} {cell.coordinate} text identity')
                if field in {'barcode','postal_code','phone'} and v is not None:
                    checks.check(v.startswith('00'),f'{t["id"]} {cell.coordinate} leading zeroes preserved')
                values[field]=v
            rows.append(values)
        tables[t['id']]=rows
        if t['exact_keys'] and t['id']!='quality:sales':
            keys=[tuple(row.get(f) for f in t['exact_keys']) for row in rows]
            checks.equal(len(keys),len(set(keys)),f'{t["id"]} exact keys unique')
            checks.check(all(all(v is not None for v in k) for k in keys),f'{t["id"]} keys complete')
    for name,b in books.items():b.close()
    checks.section('Saved XLSX readability, bounded grids, styling, literal cells, source coordinates and exact keys')
    return tables,dict(workbooks=len(files),largest_sheet_grid=max_grid)


def validate_business(root,m,e,tables,checks):
    a=date.fromisoformat(e['as_of']);c=e['core']
    lines,orders,stock,quotes=(tables['core:'+x] for x in ('sales','orders','inventory','suppliers'))
    checks.equal([len(lines),len(orders),len(stock),len({q['supplier_id'] for q in quotes})],[6000,1200,40,8],'core scale')
    checks.equal(c['counts'],dict(sales_lines=len(lines),orders=len(orders),stock_skus=len(stock),suppliers=len({q['supplier_id'] for q in quotes})),'expected counts agree with saved sources')
    order_by_id={o['order_id']:o for o in orders};stock_by_id={p['product_id']:p for p in stock};quote_by_id={p['product_id']:p for p in quotes}
    checks.equal(set(stock_by_id),set(quote_by_id),'quote coverage')
    totals,units,order_totals,order_counts=defaultdict(D),defaultdict(D),defaultdict(D),Counter()
    current,previous=defaultdict(D),defaultdict(D)
    recent,positive,positive_days=defaultdict(D),Counter(),defaultdict(set)
    dates=[];signatures=[]
    for r in lines:
        checks.check(r['product_id'] in stock_by_id and r['order_id'] in order_by_id,'exact line relationships')
        checks.check('sale_date' not in r and 'product_name' not in r,'core relies on reviewed context')
        q,price,rev=(D(str(r[k])) for k in ('quantity','unit_price','revenue'))
        checks.equal(price,D(str(r['list_unit_price']))-D(str(r['unit_discount'])),'net price arithmetic')
        checks.equal(money(rev),money(q*price),'line arithmetic')
        checks.check(rev>0 and q>0 and r['currency']=='EGP' and r['unit_of_measure']=='each','valid sale units and currency')
        pid=r['product_id'];day=order_by_id[r['order_id']]['sale_date'];dates.append(day)
        checks.check(day<=a,'sale not future to snapshot')
        totals[pid]+=rev;units[pid]+=q;order_totals[r['order_id']]+=rev;order_counts[r['order_id']]+=1
        if a-timedelta(days=6)<=day<=a:current[pid]+=rev
        if a-timedelta(days=13)<=day<=a-timedelta(days=7):previous[pid]+=rev
        if a-timedelta(days=29)<=day<=a:recent[pid]+=q;positive[pid]+=1;positive_days[pid].add(day)
        signatures.append(tuple(r.items()))
    checks.equal(len(set(signatures)),len(lines),'no exact core duplicates')
    checks.equal(set(order_counts.values()),{5},'five actual lines per order')
    checks.equal(len(set(dates)),90,'90 fully populated calendar days')
    checks.equal(min(dates),a-timedelta(days=89),'history begins exactly 89 days before as_of')
    checks.equal(max(dates),a,'latest sale anchors comparison')
    for o in orders:checks.equal(money(D(str(o['order_total']))),money(order_totals[o['order_id']]),'header total reconciles to line sum')
    checks.equal(c['revenue'],money(sum(totals.values(),D(0))),'headline revenue derived from lines')
    checks.equal(D(c['units']),sum(units.values(),D(0)),'headline units')
    for p in stock:
        q=quote_by_id[p['product_id']]
        checks.check(p['target_stock']>=p['reorder_point'],'source target >= reorder')
        checks.check(p['opening_stock']!=p['stock_quantity'] and p['stock_reserved']!=p['stock_quantity'] if p['stock_quantity'] else p['opening_stock']!=0,'distinct physical/opening/reserved meanings')
        checks.equal((p['supplier_id'],p['currency'],p['unit_of_measure']),(q['supplier_id'],q['currency'],q['unit_of_measure']),'exact procurement dimensions')
        checks.check(q['supplier_email'].endswith('@example.invalid'),'fictional supplier contact')
        checks.check(D(str(q['unit_cost']))<next(D(str(r['unit_price'])) for r in lines if r['product_id']==p['product_id']),'positive gross margin')
    checks.equal(recent['NC-001'],D(600),'hero trailing units')
    checks.equal(D(stock_by_id['NC-001']['stock_quantity'])/(recent['NC-001']/30),D('.9'),'hero cover')
    checks.equal(current['NC-002'],previous['NC-002']*3,'+200% same-price growth')
    checks.equal(current['NC-003'],previous['NC-003']*D('.4'),'-60% same-price decline')
    for pid in stock_by_id:
        case=c['risk_cases'][pid]
        checks.equal(D(case['units_30d']),recent[pid],pid+' demand units')
        checks.equal(case['observed_days'],30,pid+' observed days from table history')
        checks.equal(case['positive_records_30d'],positive[pid],pid+' positive records')
        checks.equal(case['positive_days_30d'],len(positive_days[pid]),pid+' positive days')
        checks.equal(case['eligible'],bool(recent[pid] and positive[pid]>=3 and len(positive_days[pid])>=2),pid+' history eligibility')
    checks.equal(positive['NC-008'],2,'new product exactly two positive records')
    checks.equal(len(positive_days['NC-008']),2,'new product two dates')
    checks.equal(recent['NC-007'],D(0),'dormant no recent sales')
    checks.check(units['NC-007']>0,'dormant older history remains')
    top=sorted(units,key=lambda p:units[p],reverse=True)[:10]
    checks.equal([r['product_id'] for r in c['top_products']],top,'displayed top products')
    checks.check({'NC-001','NC-002','NC-003','NC-004'}<=set(top),'hero growth decline and OOS visible in top ten')
    changes={r['product_id']:r for r in c['comparison']['products']}
    for pid in stock_by_id:
        checks.equal(changes[pid]['current_revenue'],money(current[pid]),'comparison current '+pid)
        checks.equal(changes[pid]['previous_revenue'],money(previous[pid]),'comparison previous '+pid)
        checks.equal(changes[pid]['change'],money(current[pid]-previous[pid]),'comparison change '+pid)
        checks.equal(changes[pid]['percent_change'],money((current[pid]-previous[pid])*100/previous[pid]) if previous[pid] else None,'comparison percentage '+pid)
    for k,v in [('current_from',a-timedelta(days=6)),('current_to',a),('previous_from',a-timedelta(days=13)),('previous_to',a-timedelta(days=7))]:checks.equal(c['comparison'][k],str(v),'comparison period '+k)
    checks.equal(c['comparison']['current_revenue'],money(sum(current.values(),D(0))),'current window total')
    checks.equal(c['comparison']['previous_revenue'],money(sum(previous.values(),D(0))),'previous window total')
    draft=[];supplier_totals=defaultdict(D)
    for p in stock:
        if p['stock_quantity']<p['reorder_point']:
            quantity=D(p['target_stock'])-D(p['stock_quantity']);q=quote_by_id[p['product_id']];amount=D(money(quantity*D(str(q['unit_cost']))))
            draft.append((p['product_id'],quantity,money(amount)))
            supplier_totals[(q['supplier_id'],'EGP')]+=amount
    checks.equal([(r['product_id'],D(r['quantity']),r['line_total']) for r in c['draft_lines']],draft,'all core draft lines')
    checks.equal(c['draft_by_supplier'],[dict(supplier_id=s,currency=cc,amount=money(v)) for (s,cc),v in sorted(supplier_totals.items())],'supplier subtotals')
    checks.equal(c['draft_total'],money(sum(supplier_totals.values(),D(0))),'full draft total')
    qrows=tables['quality:sales'];signatures=[tuple(r.items()) for r in qrows]
    checks.equal(len(qrows)-len(set(signatures)),e['quality']['exact_duplicates'],'quality exact duplicates')
    checks.equal(sum(not r['product_id'] for r in qrows),1,'quality missing identifier remains excluded')
    checks.equal(qrows[4]['quantity'],'1,200','thousands comma literal')
    checks.equal(qrows[5]['unit_price'],'25,50','decimal comma literal')
    checks.equal(qrows[6]['sale_date'],a.strftime('%d/%m/%Y'),'DMY literal')
    checks.equal(qrows[7]['quantity'],'1200','numeric text accepted example')
    def quality_totals(rows):
        seen=set();total=dated=D(0);valid=0
        for r in rows:
            signature=tuple(r.items())
            if signature in seen:continue
            seen.add(signature)
            if not r['product_id'] or ',' in str(r['quantity']) or ',' in str(r['unit_price']):continue
            amount=D(money(D(str(r['quantity']))*D(str(r['unit_price']))));total+=amount;valid+=1
            try:
                day=r['sale_date'] if isinstance(r['sale_date'],date) else date.fromisoformat(r['sale_date'])
                if day<=a:dated+=amount
            except ValueError:pass
        return dict(valid_sales=valid,revenue=money(total),dated_revenue=money(dated))
    checks.equal(quality_totals(qrows),e['quality']['stages']['before'],'independent quality before')
    repaired=[dict(r) for r in qrows]
    quality_spec=next(s for s in m['tables'] if s['id']=='quality:sales')
    for repair,stage in zip(e['quality']['repairs'],['after_thousands','after_decimal','after_date']):
        index=repair['row']-quality_spec['header_row']-1
        field=next(c['canonical_field'] for c in quality_spec['columns'] if c['source_column_index']==repair['column'])
        checks.equal(f"{get_column_letter(repair['column'])}{repair['row']}",repair['cell'],'repair physical coordinate')
        checks.equal(str(repaired[index][field]),repair['before'],'repair original value')
        before=repaired[index][field]
        value=before.replace(',','') if repair['interpretation']=='thousands_comma' else before.replace(',','.') if repair['interpretation']=='decimal_comma' else datetime.strptime(before,'%d/%m/%Y').date().isoformat()
        checks.equal(value,repair['after'],'explicit interpretation result')
        repaired[index][field]=value
        checks.equal(quality_totals(repaired),e['quality']['stages'][stage],'independent quality '+stage)
    checks.equal(quality_totals(qrows),e['quality']['stages']['reversed_all'],'independent quality reversal')
    dlines=tables['demand:sales'];dhero=[r for r in dlines if r['product_id']=='DP-001']
    checks.equal(sum(r['quantity'] for r in dhero),150,'demand hero units')
    checks.equal(len({r['sale_date'] for r in dhero}),30,'demand complete history')
    daily=D(sum(r['quantity'] for r in dhero))/D(30);dh=e['demand']
    checks.equal((D(dh['daily_demand']),dh['reorder_point'],dh['target_stock'],D(dh['days_cover']),dh['suggested_quantity']),(daily,int(daily*10),int(daily*24),D(6)/daily,int(daily*24)-6),'expected demand arithmetic from saved rows')
    for r in tables['demand:inventory']:checks.check('reorder_point' not in r and 'target_stock' not in r,'no source demand thresholds')
    guide=json.loads((root/'challenges/C_commercial/incoming_order_entry_guide.json').read_text(encoding='utf-8'))
    checks.equal(len(guide['supplier_rules']),3,'commercial rules for every inventory product')
    cp=next(p for p in tables['commercial:inventory'] if p['product_id']=='NC-001');cq=next(p for p in tables['commercial:suppliers'] if p['product_id']=='NC-001')
    rule=next(r for r in guide['supplier_rules'] if r['product_id']=='NC-001')
    need=D(cp['target_stock'])-D(cp['stock_quantity']);pack=D(rule['pack_size']);minimum=D(rule['min_order_quantity'])
    from decimal import ROUND_CEILING
    rounded=lambda n:(max(n,minimum)/pack).to_integral_value(rounding=ROUND_CEILING)*pack
    incoming=guide['confirmed_example'];remaining=D(incoming['ordered_quantity'])-D(incoming['received_quantity']);position=D(cp['stock_quantity'])+remaining;net=D(cp['target_stock'])-position
    checks.check(D(cp['stock_quantity'])==18 and position<D(cp['reorder_point']),'incoming position still triggers reorder')
    checks.equal(e['commercial']['stages']['no_policy'],dict(quantity=int(need),cost=money(need*D(str(cq['unit_cost'])))),'expected no-policy commercial arithmetic')
    checks.equal(e['commercial']['stages']['terms_saved'],dict(quantity=int(rounded(need)),cost=money(rounded(need)*D(str(cq['unit_cost'])))),'expected terms arithmetic')
    checks.equal(e['commercial']['stages']['incoming_saved'],dict(physical_stock=cp['stock_quantity'],eligible_incoming=int(remaining),inventory_position=int(position),net_requirement=int(net),quantity=int(rounded(net)),cost=money(rounded(net)*D(str(cq['unit_cost'])))),'expected incoming arithmetic')
    checks.equal(date.fromisoformat(incoming['expected_date']),a+timedelta(days=3),'incoming three days after snapshot')
    for rule in guide['supplier_rules']:
        q=next(p for p in tables['commercial:suppliers'] if p['product_id']==rule['product_id'])
        checks.equal((D(rule['pack_size']),D(rule['min_order_quantity']),rule['lead_time_days']),(D(q['pack_size']),D(q['min_order_quantity']),q['lead_time_days']),'review values agree with quote evidence')
    v={r['product_id']:r for r in tables['version:inventory']};common=set(v)&set(stock_by_id)
    counts=dict(added=len(set(v)-set(stock_by_id)),removed=len(set(stock_by_id)-set(v)),changed=sum(v[k]!=stock_by_id[k] for k in common),unchanged=sum(v[k]==stock_by_id[k] for k in common))
    checks.equal(counts,e['version']['counts'],'stable-key exact diff')
    checks.equal(counts,dict(added=1,removed=1,changed=3,unchanged=36),'required diff')
    checks.equal(e['version']['added'],sorted(set(v)-set(stock_by_id)),'added key list')
    checks.equal(e['version']['removed'],sorted(set(stock_by_id)-set(v)),'removed key list')
    checks.equal(e['version']['changed'],sorted(k for k in common if v[k]!=stock_by_id[k]),'changed key list')
    checks.equal(e['arabic']['revenue'],money(sum((D(str(r['revenue'])) for r in tables['arabic:sales']),D(0))),'Arabic source revenue')
    checks.section('Independent saved-row arithmetic, coverage, comparison windows, history eligibility, risks, draft totals and version diff')


def application_checks(root,m,e,checks,temp_root):
    # Deliberately import services only: sheetpilot.api has a default-store side effect.
    from sheetpilot.store import Store
    from sheetpilot.ingestion import ingest,digest
    from sheetpilot.mapping import review_mapping,discover_relationships
    from sheetpilot.models import MappingInput,ComparisonArgs,DemandParameters,DemandPolicyInput
    from sheetpilot.analytics import dashboard,materialize,records,inventory_tool
    from sheetpilot.agents import run_agents
    from sheetpilot.agent_work import compare_sales,report_text
    from sheetpilot.actions import propose,review_action,fingerprint,procurement_readiness
    from sheetpilot.demand import demand_analysis,save_policy as save_demand
    from sheetpilot.commercial import CommercialInput,SupplierTerm,IncomingInput,preview_policy,save_policy,save_incoming
    from sheetpilot.repairs import RepairPreview,CellRepair,RepairApproval,RepairReversal,repair_workspace,preview_repairs,approve_repairs,preview_reversal,reverse_correction
    from sheetpilot.versions import TablePair,VersionReview,VersionActivation,version_context,preview_version,review_version,activate_version

    store=Store(temp_root/'isolated-store')
    specs={s['id']:s for s in m['tables']}
    def load(prefix):
        ws=store.create_workspace('Validation only: '+prefix)['id'];books={};mapped={}
        selected=[s for s in m['tables'] if s['id'].startswith(prefix+':')]
        for s in selected:
            if s['workbook'] not in books:
                path=root/s['workbook'];books[s['workbook']]=ingest(store,ws,path.name,path.read_bytes())
            book=books[s['workbook']]
            candidates=[t for t in store.list(ws,'table') if t['workbook_id']==book['id'] and t['sheet']==s['sheet'] and t['ref']==s['region']]
            checks.equal(len(candidates),1,'automatic detected exact region '+s['id'])
            t=candidates[0]
            fields={str(c['source_column_index']):c['canonical_field'] for c in s['columns'] if c['canonical_field']}
            mapped[s['id']]=review_mapping(store,ws,t['id'],MappingInput(entity=s['entity'],fields=fields,header_row=s['header_row'],expected_revision=t['revision']))
        return ws,mapped,books
    def confirm(ws,mapped,prefix):
        proposals=discover_relationships(store,ws)
        for requirement in [r for r in m['required_relationships'] if r['left'].startswith(prefix+':')]:
            identifiers={mapped[requirement['left']]['id'],mapped[requirement['right']]['id']}
            candidates=[r for r in proposals if {r['left_table'],r['right_table']}==identifiers and r['field']==requirement['field']]
            checks.equal(len(candidates),1,'required relationship discovered')
            r=candidates[0]
            checks.equal(r['match_mode'],'exact','operational relationship exact')
            checks.equal((r['left_unmatched'],r['right_unmatched']),(0,0),'full exact relationship coverage')
            # Isolated validation fixture review only, never exported as presenter history.
            r['status']='confirmed';store.put(ws,'relationship',r)
        materialize(store,ws)
    def amounts(ws):
        dash=dashboard(store,ws)
        return dict(valid_sales=dash['sales_records'],revenue=next((r['amount'] for r in dash['revenue'] if r['currency']=='EGP'),'0.00'),dated_revenue=money(sum((D(r['revenue']) for r in dash['sales_trend']),D(0))))
    def verify_originals(ws):
        for b in store.list(ws,'workbook'):checks.equal(digest(store.root/'originals'/f"{b['id']}.xlsx"),b['sha256'],'immutable original SHA256')

    ws,mapped,books=load('core')
    stages=e['core']['review_stages']
    before=dashboard(store,ws)
    checks.equal(before['sales_trend'],[],'dates unavailable before required order review')
    checks.equal(before['revenue'],[dict(currency='EGP',amount=e['core']['revenue'])],'line revenue before joins')
    checks.equal(stages['mappings_confirmed_before_links'],dict(revenue=before['revenue'][0]['amount'],sales_lines=before['sales_records'],trend_days=len(before['sales_trend']),dated_demand_eligible=False),'expected pre-link stage')
    confirm(ws,mapped,'core')
    dash=dashboard(store,ws)
    checks.equal(dash['sales_records'],6000,'app valid sales')
    checks.equal(dash['revenue'],[dict(currency='EGP',amount=e['core']['revenue'])],'app revenue no header double-count')
    checks.equal(D(dash['units_sold']),D(e['core']['units']),'app units')
    checks.equal(dash['inventory_products'],40,'app stock identities')
    checks.equal(len(dash['sales_trend']),90,'app all 90 reviewed sales dates')
    checks.equal([p['product_id'] for p in dash['top_products']],[p['product_id'] for p in e['core']['top_products']],'app top products')
    checks.check(not dash['quality_issues'],'core has no quality exclusions or ambiguous joins')
    sales=[r for r in records(store,ws) if r['entity']=='sales']
    checks.check(all(r['data'].get('sale_date') and r['data'].get('product_name') and len(r['source'].get('joins',[]))==2 for r in sales),'reviewed dates/descriptions source joins')
    checks.check(all(len(r['data']['custom_fields'])==3 for r in sales),'three custom sales columns preserved')
    comp=compare_sales(store,ws,ComparisonArgs())
    checks.equal(comp['status'],'completed','comparison complete history')
    checks.equal([(p['from'],p['to']) for p in comp['periods']],[(e['core']['comparison']['previous_from'],e['core']['comparison']['previous_to']),(e['core']['comparison']['current_from'],e['core']['comparison']['current_to'])],'app comparison periods')
    changes={r['product_id']:r for r in comp['product_changes']}
    checks.equal(changes['NC-002']['percent'],'200.00','displayed app growth')
    checks.equal(changes['NC-003']['percent'],'-60.00','displayed app decline')
    demand={p['product_id']:p for p in demand_analysis(store,ws,DemandParameters(as_of=e['as_of']))['products']}
    for pid,case in e['core']['risk_cases'].items():
        p=demand[pid]
        checks.equal(D(p['sales_units']),D(case['units_30d']),pid+' app demand')
        checks.equal(p['eligible'],case['eligible'],pid+' app eligibility')
        checks.equal(p['observed_days'],case['observed_days'],pid+' app observation days')
        if case['daily_demand'] is not None:checks.check(abs(D(p['daily_sales'])-D(case['daily_demand']))<=D('.00005'),pid+' app displayed daily rate')
        if case['days_cover'] is not None:checks.check(abs(D(p['days_remaining'])-D(case['days_cover']))<=D('.00005'),pid+' app displayed cover')
    checks.equal(demand['NC-007']['status'],'no_recent_sales','dormant distinct')
    checks.equal(demand['NC-008']['status'],'limited_history','new product distinct')
    checks.equal(stages['required_links_confirmed'],dict(revenue=dash['revenue'][0]['amount'],trend_days=len(dash['sales_trend']),stock_skus=dash['inventory_products'],hero_daily_units=format(D(demand['NC-001']['daily_sales']).normalize(),'f'),hero_days_cover=format(D(demand['NC-001']['days_remaining']).normalize(),'f')),'expected reviewed-link stage')
    run=run_agents(store,ws,'Validate business checks','guided',None,'daily_review')
    checks.equal(run['origin'],'guided-tools','truthful guided provenance')
    checks.equal([s['tool'] for s in run['steps']],['sales_analysis','sales_comparison','inventory_analysis','procurement_review'],'four sequential real checks')
    checks.equal(len(store.list(ws,'action')),0,'business review creates no purchase')
    checks.equal(run['work']['completed_checks'],4,'real work count')
    checks.equal(stages['business_review'],dict(required_tools=[s['tool'] for s in run['steps']],completed_checks=run['work']['completed_checks'],purchase_proposals_created=len(store.list(ws,'action'))),'expected business-review stage')
    checks.equal(run['work']['sales_rows_in_largest_check'],6000,'real sales work count')
    checks.equal([p['product_id'] for p in run['steps'][2]['result']['priorities'][:2]],['NC-004','NC-001'],'hero visible among highest priorities')
    text=report_text(store,ws,run)
    checks.check('no AI used' in text and 'sales_comparison' in text and 'SHA256' in text,'downloadable truthful real report')
    run2=run_agents(store,ws,'Validate draft preparation','guided',None,'replenishment')
    checks.equal([s['tool'] for s in run2['steps']],['inventory_analysis','draft_purchase_orders'],'purchase job tools')
    action=store.get(ws,'action',run2['action_ids'][0])
    checks.equal(action['status'],'pending','purchase requires human approval')
    checks.equal(action['totals'],[dict(currency='EGP',amount=e['core']['draft_total'])],'app whole proposal total')
    checks.equal(stages['purchase_preparation'],dict(required_tools=[s['tool'] for s in run2['steps']],status=action['status'],line_count=len(action['lines']),total=action['totals'][0]['amount'],output_workbooks=len(list((store.root/'outputs').iterdir()))),'expected pending proposal stage')
    checks.equal(sorted((r['product_id'],r['quantity'],r['line_total']) for r in action['lines']),sorted((r['product_id'],r['quantity'],r['line_total']) for r in e['core']['draft_lines']),'app exact draft lines')
    checks.equal(list((store.root/'outputs').iterdir()),[],'no workbook before approval')
    result=review_action(store,ws,action['id'],'approve','validation-human')
    checks.equal(result['status'],'executed','actual output generated after validation-human approval')
    output=store.root/'outputs'/f"{result['id']}.xlsx"
    b=load_workbook(output);checks.equal(b.sheetnames,['Purchase Orders','Source Trace','Execution'],'real output sheets');b.close()
    checks.equal(review_action(store,ws,action['id'],'approve','validation-human'),result,'repeated approval idempotent')
    checks.equal(len(list((store.root/'outputs').iterdir())),1,'one output only')
    checks.equal(next(r for r in inventory_tool(store,ws) if r['product_id']=='NC-001')['stock_quantity'],'18','original physical stock unchanged')
    checks.equal(stages['after_human_approval'],dict(status=result['status'],output_workbooks=len(list((store.root/'outputs').iterdir())),sheets=['Purchase Orders','Source Trace','Execution'],original_hero_stock=18,repeat_approval_additional_outputs=0),'expected completed proposal stage')
    verify_originals(ws)
    checks.section('Isolated SheetPilot core ingestion, mapping, required joins, analytics, real guided jobs, pending approval, actual Excel and idempotency')

    qw,qt,_=load('quality');checks.equal(amounts(qw),e['quality']['stages']['before'],'quality before')
    corrections=[]
    for repair,stage in zip(e['quality']['repairs'],['after_thousands','after_decimal','after_date']):
        state=repair_workspace(store,qw)
        request=RepairPreview(expected_revision=state['revision'],expected_fingerprint=state['fingerprint'],repairs=[CellRepair(table_id=qt['quality:sales']['id'],row=repair['row'],column=repair['column'],interpretation=repair['interpretation'])])
        prior=amounts(qw)
        prior_records=records(store,qw)
        prior_events=store.events(qw)
        preview=preview_repairs(store,qw,request)
        checks.equal(prior,amounts(qw),'repair preview does not persist totals')
        checks.equal(prior_records,records(store,qw),'repair preview does not persist rows')
        checks.equal(prior_events,store.events(qw),'repair preview does not persist audit')
        saved=approve_repairs(store,qw,RepairApproval(**request.model_dump(),preview_hash=preview['preview_hash'],approved=True),'validation-human')
        corrections.append(saved['corrections'][0]['id'])
        checks.equal(amounts(qw),e['quality']['stages'][stage],'quality '+stage)
    for cid in reversed(corrections):
        state=repair_workspace(store,qw);body=RepairReversal(expected_revision=state['revision'],expected_fingerprint=state['fingerprint'])
        preview=preview_reversal(store,qw,cid,body);body.approved=True;body.preview_hash=preview['preview_hash']
        reverse_correction(store,qw,cid,body,'validation-human')
    checks.equal(amounts(qw),e['quality']['stages']['reversed_all'],'full reversal arithmetic')
    verify_originals(qw)
    checks.section('Isolated SheetPilot thousands/decimal/DMY repair previews, approvals, reversals and original hashes')

    dw,dt,_=load('demand');confirm(dw,dt,'demand')
    checks.check(all(not r['replenishment_configured'] for r in inventory_tool(store,dw)),'demand thresholds missing before policy')
    params=e['demand']['policy'];preview=demand_analysis(store,dw,DemandParameters(**{k:v for k,v in params.items() if k!='stock_snapshot_confirmed'}))
    hero=next(r for r in preview['products'] if r['product_id']=='DP-001')
    for key,expected in [('sales_units',150),('daily_sales',5),('days_remaining',D('1.2')),('reorder_point',50),('target_stock',120),('suggested_quantity',114)]:checks.equal(D(hero[key]),D(expected),'demand preview '+key)
    checks.equal(store.list(dw,'demand_policy'),[],'demand preview no save')
    save_demand(store,dw,DemandPolicyInput(**params,expected_revision=0),'validation-human')
    hero=next(r for r in inventory_tool(store,dw) if r['product_id']=='DP-001')
    checks.equal(hero['threshold_source'],'sales_policy','reviewed demand fallback origin')
    checks.equal(hero['suggested_quantity'],'114','saved policy top-up')
    checks.equal(propose(store,dw,['DP-001'])['lines'][0]['quantity'],'114','demand-based actual proposal')
    checks.section('Isolated SheetPilot demand preview and reviewed policy supplies exact 50/120/114 thresholds and quantity')

    cw,ct,_=load('commercial');confirm(cw,ct,'commercial')
    checks.equal(propose(store,cw,['NC-001'])['lines'][0]['quantity'],'162','unreviewed source packs do not operate')
    terms=[]
    for rule in e['commercial']['rules']:
        args={k:v for k,v in rule.items() if k not in {'supplier_id','quote_sheet'}}
        terms.append(SupplierTerm(**args,inventory_table_id=ct['commercial:inventory']['id'],quote_table_id=ct['commercial:suppliers']['id']))
    body=CommercialInput(expected_revision=0,expected_fingerprint=fingerprint(store,cw),planning_date=e['as_of'],horizon_days=14,terms=terms)
    preview=preview_policy(store,cw,body)
    checks.equal(store.list(cw,'commercial_policy'),[],'commercial preview does not save')
    body.approved=True;body.preview_hash=preview['preview_hash'];save_policy(store,cw,body,'validation-human')
    before=propose(store,cw,['NC-001'])
    checks.equal((before['lines'][0]['quantity'],before['lines'][0]['line_total']),('168','46200.00'),'reviewed pack rounding')
    guide=json.loads((root/'challenges/C_commercial/incoming_order_entry_guide.json').read_text(encoding='utf-8'))
    def record_incoming(values):
        body=IncomingInput(**{k:v for k,v in values.items() if k!='reason'},expected_revision=0,expected_fingerprint=fingerprint(store,cw),request_id=uuid4().hex,inventory_table_id=ct['commercial:inventory']['id'],approved=True)
        return save_incoming(store,cw,body,'validation-human')
    record_incoming(guide['confirmed_example'])
    checks.equal(store.get(cw,'action',before['id'])['status'],'conflicted','incoming change invalidates pending proposal')
    for values in guide['optional_excluded_examples']:record_incoming(values)
    after=propose(store,cw,['NC-001']);line=after['lines'][0]
    checks.equal((line['quantity'],line['line_total']),('120','33000.00'),'incoming-aware pack rounding')
    checks.equal((line['commercial']['eligible_incoming'],line['commercial']['inventory_position'],line['commercial']['net_requirement']),('48','66','114'),'exact incoming basis excludes optional examples')
    checks.equal(len(store.list(cw,'incoming_order')),4,'explicit human fixture entries only')
    review_action(store,cw,after['id'],'approve','validation-human')
    checks.equal(len(store.list(cw,'incoming_order')),4,'generation does not create receipt/order')
    checks.equal(next(r for r in inventory_tool(store,cw) if r['product_id']=='NC-001')['threshold_source'],'source','source threshold precedence with terms')
    verify_originals(cw)
    checks.section('Isolated SheetPilot all-SKU supplier review, 162/168/120 quantities, incoming exclusions, stale proposal and Decimal output')

    # Same core store, candidate uploaded via the actual new-snapshot service argument.
    old=mapped['core:inventory'];parent=books[specs['core:inventory']['workbook']]
    spec=specs['version:inventory'];path=root/spec['workbook']
    candidate=ingest(store,ws,path.name,path.read_bytes(),previous_id=parent['id'])
    new=next(t for t in store.list(ws,'table') if t['workbook_id']==candidate['id'] and t['sheet']==spec['sheet'] and t['ref']==spec['region'])
    new=review_mapping(store,ws,new['id'],MappingInput(entity='inventory',fields=new['fields'],header_row=spec['header_row'],expected_revision=new['revision']))
    body=VersionReview(expected_fingerprint=version_context(store,ws,candidate['id'])['fingerprint'],expected_revision=0,pairs=[TablePair(previous_table_id=old['id'],table_id=new['id'],key_fields=['product_id'])],identifiers_confirmed=True)
    preview=preview_version(store,ws,candidate['id'],body)
    checks.equal(preview['changes'][0]['counts'],e['version']['counts'],'actual SheetPilot stable-key diff')
    reviewed=review_version(store,ws,candidate['id'],body,'validation-human')
    activate_version(store,ws,candidate['id'],VersionActivation(expected_revision=reviewed['revision'],expected_fingerprint=reviewed['fingerprint']),'validation-human')
    checks.equal(dashboard(store,ws)['inventory_products'],40,'one active stock snapshot after activation')
    checks.check(not store.get(ws,'workbook',parent['id'])['active'],'old stock snapshot inactive')
    verify_originals(ws)
    checks.section('Isolated SheetPilot candidate mapping, explicit stable-key review, exact diff and snapshot activation')
    bw,bt,_=load('broader')
    checks.equal(dashboard(store,bw)['sales_records'],0,'broader entities cannot add sales')
    checks.equal(store.list(bw,'incoming_order'),[],'purchase entity does not ingest incoming')
    checks.equal(Counter(r['entity'] for r in records(store,bw)),Counter(e['broader']['entity_counts']),'all broader entity grains retained')
    for r in records(store,bw):
        for field in ['barcode','postal_code','phone']:
            if field in r['data']:checks.check(isinstance(r['data'][field],str) and r['data'][field].startswith('00'),'app retains leading zeroes for '+field)
    aw,at,_=load('arabic');confirm(aw,at,'arabic')
    checks.equal(dashboard(store,aw)['revenue'],[dict(currency='EGP',amount=e['arabic']['revenue'])],'Arabic second-company revenue')
    checks.section('Isolated SheetPilot broader entity preservation and distinct Arabic-company deterministic analytics')


def package(root):
    target=root/'SheetPilot_Demo_Pack.zip'
    files=[p for p in root.rglob('*') if p.is_file() and p!=target and '__pycache__' not in p.parts and p.suffix in {'.xlsx','.py','.md','.json'}]
    with ZipFile(target,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(files):
            info=ZipInfo(p.relative_to(root).as_posix(),(2026,1,1,0,0,0));info.compress_type=ZIP_DEFLATED;info.external_attr=0o600<<16
            z.writestr(info,p.read_bytes())
    return target


def reproduction_checks(root,m,checks):
    from generate_demo_pack import generate
    scratch=root/'.validation-tmp'
    scratch.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='reproduce-',dir=scratch) as folder:
        other=Path(folder)
        generate(other,date.fromisoformat(m['as_of']),m['seed'])
        files=sorted({s['workbook'] for s in m['tables']})+['mapping_manifest.json','expected_results.json','SCENARIO_CARDS.md','RECORDING_GUIDE.md','README.md','challenges/C_commercial/incoming_order_entry_guide.json']
        for relative in files:
            checks.equal(sha256((root/relative).read_bytes()).hexdigest(),sha256((other/relative).read_bytes()).hexdigest(),'byte reproducibility '+relative)
    checks.section('Same date/seed regenerate byte-identical workbooks, manifests, expectations and guides')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack-dir',type=Path,default=Path(__file__).resolve().parent)
    p.add_argument('--app',action='store_true',help='Run actual deterministic services in private temporary stores; no provider')
    p.add_argument('--reproduce',action='store_true',help='Regenerate and compare workbook/document SHA256 hashes')
    args=p.parse_args();root=args.pack_dir.resolve();checks=Checks()
    m=json.loads((root/'mapping_manifest.json').read_text(encoding='utf-8'))
    e=json.loads((root/'expected_results.json').read_text(encoding='utf-8'))
    tables,stats=read_tables(root,m,checks)
    validate_business(root,m,e,tables,checks)
    if args.reproduce:reproduction_checks(root,m,checks)
    if args.app:
        repo=next((p for p in [root,*root.parents,Path.cwd()] if (p/'src/sheetpilot').is_dir()),None)
        if repo is None:raise RuntimeError('--app requires the SheetPilot repository')
        sys.path.insert(0,str(repo/'src'))
        # Keep temporary files under ignored outputs, within the authorized workspace.
        scratch=repo/'outputs'/'demo-pack-validation';scratch.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='isolated-',dir=scratch) as temporary:
            application_checks(root,m,e,checks,Path(temporary))
    result=dict(status='passed',assertions=checks.count,stats=stats,generator_checks='passed',application_integration='passed' if args.app else 'not run',live_meta='not run; no provider calls or credentials used',sections=checks.sections)
    (root/'validation_results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    report=['# Validation results','',f"Result: PASS. {checks.count:,} assertions against saved workbooks and their derived expectations.",'',f"Files: {stats['workbooks']} normal XLSX workbooks. Largest full populated bounding grid: {stats['largest_sheet_grid']:,} cells. All workbook sizes are below 10 MiB. No formulas, macro projects or external links.",'','## Checks actually executed','']
    report += ['- '+s['name']+': passed.' for s in checks.sections]
    report += ['', '## Application and provider boundaries','', 'Application integration: '+result['application_integration']+'.', '', 'Application checks use temporary isolated stores, explicit fixture reviews and real deterministic service functions/guided jobs. No existing application workspace database is opened or populated. All temporary action outputs, reports and review records are discarded, not packaged as a completed demo run.', '', 'Live Meta validation: not run. No provider is instantiated or called and no .env is read by these scripts. For Meta recording, use the real configured provider and show its actual outputs. This report establishes deterministic data/workflow correctness, not successful live Meta semantic proposals or browser footage.', '', 'Reproduce with `python validate_demo_pack.py --pack-dir <pack> --app` from the repository environment. Generator-only validation can run with openpyxl alone. No frontend or native Excel UI automation is claimed here.']
    (root/'VALIDATION_RESULTS.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
    target=package(root)
    print(f'PASS {checks.count:,} assertions. ZIP: {target}',flush=True)


if __name__=='__main__':main()
