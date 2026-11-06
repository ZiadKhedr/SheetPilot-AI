"""Reproducible synthetic Excel inputs. Python 3.10+ and openpyxl 3.1+ only.

No application imports, environment reads, network, credentials or database writes.
Amounts are calculated with Decimal; XLSX cells contain literals, never formulas.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from hashlib import sha256
import json
from pathlib import Path
import random
import re
import shutil
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter as col

D = Decimal
DEFAULT_DATE = date(2026, 11, 3)
COMPANY = "Nile Circuit Distribution"
FIELDS = {
    "sales": "order_id product_id quantity list_unit_price unit_discount unit_price revenue currency unit_of_measure channel campaign notes".split(),
    "orders": "order_id sale_date customer_id order_total currency order_status".split(),
    "inventory": "product_id product_name stock_quantity reorder_point target_stock supplier_id unit_cost currency unit_of_measure opening_stock stock_reserved warehouse_id".split(),
    "suppliers": "supplier_id supplier_name product_id unit_cost currency supplier_email lead_time_days pack_size min_order_quantity unit_of_measure quote_reference notes".split(),
}
LABELS = {
    "sales": ["Invoice No", "Item Code", "Units Sold", "List Price (EGP)", "Discount per Unit (EGP)", "Net Selling Price (EGP)", "Net Line Amount (EGP)", "Currency", "Base Unit", "Sales Channel", "Campaign Code", "Line Notes"],
    "orders": ["Invoice No", "Invoice Date", "Wholesale Account", "Invoice Total (EGP)", "Currency", "Order Status"],
    "inventory": ["Stock Code", "Item Description", "Physical On Hand (each)", "Reorder Level (each)", "Target Units (each)", "Vendor Code", "Cost per Unit (EGP)", "Currency", "Base Unit", "Opening Balance (each)", "Reserved Units (each)", "Warehouse Code"],
    "suppliers": ["Vendor Code", "Vendor Name", "Product Reference", "Quoted Base Unit Cost (EGP)", "Currency", "Vendor Email", "Delivery Days", "Units per Pack", "MOQ (base units)", "Base Unit", "Quote Reference", "Quote Notes"],
}
CUSTOM = {"channel", "campaign", "notes", "quote_reference"}
GRAINS = {"sales": "one actual sales line", "orders": "one unique sales order header", "inventory": "one current physical stock row per SKU", "suppliers": "one current product-specific supplier quote"}
SUPPLIERS = ["Delta Audio Wholesale", "Cairo Digital Trading", "Alexandria Device Supply", "Giza Peripheral House", "Aswan Cable Works", "Canal Power Trading", "Fayoum Network Supply", "Luxor Office Electronics"]
NAMES = ["Wireless Earbuds", "USB-C Docking Station", "Portable SSD 1TB", "65W GaN Charger", "Wireless Keyboard", "Micro USB Cable", "Legacy VGA Adapter", "Smart Travel Hub", "USB-C Cable 1m", "HDMI Cable 2m", "Ethernet Cable 3m", "Wireless Mouse", "Mouse Pad", "Laptop Stand", "Webcam Cover", "Screen Cleaner", "USB Flash Drive 64GB", "SD Card Reader", "DisplayPort Cable", "Audio Splitter", "USB Extension Cable", "Phone Stand", "Cable Organizer", "HDMI Adapter", "USB-A Hub", "Bluetooth Receiver", "Laptop Sleeve", "RJ45 Coupler", "Headset Adapter", "Power Cable", "Keyboard Cover", "USB-C Connector", "Network Tester", "Travel Plug", "Stylus Pen", "Phone Grip", "Camera Mount", "Microphone Clip", "Dust Blower", "Cable Ties Pack"]


def money(value):
    return str(D(value).quantize(D("0.01"), rounding=ROUND_HALF_UP))


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def canonical_zip(path):
    """Normalize timestamps and member order, including openpyxl's generated ZIP."""
    with ZipFile(path) as archive:
        parts = {n: archive.read(n) for n in archive.namelist()}
    # openpyxl stamps modified at save time; normalize it as well as ZIP metadata.
    parts['docProps/core.xml'] = re.sub(
        rb'(<dcterms:modified\b[^>]*>)[^<]*(</dcterms:modified>)',
        rb'\g<1>2026-01-01T00:00:00Z\g<2>',parts['docProps/core.xml'])
    with ZipFile(path, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(parts.items()):
            info = ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, data)


def table(entity, sheet, rows, header=4, start=1, fields=None, labels=None, keys=None):
    fields = fields or FIELDS[entity]
    return dict(entity=entity, sheet=sheet, rows=rows, header_row=header, first_column=start,
                fields=fields, labels=labels or LABELS.get(entity, [f.replace('_',' ').title().replace(' Id',' ID') for f in fields]),
                exact_keys=keys if keys is not None else {"sales": ["order_id", "notes"], "orders": ["order_id"],
                                   "inventory": ["product_id"], "suppliers": ["product_id"]}.get(entity, []))


