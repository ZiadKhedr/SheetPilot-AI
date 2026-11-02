"""Generate fictional SheetPilot companies; manifest is a fixture oracle, not inference."""
from __future__ import annotations
import argparse
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]

def money(value):
    return f"{Decimal(str(value)):.2f}"

def workbook(directory, filename, sheet_name, title, fields, labels, rows, header_row, first_col, rtl):
    wb = Workbook()
    wb.properties.creator = "SheetPilot synthetic fixture generator"
    wb.properties.created = wb.properties.modified = datetime(2026, 1, 1)
    ws = wb.active
    ws.title = sheet_name
    ws.sheet_view.rightToLeft = rtl
    last_col = first_col + len(fields) - 1
    title_row = max(1, header_row - 3)
    ws.merge_cells(start_row=title_row, start_column=first_col, end_row=title_row, end_column=last_col)
    ws.cell(title_row, first_col, title).font = Font(name="Calibri", size=18, bold=True, color="143E53")
    for c, label in enumerate(labels, first_col):
        cell = ws.cell(header_row, c, label)
        cell.fill = PatternFill("solid", fgColor="143E53")
        cell.font = Font(name="Calibri", bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="right" if rtl else "left")
        ws.column_dimensions[get_column_letter(c)].width = max(18, min(30, len(label) + 3))
    for r, values in enumerate(rows, header_row + 1):
        for c, (field, value) in enumerate(zip(fields, values), first_col):
            cell = ws.cell(r, c, float(value) if isinstance(value, Decimal) else value)
            if isinstance(value, datetime):
                cell.number_format = "yyyy-mm-dd"
            elif field in {"unit_price", "unit_cost", "revenue"} and isinstance(value, (int, float, Decimal)):
                cell.number_format = "#,##0.00"
            if r % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="EDF5F7")
    last_row = header_row + len(rows)
    left, right = get_column_letter(first_col), get_column_letter(last_col)
    ref = f"{left}{header_row}:{right}{last_row}"
    ws.freeze_panes = f"{left}{header_row + 1}"
    ws.auto_filter.ref = ref
    detail_row = last_row + 4
    for r, values in enumerate([["Fixture property", "Value"], ["Source", "Fictional / generated"],
                                 ["Review policy", "Confirm all mappings before use"]], detail_row):
        for c, value in enumerate(values, first_col):
            ws.cell(r, c, value)
    notes = wb.create_sheet("ملاحظات" if rtl else "Notes")
    notes.sheet_state = "hidden"
    notes["A1"] = "Synthetic fixture; unrelated notes and formulas must remain unchanged"
    notes["A3"] = "Data row count"
    notes["B3"] = f"=COUNTA('{sheet_name}'!{left}{header_row + 1}:{left}{last_row})"
    notes["A4"] = "Arithmetic example"
    notes["B4"] = "=SUM(10,20,30)"
    wb.save(directory / filename)
    wb.close()
    return dict(filename=filename, sheet=sheet_name, header_row=header_row, first_column=first_col,
                ref=ref, data_rows=len(rows), hidden_sheet=notes.title,
                columns={str(c): f for c, f in enumerate(fields, first_col)},
                column_labels={str(c): label for c, label in enumerate(labels, first_col)},
                administrative_table_ref=f"{left}{detail_row}:{get_column_letter(first_col + 1)}{detail_row + 2}")

