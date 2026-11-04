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
    print(f'Generated 9 XLSX workbooks in {root}; run validate_demo_pack.py --app to validate and package.')
    return manifest,expected


def write_docs(root,manifest,e):
    c=e['core']; a=e['as_of']; lookup={s['id']:s for s in manifest['tables']}
    def refs(pid):
        lines,orders,stock,_=core_records(date.fromisoformat(a),e['seed'])
        index=next(i for i,p in enumerate(stock) if p['product_id']==pid)
        row=index+6
        first=[(i,r) for i,r in enumerate(lines) if r['product_id']==pid][:3]
        samples=[f"'Sales Lines'!A{i+5}:L{i+5}" for i,r in first]
        order_indices={o['order_id']:i for i,o in enumerate(orders)}
        order_cells=[f"'Orders'!B{order_indices[r['order_id']]+7}:D{order_indices[r['order_id']]+7}" for i,r in first]
        return f"02_Warehouse.xlsx 'Current Stock'!C{row}:N{row}; 01_Commerce.xlsx " + ', '.join(samples+order_cells) + f"; 03_Supplier_Quotes.xlsx 'Supplier Quotes'!B{index+8}:M{index+8}"
    stories={'NC-001':'Urgent fast mover: 600 units / 30 days = 20 per day. Stock 18 gives 0.9 days. Core top-up 162 at EGP 275 = 44,550.00.',
             'NC-002':'Dock campaign growth: current seven-day quantity is three times previous, fixed EGP 1,800 net price. Revenue +200%.',
             'NC-003':'SSD decline: current seven-day quantity is 40% of previous, fixed EGP 2,400 net price. Revenue -60%.',
             'NC-004':'Out of stock with 25 units per day of dated historical demand. Source top-up 300.',
             'NC-005':'Healthy stock: 600 physical units against 10 units per day. No source-rule purchase.',
             'NC-006':'Overstocked slow seller: 1,000 physical units against one unit per day. No source-rule purchase.',
             'NC-007':'Older sales history, no last-30-day sales. No recent demand estimate or confirmed zero-demand claim.',
             'NC-008':'New SKU: exactly two positive records on two days. Insufficient history cannot supply demand thresholds.'}
    cards=['# Scenario cards','',f'Company: {COMPANY}. Historical snapshot: {a}. All quantities are base units (`each`).','']
    for pid,story in stories.items():
        tool='Sales Agent / sales_comparison' if pid in {'NC-002','NC-003'} else 'Inventory Agent / inventory_analysis'
        cards += [f'## {pid} — {c["risk_cases"][pid]["product_name"]}','',story,'',f'Sources: {refs(pid)}.', '',f'Responsible specialist/tool: {tool}. Human step: confirm mappings and exact links. Procurement Agent / draft_purchase_orders creates a pending proposal only. Review quantities and supplier evidence before approving any output.','']
    cards += ['## Challenge source coordinates','', 'A_quality / Quality_Repairs.xlsx, Sales: duplicate B5:H5 copied exactly to B6:H6. C8 is missing product ID. D9 requires thousands-comma interpretation. E10 requires decimal-comma interpretation. F11 requires DMY interpretation. D12 contains accepted numeric text `1200`.', '',
              'B_demand / Demand_Policy.xlsx: DP-001 Sales A4:M33; Current Stock B6:K6; Supplier Quotes A8:L8. Inventory Agent uses reviewed 30-day history; save the explicit demand policy to make calculated thresholds operational.', '',
              'C_commercial / Supplier_Terms.xlsx: NC-001 Current Stock C6:N6; Supplier Quotes B8:M8. Procurement Agent uses only saved supplier rules and separately saved incoming records. See incoming_order_entry_guide.json for every SKU rule.', '',
              'D_versions / 02_Warehouse_v2.xlsx: use product_id, not row number. One added, one removed, three changed and 36 unchanged. The manifest and expected_results.json list keys.','']
    (root/'SCENARIO_CARDS.md').write_text('\n'.join(cards),encoding='utf-8')
    quality=e['quality']['stages']
    guide=f'''# Recording guide

Use a new workspace named Nile Circuit Distribution. Upload only core/01_Commerce.xlsx, core/02_Warehouse.xlsx and core/03_Supplier_Quotes.xlsx. Default as-of date: {a}. These are historical snapshot facts. Set the demand estimate stock date to {a} if needed. Use an already configured real Meta provider for Meta footage. Generation and validation do not configure or call Meta. Guided tools are labeled no AI.

## Main story (6 minutes 30 seconds)

| Time | Screen and action | Evidence and concise narration |
|---|---|---|
| 0:00–0:40 | Excel File Manager: upload the three core files. Structure Explorer: open Sales Lines, Orders, Current Stock and Supplier Quotes. | Show offset headers and source coordinates. Exclude the hidden Internal Notes sheet, and exclude title/subtitle rows above each manifest header. No administrative table belongs in analytics. |
| 0:40–2:00 | Mapping Review: request actual Meta proposals, then inspect each mapping. | Net Selling Price is unit_price, List Price is list_unit_price, Discount per Unit is unit_discount, Net Line Amount is revenue. Physical On Hand is stock_quantity; opening and reserved quantities are separate. Orders is order-header grain; Invoice Total maps to order_total. Leave Sales Channel, Campaign Code, Line Notes, Quote Reference and Quote Notes as preserved custom columns. Confirm the four operational mappings. |
| 2:00–2:30 | Mapping Review: discover relationships; review three exact links. | Sales Lines–Orders on order_id (many-to-one), Sales Lines–Current Stock on product_id (many-to-one), Current Stock–Supplier Quotes on product_id (one-to-one). Check entity, field, exact overlap, cardinality and unmatched IDs. Do not accept every candidate. Dates and descriptions now flow through reviewed joins. |
| 2:30–3:20 | Overview, then Business Analytics. | Revenue EGP {c['revenue']}, {c['units']} units, 6,000 sales lines, 1,200 headers and 40 stock SKUs. Order totals do not double revenue. Show seven-day comparison anchored to latest reviewed sale: {c['comparison']['current_from']}–{c['comparison']['current_to']} versus {c['comparison']['previous_from']}–{c['comparison']['previous_to']}. NC-002 +200%, NC-003 -60%. Show NC-001 at 20/day and 0.9 days cover, plus NC-004 out of stock. |
| 3:20–4:25 | Agent Workspace: select Meta mode and Review the business. | Wait for the real run. Show Sales Agent sales_analysis and sales_comparison, Inventory Agent inventory_analysis, Procurement Agent procurement_review: four sequential tool checks, actual status/runtime/work counts/source evidence. Download the text work report. This review creates no purchase proposal. Narration: Meta selects typed tools; Python calculates the numbers. |
| 4:25–5:25 | Agent Workspace: Prepare purchase drafts in Meta mode. Open Approval Center. | Show actual inventory_analysis and draft_purchase_orders steps. Inspect the pending proposal, supplier IDs, currency, quantity and sources. With commercial policy disabled NC-001 is 162 units, EGP 44,550.00. Quoted packs/MOQ alone do not round it. Full core proposal is EGP {c['draft_total']}; exact lines and supplier subtotals are in expected_results.json. |
| 5:25–6:30 | Approval Center: approve once; download. Inspect Purchase Orders, Source Trace and Execution sheets. Activity Timeline: show real execution. | The approved output is an additional workbook. Reopen the same completed proposal: the same output is returned, with no second execution. Download/open the original warehouse file: NC-001 remains 18. Narration: the human approves workbook generation; no supplier order is sent and no receipt is recorded. |

Do not promise a fixed provider response time. Cut quiet waiting in editing without fabricating progress or logs. Only describe reconnection/recoverability if actually observed in a real run. A worker interruption requires explicit review/retry; no promise of automatic replay.

## Three paste-ready custom requests (Meta mode)

1. Compare NC-002 and NC-003 separately over the latest seven calendar days versus the preceding seven. Use sales_comparison with exact product IDs and show source evidence.
2. Use inventory_analysis for NC-001. Explain its dated demand, stock cover, source thresholds and quantity basis.
3. Use inventory_analysis and draft_purchase_orders for NC-001 only. Prepare a pending purchase draft with quantity, supplier, EGP total and sources for my review.

The comparison tool accepts one product scope per call. The first request requires separate scoped calls. If a provider request fails, show its actual error, review the connection and explicitly retry. Guided/no-AI results must never be presented as Meta results.

## Optional A: data quality and reversible repair (fresh workspace)

Upload only challenges/A_quality/Quality_Repairs.xlsx. Map Sales with explicit sale_date. B5:H5 and B6:H6 are exact duplicates, including invoice ID. Another DQ-A order is a valid independent sale. C8 has no product ID and remains excluded. D12 `1200` is already usable numeric text.

Data quality repairs: preview D9 as thousands_comma (`1,200` to 1200), approve. Preview E10 as decimal_comma (`25,50` to 25.50), approve. Preview F11 as date_dmy ({date.fromisoformat(a).strftime('%d/%m/%Y')} to {a}), approve. Revenue stages: EGP {quality['before']['revenue']} → {quality['after_thousands']['revenue']} → {quality['after_decimal']['revenue']} → {quality['after_date']['revenue']}. Dated trend revenue stages: {quality['before']['dated_revenue']} → {quality['after_thousands']['dated_revenue']} → {quality['after_decimal']['dated_revenue']} → {quality['after_date']['dated_revenue']}. An invalid date retains revenue but omits it from trends. Reverse the three corrections in reverse order using preview and human approval; revenue returns to {quality['reversed_all']['revenue']}, with original files preserved. No formula repair or unsupported identifier guess is involved.

## Optional B: demand ordering policy (fresh workspace)

Upload only challenges/B_demand/Demand_Policy.xlsx, confirm Sales, Current Stock and Supplier Quotes, then confirm the two exact product links in the manifest. Business Analytics: Change settings, stock date {a}; More settings: 30-day lookback, 7 delivery days, 3 safety days, 14 extra stock days. Update estimate previews only. DP-001 has 150 units / 30 days = 5/day, stock 6, cover 1.2 days, reorder 50, target 120 and top-up 114. Explicitly acknowledge comparable base units and alignment with the physical stock snapshot, then Save ordering settings. Only then prepare purchase drafts and separately approve output. Source thresholds take precedence wherever present. Call this a trailing-average scenario, never an ML forecast or a guaranteed stockout date.

## Optional C: supplier terms and incoming orders (fresh workspace)

Upload only challenges/C_commercial/Supplier_Terms.xlsx. Confirm its three mappings and two exact product links. Open Supplier planning. Set planning date {a} and horizon 14. Review and enter ALL three SKU rules from incoming_order_entry_guide.json; select the matching quote, per-base-unit prices, units and EGP. Preview, acknowledge and save. NC-001 changes from 162 to 168 units (14 packs of 12), EGP 46,200.00.

Incoming orders: explicitly enter and confirm the 48-unit unreceived external order in the JSON guide, expected {date.fromisoformat(a)+timedelta(days=3)}. Position becomes 18 + 48 = 66, below reorder 70. Net requirement 180 - 66 = 114; ten packs produce 120 units, EGP 33,000.00. Optional overdue, cancelled and day-15 examples do not count. A generated workbook or imported purchases table does not record incoming stock. Save all rule/receipt changes before preparing a fresh proposal; data changes can invalidate a pending one. Use an NC-001-scoped custom request to isolate the hero line if desired.

## Optional D: new stock snapshot (after purchase footage or fresh core workspace)

File Manager: select the original warehouse file, choose New snapshot and upload challenges/D_versions/02_Warehouse_v2.xlsx. Do not upload it as an independent active inventory file. Confirm the candidate mapping. Preview changes with product_id as the stable key, explicitly save the identifier/key review, then activate the candidate. Expected: 1 added (NC-041), 1 removed (NC-040), 3 changed (NC-001/002/003), 36 unchanged. Row movement alone is unchanged. Only the active snapshot contributes; old originals remain downloadable. Review links against the new mapping. Previous findings/pending proposals may become stale. The added SKU intentionally lacks a quote until separately reviewed; do not continue core procurement claims after this update.

## Optional E/F: broader entities and Arabic mapping

E_mapping/Broader_Entities.xlsx is a small entity-preservation showcase in a separate workspace. Map products, customers, supplier_directory, purchases and payments to their own entities. Standalone sales revenue is zero, and no incoming order is created. It does not implement CRM, receivables or automatic purchase ingestion. A supplier directory cannot replace product-specific quotes. If showing this alongside a deliberately extended core workspace, retain inventory-to-sales enrichment and do not also confirm product-master-to-sales enrichment, which can create ambiguous inherited context.

F_arabic/Manara_Trading.xlsx belongs to a separate company/workspace, Manara Electronics Trading, with MN-/MNV- IDs and EGP. Confirm the Arabic tables and two exact product links. Its expected revenue is EGP {e['arabic']['revenue']}. Do not load a translated second copy of core data into the main workspace.
'''
    (root/'RECORDING_GUIDE.md').write_text(guide,encoding='utf-8')
    readme='''# SheetPilot AI synthetic demo pack

Start with RECORDING_GUIDE.md. Upload only the three core/*.xlsx files into a clean workspace. Every challenge/optional folder is a separate workspace unless the version guide explicitly uses New snapshot. Mapping and relationship references do not grant application approval.

Requires Python 3.10+ and openpyxl 3.1+. Reproduce:

```powershell
python generate_demo_pack.py --as-of 2026-11-03 --seed 42 --output-dir ./generated
python validate_demo_pack.py --pack-dir ./generated --reproduce
```

From the SheetPilot repository with its app dependencies installed:

```powershell
.venv/Scripts/python demo_pack/validate_demo_pack.py --pack-dir demo_pack --app --reproduce
```

Validation writes VALIDATION_RESULTS.md and validation_results.json, then packages SheetPilot_Demo_Pack.zip. The ZIP contains the workbooks, Python sources, manifests and guides. All XLSX archives and package entries use stable timestamps for byte reproducibility. No application fixtures are changed. Provider configuration/live Meta validation is outside the generator and validator.

All Excel business values are literals. Decimal arithmetic uses ROUND_HALF_UP to cents. Quotes are per base unit and may retain six decimal places. Source coordinates are recorded in the mapping manifest and scenario cards. Synthetic contacts use example.invalid. No real personal data is included.
'''
    (root/'README.md').write_text(readme,encoding='utf-8')


if __name__ == '__main__':
    main()