def write_book(root, relative, tables, manifest, *, hidden_notes=False, rtl=False):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    book = Workbook()
    book.remove(book.active)
    book.properties.creator = "SheetPilot synthetic business-data generator"
    book.properties.created = book.properties.modified = datetime(2026, 1, 1)
    specs = []
    for t in tables:
        ws = book.create_sheet(t["sheet"])
        ws.sheet_view.showGridLines = False
        ws.sheet_view.rightToLeft = rtl
        h, start, fields = t["header_row"], t["first_column"], t["fields"]
        end = start + len(fields) - 1
        ws.merge_cells(start_row=1, start_column=start, end_row=1, end_column=end)
        title = ws.cell(1, start, COMPANY if not rtl else "شركة منارة للتجهيزات الإلكترونية")
        title.font = Font(name="Arial", size=15, bold=True, color="183448")
        if h >= 4:
            ws.cell(2, start, "Synthetic business records · EGP · " + t["sheet"]).font = Font(name="Arial", size=10, italic=True, color="526576")
        for index, (field, label) in enumerate(zip(fields, t["labels"]), start):
            cell = ws.cell(h, index, label)
            cell.fill = PatternFill("solid", fgColor="183448")
            cell.font = Font(name="Arial", size=10, bold=True, color="FFFFFF")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            width = 35 if field in {"product_name", "supplier_name", "supplier_email", "customer_name", "customer_email", "notes"} else 24 if "price" in field or "cost" in field or "discount" in field else 21
            ws.column_dimensions[col(index)].width = width
        ws.row_dimensions[h].height = 34
        for row_index, record in enumerate(t["rows"], h + 1):
            for index, field in enumerate(fields, start):
                value = record.get(field)
                cell = ws.cell(row_index, index, float(value) if isinstance(value, D) else value)
                cell.font = Font(name="Arial", size=10, color="243746")
                cell.alignment = Alignment(vertical="center", horizontal="right" if isinstance(value, (int, float, D)) else "left")
                if isinstance(value, date):
                    cell.number_format = "yyyy-mm-dd"
                elif isinstance(value, str):
                    cell.number_format = "@"
                elif field == "unit_cost":
                    cell.number_format = '#,##0.00####'
                elif field in {"revenue", "unit_price", "list_unit_price", "unit_discount", "order_total", "payment_amount", "total_cost"}:
                    cell.number_format = '#,##0.00'
                else:
                    cell.number_format = '#,##0' if isinstance(value,int) else '#,##0.00####'
                if row_index % 2 == 0:
                    cell.fill = PatternFill("solid", fgColor="F0F4F7")
        ref = f"{col(start)}{h}:{col(end)}{h + len(t['rows'])}"
        ws.freeze_panes = f"{col(start + 2)}{h + 1}"
        ws.auto_filter.ref = ref
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_options.horizontalCentered = True
        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = ws.PAPERSIZE_A3
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        spec = {k: t[k] for k in ("entity", "sheet", "header_row", "first_column", "exact_keys")}
        spec.update(workbook=relative, region=ref, data_rows=len(t["rows"]), currency="EGP",
                    row_grain=GRAINS.get(t["entity"], "one " + t["entity"] + " record"),
                    columns=[dict(source_column_index=i, source_label=label, header_cell=f"{col(i)}{h}",
                                  canonical_field=None if field in CUSTOM else field,
                                  custom_name=field if field in CUSTOM else None)
                             for i, (field, label) in enumerate(zip(fields, t["labels"]), start)])
        specs.append(spec)
    if hidden_notes:
        notes = book.create_sheet("Internal Notes")
        notes["A1"] = "Administrative notes only. Exclude this sheet from semantic mapping."
        notes["A2"] = "All contacts and business records are fictional."
        notes.sheet_state = "hidden"
    book.save(path)
    book.close()
    canonical_zip(path)
    manifest.setdefault('workbooks',[]).append(dict(path=relative,sha256=sha256(path.read_bytes()).hexdigest(),size_bytes=path.stat().st_size))
    manifest["tables"].extend(specs)
    if hidden_notes:
        manifest["exclude_regions"].append(dict(workbook=relative, sheet="Internal Notes", region="A1:A2", reason="administrative notes"))
    return specs