def company(output, key, name, currency, products, transactions, filenames, labels, positions, rtl=False):
    folder = output / key
    folder.mkdir(parents=True, exist_ok=True)
    fields = {
        "sales": ["order_id","product_id","product_name","quantity","unit_price","revenue","sale_date","currency"],
        "inventory": ["product_id","product_name","stock_quantity","reorder_point","target_stock","supplier_id","unit_cost","currency"],
        "suppliers": ["supplier_id","supplier_name","product_id","unit_cost","currency","supplier_email"],
    }
    by_id = {p["id"]: p for p in products}
    sales = []
    for n, (pid, qty, day) in enumerate(transactions, 1):
        p = by_id[pid]
        price = Decimal(p["price"])
        sales.append([f"{key.upper()}-{n:03}",pid,p["name"],qty,price,price * qty,datetime(2026,10,day),currency])
    valid_sales = list(sales)
    duplicated = list(sales[1 if key == "company_a" else 0])
    sales.append(duplicated)
    invalid_money = Decimal("99") if key == "company_a" else Decimal("200")
    sales.append([f"{key.upper()}-MISSING",None,"Needs product review",1,invalid_money,invalid_money,datetime(2026,10,31),currency])
    inventory, suppliers = [], []
    for n, p in enumerate(products):
        inventory.append([p["id"],p["name"],str(p["stock"]) if n == 2 else p["stock"],p["reorder"],
                          p["target"],p["supplier_id"],Decimal(p["cost"]),currency])
        suppliers.append([p["supplier_id"],p["supplier_name"],p["id"],Decimal(p["cost"]),currency,
                          None if n == 2 else f"purchasing-{n+1}@example.invalid"])
    specs = {}
    for entity, rows in [("sales",sales),("inventory",inventory),("suppliers",suppliers)]:
        sheet, row, col = positions[entity]
        specs[entity] = workbook(folder, filenames[entity], sheet, name + " — SYNTHETIC", fields[entity],
                                 labels[entity], rows, row, col, rtl)
    low = [p for p in products if p["stock"] < p["reorder"]]
    replenishment = [dict(product_id=p["id"],product_name=p["name"],stock_quantity=p["stock"],
                          reorder_point=p["reorder"],target_stock=p["target"],quantity=p["target"]-p["stock"],
                          supplier_id=p["supplier_id"],supplier_name=p["supplier_name"],unit_cost=money(p["cost"]),
                          line_total=money((p["target"]-p["stock"])*Decimal(p["cost"])),currency=currency) for p in low]
    revenue = sum(row[5] for row in valid_sales)
    expected = dict(revenue=money(revenue),units_sold=sum(row[3] for row in valid_sales),
                    valid_sales_rows=len(valid_sales),raw_sales_rows=len(sales),duplicate_sales_rows=1,
                    invalid_sales_rows=1,raw_revenue=money(revenue+duplicated[5]+invalid_money),
                    product_count=len(products),inventory_quantity=sum(p["stock"] for p in products),
                    inventory_value=money(sum(p["stock"]*Decimal(p["cost"]) for p in products)),
                    low_stock_count=len(low),replenishment_lines=replenishment,
                    replenishment_quantity=sum(line["quantity"] for line in replenishment),
                    replenishment_total=money(sum(Decimal(line["line_total"]) for line in replenishment)),
                    product_sales=[dict(product_id=p["id"],product_name=p["name"],
                        quantity=sum(row[3] for row in valid_sales if row[1]==p["id"]),
                        revenue=money(sum(row[5] for row in valid_sales if row[1]==p["id"]))) for p in products],
                    relationships=[
                        dict(left_entity="sales",right_entity="inventory",field="product_id",overlap=4,left_coverage=1.0),
                        dict(left_entity="inventory",right_entity="suppliers",field="product_id",overlap=4,left_coverage=1.0)])
    return dict(company_id=key,name=name,currency=currency,fictional=True,files=specs,expected=expected,quality_issues=[
        dict(entity="sales",source_row=specs["sales"]["header_row"]+len(transactions)+1,code="exact_duplicate",
             policy="Extra row has identical order_id and values. Flag for duplicate-policy review."),
        dict(entity="sales",source_row=specs["sales"]["header_row"]+len(sales),code="missing_product_id",
             policy="Quarantine from joined analytics until corrected."),
        dict(entity="inventory",source_row=specs["inventory"]["header_row"]+3,code="numeric_text",
             policy="Validate and normalize numeric string in the operational copy; preserve original."),
        dict(entity="suppliers",source_row=specs["suppliers"]["header_row"]+3,code="missing_optional_email",
             policy="Warn; does not block a local purchase order draft.")])

