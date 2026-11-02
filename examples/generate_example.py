"""Generate a small, reproducible synthetic workbook, report, and JSON Schema."""
import argparse
import json
from pathlib import Path

from openpyxl import Workbook
from excel_intelligence import analyze_workbook
from excel_intelligence.schemas import WorkbookReport


def generate(directory):
    directory.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    sheet = wb.active
    sheet.title = "Synthetic Sales"
    sheet.merge_cells("A1:C1")
    sheet["A1"] = "Synthetic sales — not company data"
    for r, row in enumerate([["Order ID", "Item", "Qty"], [101, "Pen", 4], [102, "Book", 2],
                             [102, "Book", 2]], 5):
        for c, value in enumerate(row, 1):
            sheet.cell(r, c, value)
    sheet["E5"] = "=SUM(C6:C8)"
    hidden = wb.create_sheet("مخزون")
    hidden.sheet_state = "hidden"
    hidden.append(["كود الصنف", "الكمية"])
    hidden.append(["P1", 12])
    path = directory / "synthetic.xlsx"
    wb.save(path)
    report = analyze_workbook(path)
    (directory / "example-report.json").write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    (directory / "report.schema.json").write_text(
        json.dumps(WorkbookReport.model_json_schema(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).parent)
    generate(parser.parse_args().output_dir)