def products():
    rows = []
    for i, name in enumerate(NAMES, 1):
        cost = D(30 + i * 3)
        stock, reorder, target = 1000, 100, 500
        if i == 1: cost, stock, reorder, target = D(275), 18, 70, 180
        if i == 2: cost, stock, reorder, target = D(1150), 60, 200, 700
        if i == 3: cost, stock, reorder, target = D(1650), 1000, 100, 500
        if i == 4: cost, stock, reorder, target = D(420), 0, 80, 300
        if i == 5: cost, stock, reorder, target = D(250), 600, 60, 300
        if i == 6: cost, stock, reorder, target = D(20), 1000, 20, 60
        if i == 7: cost, stock, reorder, target = D(50), 150, 20, 60
        if i == 8: cost, stock, reorder, target = D(250), 80, 10, 40
        rows.append(dict(product_id=f"NC-{i:03}", product_name=name, stock_quantity=stock,
                         reorder_point=reorder, target_stock=target, supplier_id=f"NCS-{(i-1)%8+1:03}",
                         unit_cost=cost, currency="EGP", unit_of_measure="each", opening_stock=stock+200,
                         stock_reserved=0 if stock == 0 else min(5, stock), warehouse_id="NC-WH-01"))
    return rows


def quotes(stock):
    return [dict(supplier_id=p["supplier_id"], supplier_name=SUPPLIERS[int(p["supplier_id"][-3:])-1],
                 product_id=p["product_id"], unit_cost=p["unit_cost"], currency="EGP",
                 supplier_email=f"quotes-{p['supplier_id'].lower()}@example.invalid",
                 lead_time_days=7 if p["product_id"] == "NC-001" else 5,
                 pack_size=12 if p["product_id"] == "NC-001" else 6,
                 min_order_quantity=48 if p["product_id"] == "NC-001" else 12,
                 unit_of_measure="each", quote_reference=f"Q-2026-{p['product_id']}",
                 notes="Per base unit; review terms") for p in stock]


def sales_line(order, pid, quantity, price, slot, *, day=None):
    record = dict(order_id=order, product_id=pid, quantity=quantity, list_unit_price=D(price)+D(15),
                  unit_discount=D(15), unit_price=D(price), revenue=D(money(D(quantity)*D(price))),
                  currency="EGP", unit_of_measure="each", channel="Wholesale",
                  campaign="DOCK-NOV" if pid == "NC-002" else "STANDARD", notes=f"Line {slot:03}")
    if day is not None:
        record["sale_date"] = day
    return record


def core_records(as_of, seed):
    rng = random.Random(seed)
    stock = products()
    lines, orders = [], []
    counter = 0
    for index in range(90):
        day = as_of - timedelta(days=89-index)
        offset = (as_of-day).days
        count = 14 if index < 30 else 13
        daily = [("NC-001",20,475), ("NC-002",30 if offset < 7 else 10 if offset < 14 else 16,1800),
                 ("NC-003",20 if offset < 7 else 50 if offset < 14 else 40,2400),
                 ("NC-004",25,900), ("NC-005",10,420), ("NC-006",1,45)]
        if offset >= 30: daily.append(("NC-007",10,100))
        if offset in {0,1}: daily.append(("NC-008",2,480))
        while len(daily) < count*5:
            p = rng.choice(stock[8:])
            daily.append((p["product_id"],rng.randint(1,3),p["unit_cost"]+D(65)))
        # Spread special SKUs through the day's orders while keeping five actual lines per order.
        rng.shuffle(daily)
        for j in range(count):
            counter += 1
            oid = f"NC-ORD-{counter:06}"
            chunk = [sales_line(oid, pid, qty, price, slot+1) for slot,(pid,qty,price) in enumerate(daily[j*5:j*5+5])]
            lines.extend(chunk)
            orders.append(dict(order_id=oid,sale_date=day,customer_id=f"NC-CUST-{counter%12+1:04}",
                               order_total=sum((r["revenue"] for r in chunk),D(0)),currency="EGP",order_status="Fulfilled"))
    return lines, orders, stock, quotes(stock)


