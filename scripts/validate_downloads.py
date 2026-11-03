"""Inspect actual browser-downloaded workbooks against the independent demo oracle."""
from decimal import Decimal
import argparse
from hashlib import sha256
import json
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]


def validate(directory=None):
    directory = directory or ROOT / "frontend/test-results"
    companies = json.loads((ROOT / "demo_data/manifest.json").read_text(encoding="utf-8"))["companies"]
    results = []
    for company, config in companies.items():
        matches = list(directory.rglob(f"browser-{company}-purchase-orders.xlsx"))
        assert len(matches) == 1, f"Expected one {company} browser download under {directory}; found {len(matches)}."
        path = matches[0]
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
        assert all(r[8] == config["currency"] for r in rows)
        assert wb["Source Trace"].max_row == 1 + len(rows)*2
        files = {f["filename"]:f for f in config["files"].values()}
        for product, filename, recorded_hash, sheet, row, region in list(wb["Source Trace"].values)[1:]:
            mapping = files[filename]
            source = ROOT/"demo_data"/company/mapping["filename"]
            assert sha256(source.read_bytes()).hexdigest() == recorded_hash
            assert (sheet,region) == (mapping["sheet"],mapping["ref"])
            column = next(int(k) for k,v in mapping["columns"].items() if v == "product_id")
            source_book = load_workbook(source, read_only=True, data_only=False)
            try:
                assert source_book[sheet].cell(row, column).value == product
            finally:
                source_book.close()
        assert all(cell.data_type != "f" for sheet in wb for row in sheet for cell in row)
        wb.close()
        results.append({"company":company, "file":path.name, "lines":len(rows),
                        "quantity":str(quantity), "total":str(total), "currency":config["currency"], "valid":True})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--downloads", type=Path, help="Directory containing both browser downloads")
    print(json.dumps(validate(parser.parse_args().downloads), indent=2))
