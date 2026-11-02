"""Inspect actual browser-downloaded workbooks against the independent demo oracle."""
from decimal import Decimal
import json
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]


def validate():
    companies = json.loads((ROOT / "demo_data/manifest.json").read_text(encoding="utf-8"))["companies"]
    results = []
    for company, config in companies.items():
        path = ROOT / "outputs" / f"browser-{company}-purchase-orders.xlsx"
        wb = load_workbook(path, data_only=False)
        assert wb.sheetnames == ["Purchase Orders", "Source Trace", "Execution"]
        rows = list(wb["Purchase Orders"].iter_rows(min_row=2, values_only=True))
        expected = config["expected"]
        assert len(rows) == len(expected["replenishment_lines"])
        quantity = sum(Decimal(str(r[5])) for r in rows)
        total = sum(Decimal(str(r[7])) for r in rows)
        assert quantity == expected["replenishment_quantity"]
        assert total == Decimal(expected["replenishment_total"])
        actual = {r[3]: (Decimal(str(r[5])), Decimal(str(r[7]))) for r in rows}
        for line in expected["replenishment_lines"]:
            assert actual[line["product_id"]] == (Decimal(str(line["quantity"])), Decimal(line["line_total"]))
        assert all(cell.data_type != "f" for row in wb["Purchase Orders"] for cell in row)
        wb.close()
        results.append({"company":company, "file":path.name, "lines":len(rows),
                        "quantity":str(quantity), "total":str(total), "currency":config["currency"], "valid":True})
    (ROOT / "outputs/download-verification.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
    return results


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