def summary(lines, orders, stock, supplier_rows, as_of):
    dates = {o["order_id"]: o["sale_date"] for o in orders}
    totals, units, current, previous = defaultdict(D), defaultdict(D), defaultdict(D), defaultdict(D)
    recent, positive, days, source_rows = defaultdict(D), Counter(), defaultdict(set), defaultdict(list)
    for index, r in enumerate(lines):
        pid, day = r["product_id"], dates.get(r["order_id"],r.get("sale_date"))
        totals[pid] += r["revenue"]
        units[pid] += D(r["quantity"])
        source_rows[pid].append(index)
        if as_of-timedelta(days=6) <= day <= as_of: current[pid] += r["revenue"]
        if as_of-timedelta(days=13) <= day <= as_of-timedelta(days=7): previous[pid] += r["revenue"]
        if as_of-timedelta(days=29) <= day <= as_of:
            recent[pid] += D(r["quantity"])
            if r["quantity"] > 0: positive[pid] += 1; days[pid].add(day)
    by_id = {s["product_id"]:s for s in stock}
    quote_by_id = {s["product_id"]:s for s in supplier_rows}
    draft, supplier_totals, cases = [], defaultdict(D), {}
    for p in stock:
        pid = p["product_id"]
        history = [dates.get(lines[i]["order_id"],lines[i].get("sale_date")) for i in source_rows[pid]]
        # SheetPilot clips to first available date in the related sales table,
        # not the first sale of this individual SKU.
        all_dates = [dates.get(r['order_id'],r.get('sale_date')) for r in lines]
        observed = min(30,(as_of-min(all_dates)).days+1) if all_dates else 0
        rate = recent[pid]/observed if observed else D(0)
        eligible = bool(rate and observed>=7 and positive[pid]>=3 and len(days[pid])>=2)
        cases[pid] = dict(product_name=p["product_name"],stock=p["stock_quantity"],units_30d=str(recent[pid]),
                          observed_days=observed,positive_records_30d=positive[pid],positive_days_30d=len(days[pid]),
                          daily_demand=str(rate) if rate else None,
                          days_cover=str(D(p["stock_quantity"])/rate) if rate else None,eligible=eligible,
                          demand_status="no_recent_sales" if not rate else "limited_history" if not eligible else "out_of_stock" if p["stock_quantity"]==0 else "eligible",
                          threshold_origin="source" if p.get("reorder_point") is not None else "missing",
                          first_sale=str(min(history)) if history else None,last_sale=str(max(history)) if history else None,
                          total_positive_records=len(history))
        if p.get("reorder_point") is not None and p["stock_quantity"] < p["reorder_point"]:
            q = p["target_stock"]-p["stock_quantity"]
            quote = quote_by_id[pid]
            amount = D(money(D(q)*quote["unit_cost"]))
            draft.append(dict(product_id=pid,supplier_id=quote["supplier_id"],quantity=str(q),
                              unit_cost=money(quote["unit_cost"]),line_total=money(amount),currency="EGP",threshold_origin="source"))
            supplier_totals[(quote["supplier_id"],"EGP")] += amount
    changes = [dict(product_id=pid,current_revenue=money(current[pid]),previous_revenue=money(previous[pid]),
                    change=money(current[pid]-previous[pid]),
                    percent_change=money((current[pid]-previous[pid])*100/previous[pid]) if previous[pid] else None)
               for pid in by_id]
    changes.sort(key=lambda r:abs(D(r["change"])),reverse=True)
    return dict(counts=dict(sales_lines=len(lines),orders=len(orders),stock_skus=len(stock),suppliers=len({q['supplier_id'] for q in supplier_rows})),
                revenue=money(sum(totals.values(),D(0))),units=str(sum(units.values(),D(0))),currency="EGP",
                top_products=[dict(product_id=pid,name=by_id[pid]["product_name"],units=str(units[pid]),revenue=money(totals[pid]))
                              for pid in sorted(units,key=lambda p:units[p],reverse=True)[:10]],
                comparison=dict(current_from=str(as_of-timedelta(days=6)),current_to=str(as_of),
                                previous_from=str(as_of-timedelta(days=13)),previous_to=str(as_of-timedelta(days=7)),
                                current_revenue=money(sum(current.values(),D(0))),previous_revenue=money(sum(previous.values(),D(0))),
                                products=changes),risk_cases=cases,draft_lines=draft,
                draft_total=money(sum((D(r['line_total']) for r in draft),D(0))),
                draft_by_supplier=[dict(supplier_id=s,currency=c,amount=money(v)) for (s,c),v in sorted(supplier_totals.items())])