def generate(output):
    output.mkdir(parents=True,exist_ok=True)
    electronics = [
        dict(id="A001",name="USB-C Hub",price="45",stock=8,reorder=10,target=30,supplier_id="S01",supplier_name="Circuit Harbor Supply",cost="22"),
        dict(id="A002",name="24-inch Monitor",price="180",stock=2,reorder=5,target=12,supplier_id="S02",supplier_name="Bright Pixel Wholesale",cost="110"),
        dict(id="A003",name="Keyboard",price="35",stock=24,reorder=8,target=30,supplier_id="S01",supplier_name="Circuit Harbor Supply",cost="16"),
        dict(id="A004",name="HDMI Cable",price="12",stock=0,reorder=15,target=50,supplier_id="S03",supplier_name="Wireline Components",cost="4.50")]
    restaurant = [
        dict(id="R01",name="دقيق - كيس 25 كجم",price="320",stock=6,reorder=10,target=25,supplier_id="V10",supplier_name="شركة الحصاد للتوريد",cost="260"),
        dict(id="R02",name="زيت - عبوة 5 لتر",price="250",stock=3,reorder=8,target=20,supplier_id="V11",supplier_name="النيل للمواد الغذائية",cost="200"),
        dict(id="R03",name="طماطم - صندوق",price="180",stock=14,reorder=5,target=20,supplier_id="V12",supplier_name="مزارع الصباح",cost="120"),
        dict(id="R04",name="أرز - كيس 10 كجم",price="480",stock=1,reorder=4,target=12,supplier_id="V10",supplier_name="شركة الحصاد للتوريد",cost="390")]
    a = company(output,"company_a","Circuit Harbor Electronics","USD",electronics,
        [("A001",4,1),("A002",2,3),("A003",3,5),("A004",10,10),("A001",2,15),("A002",1,20),("A003",5,25),("A004",4,30)],
        dict(sales="Sales.xlsx",inventory="Inventory.xlsx",suppliers="Suppliers.xlsx"),
        dict(sales=["Order Number","Item Code","Product Description","Units Sold","Selling Price","Net Sales","Transaction Date","Currency"],
             inventory=["SKU","Item Name","Available Units","Reorder At","Target Units","Vendor Code","Purchase Cost","Currency"],
             suppliers=["Supplier Code","Trading Name","Product Reference","Supply Price","Currency","Contact Email"]),
        dict(sales=("Transactions",5,1),inventory=("Warehouse",3,2),suppliers=("Partners",4,3)))
    b = company(output,"company_b","مائدة للمطاعم والتوريد","EGP",restaurant,
        [("R01",8,2),("R02",10,4),("R03",6,7),("R04",5,12),("R01",4,16),("R02",3,21),("R03",2,26),("R04",2,30)],
        dict(sales="Orders.xlsx",inventory="Stock.xlsx",suppliers="Vendors.xlsx"),
        dict(sales=["رقم الطلب","مرجع المنتج","اسم المنتج","الوحدات المباعة","سعر الوحدة","قيمة الطلب","يوم التسليم","العملة"],
             inventory=["رمز المادة","وصف المادة","الرصيد الحالي","حد إعادة الطلب","الرصيد المستهدف","رقم المورد","تكلفة الشراء","عملة التكلفة"],
             suppliers=["معرف المورد","اسم جهة التوريد","كود المادة الغذائية","سعر التوريد","عملة السعر","البريد الإلكتروني"]),
        dict(sales=("طلبات المطاعم",7,2),inventory=("المخزن",4,4),suppliers=("جهات التوريد",6,1)),rtl=True)
    manifest = dict(schema_version="1.0",
        description="Explicit synthetic fixture oracle. Do not import as application semantic inference.",
        duplicate_policy="Review and exclude the extra exact duplicate (including identical order_id); preserve different order IDs.",
        replenishment_policy="When stock_quantity < reorder_point, purchase target_stock - stock_quantity. Historical sales must not be subtracted from a current stock snapshot.",
        companies={c["company_id"]:c for c in (a,b)})
    (output/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return manifest

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",type=Path,default=ROOT/"demo_data")
    manifest = generate(parser.parse_args().output_dir)
    for c in manifest["companies"].values():
        e=c["expected"]
        print(f"{c['company_id']}: revenue {e['revenue']} {c['currency']}; replenish {e['replenishment_quantity']} units / {e['replenishment_total']} {c['currency']}")