def links(prefix, *, orders=False):
    result = [dict(left=f"{prefix}:sales",right=f"{prefix}:inventory",field="product_id",cardinality="many-to-one",purpose="reviewed product descriptions and dated demand"),
              dict(left=f"{prefix}:inventory",right=f"{prefix}:suppliers",field="product_id",cardinality="one-to-one",purpose="product-specific procurement quote")]
    if orders: result.insert(0,dict(left=f"{prefix}:sales",right=f"{prefix}:orders",field="order_id",cardinality="many-to-one",purpose="inherit sale dates without adding order totals to revenue"))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of",type=date.fromisoformat,default=DEFAULT_DATE)
    parser.add_argument("--seed",type=int,default=42)
    parser.add_argument("--output-dir",type=Path,default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if args.as_of < date(1900,4,1) or args.as_of > date.today():
        parser.error("--as-of must support 90 historical days and be no later than today")
    generate(args.output_dir.resolve(),args.as_of,args.seed)


def generate(root, as_of=DEFAULT_DATE, seed=42):
    root.mkdir(parents=True,exist_ok=True)
    manifest = dict(company=COMPANY,as_of=str(as_of),seed=seed,tables=[],exclude_regions=[],required_relationships=[],
                    note="External human review/validation reference. Not an application import or approval record.")
    lines, orders, stock, suppliers = core_records(as_of,seed)
    expected = dict(as_of=str(as_of),seed=seed,core=summary(lines,orders,stock,suppliers,as_of))
    core=expected['core']
    core['review_stages']=dict(
        mappings_confirmed_before_links=dict(revenue=core['revenue'],sales_lines=len(lines),trend_days=0,dated_demand_eligible=False),
        required_links_confirmed=dict(revenue=core['revenue'],trend_days=len({o['sale_date'] for o in orders}),stock_skus=len(stock),hero_daily_units=core['risk_cases']['NC-001']['daily_demand'],hero_days_cover=core['risk_cases']['NC-001']['days_cover']),
        business_review=dict(required_tools=['sales_analysis','sales_comparison','inventory_analysis','procurement_review'],completed_checks=4,purchase_proposals_created=0),
        purchase_preparation=dict(required_tools=['inventory_analysis','draft_purchase_orders'],status='pending',line_count=len(core['draft_lines']),total=core['draft_total'],output_workbooks=0),
        after_human_approval=dict(status='executed',output_workbooks=1,sheets=['Purchase Orders','Source Trace','Execution'],original_hero_stock=stock[0]['stock_quantity'],repeat_approval_additional_outputs=0))
    specs = write_book(root,"core/01_Commerce.xlsx",[table("sales","Sales Lines",lines,4,1),table("orders","Orders",orders,6,2)],manifest,hidden_notes=True)
    specs += write_book(root,"core/02_Warehouse.xlsx",[table("inventory","Current Stock",stock,5,3)],manifest)
    specs += write_book(root,"core/03_Supplier_Quotes.xlsx",[table("suppliers","Supplier Quotes",suppliers,7,2)],manifest)
    for s in specs: s["id"] = "core:"+s["entity"]
    manifest["required_relationships"] += links("core",orders=True)

    quality_fields = "order_id product_id quantity unit_price sale_date currency unit_of_measure".split()
    quality = [dict(zip(quality_fields,r)) for r in [
        ["DQ-001","DQ-A",2,100,as_of,"EGP","each"],
        ["DQ-001","DQ-A",2,100,as_of,"EGP","each"],
        ["DQ-002","DQ-A",3,100,as_of,"EGP","each"],
        ["DQ-003",None,4,100,as_of,"EGP","each"],
        ["DQ-004","DQ-B","1,200",2,as_of,"EGP","each"],
        ["DQ-005","DQ-C",2,"25,50",as_of,"EGP","each"],
        ["DQ-006","DQ-A",1,50,as_of.strftime("%d/%m/%Y"),"EGP","each"],
        ["DQ-007","DQ-D","1200",1,as_of,"EGP","each"],
    ]]
    qspec=write_book(root,"challenges/A_quality/Quality_Repairs.xlsx",[table("sales","Sales",quality,4,2,quality_fields,["Invoice No","Item Code","Units","Net Unit Price","Sale Date","Currency","Base Unit"],keys=[])],manifest)[0]
    qspec["id"]="quality:sales"
    base=sum((D(r["quantity"])*D(r["unit_price"]) for i,r in enumerate(quality) if i in {0,2,6,7}),D(0))
    fixed=base+D(1200)*D(2)+D(2)*D("25.50")
    expected["quality"]=dict(raw_rows=len(quality),exact_duplicates=1,missing_identifier_rows=1,
        stages=dict(before=dict(valid_sales=4,revenue=money(base),dated_revenue=money(base-50)),
                    after_thousands=dict(valid_sales=5,revenue=money(base+2400),dated_revenue=money(base-50+2400)),
                    after_decimal=dict(valid_sales=6,revenue=money(fixed),dated_revenue=money(fixed-50)),
                    after_date=dict(valid_sales=6,revenue=money(fixed),dated_revenue=money(fixed)),
                    reversed_all=dict(valid_sales=4,revenue=money(base),dated_revenue=money(base-50))),
        repairs=[dict(cell="D9",row=9,column=4,interpretation="thousands_comma",before="1,200",after="1200"),
                 dict(cell="E10",row=10,column=5,interpretation="decimal_comma",before="25,50",after="25.50"),
                 dict(cell="F11",row=11,column=6,interpretation="date_dmy",before=as_of.strftime("%d/%m/%Y"),after=str(as_of))],
        duplicate_rows=[5,6],missing_identifier_cell="C8",accepted_numeric_text_cell="D12")

    # Small dated scenario workbooks, each kept in a fresh workspace.
    dated_fields = FIELDS["sales"] + ["sale_date"]
    dated_labels = LABELS["sales"] + ["Sale Date"]
    demand_stock = deepcopy(stock[:3])
    demand_lines=[]
    for i,p in enumerate(demand_stock):
        p.update(product_id=f"DP-{i+1:03}",stock_quantity=[6,100,200][i],reorder_point=None,target_stock=None)
        for day in range(30):
            demand_lines.append(sales_line(f"DP-{i}-{day:03}",p["product_id"],[5,2,1][i],p['unit_cost']+D(80),1,day=as_of-timedelta(days=29-day)))
    ds=write_book(root,"challenges/B_demand/Demand_Policy.xlsx",[
        table("sales","Sales",demand_lines,3,1,dated_fields,dated_labels),
        table("inventory","Current Stock",demand_stock,5,2,fields=[f for f in FIELDS['inventory'] if f not in {'reorder_point','target_stock'}],labels=[l for f,l in zip(FIELDS['inventory'],LABELS['inventory']) if f not in {'reorder_point','target_stock'}]),
        table("suppliers","Supplier Quotes",quotes(demand_stock),7,1)],manifest)
    for s in ds:s["id"]="demand:"+s["entity"]
    manifest["required_relationships"] += links("demand")
    hero_units=sum(r['quantity'] for r in demand_lines if r['product_id']=='DP-001')
    rate=D(hero_units)/30; rp=int((rate*10).to_integral_value(rounding=ROUND_CEILING)); target=int((rate*24).to_integral_value(rounding=ROUND_CEILING))
    expected["demand"]=dict(hero="DP-001",units_30d=hero_units,observed_days=30,daily_demand=str(rate),reorder_point=rp,target_stock=target,days_cover=str(D(6)/rate),suggested_quantity=target-6,
        policy=dict(window_days=30,lead_time_days=7,safety_days=3,review_period_days=14,as_of=str(as_of),stock_snapshot_confirmed=True),
        stages=dict(before_policy="thresholds missing; no purchase",preview="read-only; no policy or proposal",saved="sales_policy thresholds operational; purchase approval separate"))

    commercial_stock=deepcopy(stock[:3]); commercial_quotes=quotes(commercial_stock)
    order_dates={o['order_id']:o['sale_date'] for o in orders}
    commercial_lines=[r|{'sale_date':order_dates[r['order_id']]} for r in lines if r['product_id'] in {'NC-001','NC-002','NC-003'}]
    cs=write_book(root,"challenges/C_commercial/Supplier_Terms.xlsx",[
        table("sales","Sales",commercial_lines,4,1,dated_fields,dated_labels),
        table("inventory","Current Stock",commercial_stock,5,3),
        table("suppliers","Supplier Quotes",commercial_quotes,7,2)],manifest)
    for s in cs:s['id']='commercial:'+s['entity']
    manifest['required_relationships']+=links('commercial')
    review_values=[dict(product_id=q['product_id'],supplier_id=q['supplier_id'],quote_sheet='Supplier Quotes',quote_row=8+i,
                       lead_time_days=q['lead_time_days'],pack_size=str(q['pack_size']),min_order_quantity=str(q['min_order_quantity']),unit_of_measure='each',currency='EGP',price_basis='per_base_unit') for i,q in enumerate(commercial_quotes)]
    incoming=dict(order_reference='EXT-NC-2026-0048',product_id='NC-001',supplier_id='NCS-001',ordered_quantity='48',received_quantity='0',unit_of_measure='each',currency='EGP',ordered_date=str(as_of-timedelta(days=1)),expected_date=str(as_of+timedelta(days=3)),status='confirmed')
    dump(root/'challenges/C_commercial/incoming_order_entry_guide.json',dict(note='Human-entry values only. No application record exists until separately reviewed and saved.',planning_date=str(as_of),horizon_days=14,supplier_rules=review_values,confirmed_example=incoming,
        optional_excluded_examples=[incoming|dict(order_reference='EXCLUDED-OVERDUE',expected_date=str(as_of-timedelta(days=1)),ordered_date=str(as_of-timedelta(days=5)),reason='overdue at snapshot'),incoming|dict(order_reference='EXCLUDED-CANCELLED',status='cancelled',reason='cancelled status'),incoming|dict(order_reference='EXCLUDED-LATE',expected_date=str(as_of+timedelta(days=15)),reason='outside 14-day horizon')]))
    hero=stock[0]; qty=hero['target_stock']-hero['stock_quantity']; rounded=lambda v:int((D(max(v,48))/12).to_integral_value(rounding=ROUND_CEILING))*12
    expected['commercial']=dict(rules=review_values,stages=dict(no_policy=dict(quantity=qty,cost=money(D(qty)*hero['unit_cost'])),terms_saved=dict(quantity=rounded(qty),cost=money(D(rounded(qty))*hero['unit_cost'])),incoming_saved=dict(physical_stock=18,eligible_incoming=48,inventory_position=18+48,net_requirement=180-18-48,quantity=rounded(180-18-48),cost=money(D(rounded(180-18-48))*hero['unit_cost']))))

    v2=deepcopy(stock[:-1])
    for p,delta in zip(v2[:3],[12,-10,25]):p['stock_quantity']+=delta
    extra=deepcopy(stock[-1]);extra.update(product_id='NC-041',product_name='USB-C Cable 2m',stock_quantity=250)
    v2.append(extra);random.Random(seed+1).shuffle(v2)
    vs=write_book(root,'challenges/D_versions/02_Warehouse_v2.xlsx',[table('inventory','Current Stock',v2,5,3)],manifest)[0];vs['id']='version:inventory'
    original={p['product_id']:p for p in stock};updated={p['product_id']:p for p in v2};shared=original.keys()&updated.keys()
    expected['version']=dict(key_fields=['product_id'],added=sorted(updated.keys()-original.keys()),removed=sorted(original.keys()-updated.keys()),changed=sorted(k for k in shared if original[k]!=updated[k]),
        counts=dict(added=len(updated.keys()-original.keys()),removed=len(original.keys()-updated.keys()),changed=sum(original[k]!=updated[k] for k in shared),unchanged=sum(original[k]==updated[k] for k in shared)))

    broader=[table('products','products',[dict(product_id=p['product_id'],product_name=p['product_name'],barcode=f"000620{i:07}",unit_of_measure='each') for i,p in enumerate(stock[:5],1)],3,1,fields=['product_id','product_name','barcode','unit_of_measure'],labels=['Item Code','Description','Barcode','Base Unit'],keys=['product_id']),
        table('customers','customers',[dict(customer_id=f'NC-CUST-{i:04}',customer_name=f'Nile Wholesale Account {i:02}',customer_email=f'account-{i}@example.invalid',postal_code=f'00{i:03}',phone=f'00020{i:06}') for i in range(1,13)],4,2,fields=['customer_id','customer_name','customer_email','postal_code','phone'],keys=['customer_id']),
        table('supplier_directory','supplier_directory',[dict(supplier_id=f'NCS-{i:03}',supplier_name=n,supplier_email=f'office-{i}@example.invalid') for i,n in enumerate(SUPPLIERS,1)],5,3,fields=['supplier_id','supplier_name','supplier_email'],keys=['supplier_id']),
        table('purchases','purchases',[dict(purchase_order_id='EXT-PO-001',product_id='NC-001',supplier_id='NCS-001',quantity=48,unit_cost=D(275),total_cost=D(13200),currency='EGP',purchase_date=as_of-timedelta(days=1),expected_date=as_of+timedelta(days=3))],6,1,fields=['purchase_order_id','product_id','supplier_id','quantity','unit_cost','total_cost','currency','purchase_date','expected_date'],keys=['purchase_order_id']),
        table('payments','payments',[dict(payment_id=f'PAY-{i:03}',order_id=orders[i-1]['order_id'],customer_id=orders[i-1]['customer_id'],payment_amount=orders[i-1]['order_total'],currency='EGP') for i in range(1,4)],7,2,fields=['payment_id','order_id','customer_id','payment_amount','currency'],keys=['payment_id'])]
    bs=write_book(root,'optional/E_mapping/Broader_Entities.xlsx',broader,manifest)
    for s in bs:s['id']='broader:'+s['entity']
    expected['broader']=dict(entity_counts={t['entity']:len(t['rows']) for t in broader},sales_revenue='0.00',incoming_orders=0,relationship_selection='Use core inventory-to-sales enrichment only. Do not confirm an additional products-to-sales enrichment link.')

    arabic_stock=deepcopy(stock[:3])
    for i,p in enumerate(arabic_stock,1):p.update(product_id=f'MN-{i:03}',product_name=['سماعات لاسلكية','محطة توصيل','قرص تخزين محمول'][i-1],supplier_id=f'MNV-{i:03}',stock_quantity=[15,120,250][i-1])
    arabic_quotes=quotes(stock[:3])
    for i,q in enumerate(arabic_quotes,1):q.update(product_id=f'MN-{i:03}',supplier_id=f'MNV-{i:03}',supplier_name=f'مورد منارة {i}',supplier_email=f'manara-{i}@example.invalid')
    arabic_fields=['order_id','product_id','quantity','unit_price','revenue','sale_date','currency','unit_of_measure']
    arabic_lines=[sales_line(f'MN-ORD-{i:03}',f'MN-{i%3+1:03}',3,arabic_stock[i%3]['unit_cost']+D(100),1,day=as_of-timedelta(days=9-i)) for i in range(10)]
    ar=write_book(root,'optional/F_arabic/Manara_Trading.xlsx',[
        table('sales','المبيعات',arabic_lines,3,3,arabic_fields,['رقم الفاتورة','كود الصنف','الكمية المباعة','سعر البيع','اجمالي','تاريخ البيع','العملة','وحدة القياس'],keys=['order_id']),
        table('inventory','المخزون',arabic_stock,5,1,fields=FIELDS['inventory'][:9],labels=['كود الصنف','اسم الصنف','المخزون الحالي','حد إعادة الطلب','الرصيد المستهدف','كود المورد','تكلفة الوحدة','العملة','وحدة القياس']),
        table('suppliers','عروض الموردين',arabic_quotes,7,2,fields=FIELDS['suppliers'][:10],labels=['كود المورد','اسم المورد','كود الصنف','تكلفة الوحدة','العملة','بريد المورد','مدة التوريد','حجم العبوة','حد ادني للطلب','وحدة القياس'])],manifest,rtl=True)
    for s in ar:s['id']='arabic:'+s['entity']
    manifest['required_relationships']+=links('arabic')
    expected['arabic']=dict(company='Manara Electronics Trading',sales_lines=len(arabic_lines),stock_skus=3,currency='EGP',revenue=money(sum((r['revenue'] for r in arabic_lines),D(0))))
    dump(root/'mapping_manifest.json',manifest)
    dump(root/'expected_results.json',expected)
    write_docs(root,manifest,expected)
    # Include the standalone sources in custom output folders as well.
    source=Path(__file__).resolve().parent
    for name in ['generate_demo_pack.py','validate_demo_pack.py']:
        if (source/name).exists() and (source/name).resolve() != (root/name).resolve():shutil.copyfile(source/name,root/name)
    print(f'Generated 9 XLSX workbooks in {root}; run validate_demo_pack.py --app to validate.')
    return manifest,expected


def write_docs(root,manifest,e):
    c=e['core']
    readme=f"""# Nile Circuit sample workbooks

Synthetic EGP business data for evaluating SheetPilot. Historical snapshot: {e['as_of']}.

## Try the core workflow

1. Create a fresh workspace and upload the three workbooks in `core/`.
2. Review the Sales Lines, Orders, Current Stock and Supplier Quotes mappings. Exclude Internal Notes and title rows above the headers.
3. Review exact relationships: Sales Lines to Orders on `order_id`, Sales Lines to Current Stock on `product_id`, and Current Stock to Supplier Quotes on `product_id`.
4. Inspect analytics, run an agent task, then review a pending purchase proposal before approving an additional Excel output.

| Fixture expectation | Result |
| --- | ---: |
| Sales lines | 6,000 |
| Order headers | 1,200 |
| Stock SKUs | 40 |
| Suppliers | 8 |
| Reviewed revenue | EGP {c['revenue']} |
| Purchase draft with source thresholds and no commercial policy | EGP {c['draft_total']} |

These are independent fixture expectations. The application calculates results from reviewed workbooks. `mapping_manifest.json` records source coordinates and required links; `expected_results.json` contains exact calculations and stages. Neither file grants application approval.

## Additional evaluation files

| Folder | Purpose | Workspace |
| --- | --- | --- |
| `challenges/A_quality/` | Numeric/date repair, duplicates and missing identifiers | Fresh |
| `challenges/B_demand/` | Reviewed demand-based ordering settings | Fresh |
| `challenges/C_commercial/` | Supplier terms and separately entered incoming orders | Fresh |
| `challenges/D_versions/` | Stable-key stock snapshot comparison | Core workspace: use New snapshot on the original warehouse workbook |
| `optional/E_mapping/` | Products, customers, supplier directory, purchases and payments | Fresh |
| `optional/F_arabic/` | Independent Arabic company | Fresh |

For demand and supplier planning, use the historical snapshot date above. Supplier-order entry values are in `challenges/C_commercial/incoming_order_entry_guide.json`. Review and save them separately in the app. Imported purchase rows and generated workbooks do not record incoming stock.

## Reproduce and validate

Requires Python 3.10+ and openpyxl 3.1+. From this folder:

```sh
python generate_demo_pack.py --as-of {e['as_of']} --seed {e['seed']} --output-dir ./generated
python validate_demo_pack.py --pack-dir ./generated --reproduce
```

From the repository root with app dependencies installed (Windows):

```powershell
.venv/Scripts/python demo_pack/validate_demo_pack.py --pack-dir demo_pack --app --reproduce
```

On macOS/Linux, use `.venv/bin/python`. Validation writes `VALIDATION_RESULTS.md` and `validation_results.json`. Application checks use isolated temporary stores and deterministic services; these scripts do not configure or call Meta.

All business values are literals. Decimal calculations round money to cents; per-base-unit quotes may retain six decimal places. XLSX timestamps are stable for byte reproducibility. All businesses and contacts are fictional; contact domains use `example.invalid`.
"""
    (root/'README.md').write_text(readme,encoding='utf-8')


if __name__ == '__main__':
    main()
