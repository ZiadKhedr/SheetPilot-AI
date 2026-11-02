from pathlib import Path

import pytest
from openpyxl import Workbook


@pytest.fixture
def sample_workbook(tmp_path: Path) -> Path:
    path = tmp_path / "sample.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "مبيعات"
    ws.merge_cells("A1:C1")
    ws["A1"] = "تقرير مبيعات"
    ws.append([])
    ws.append([])
    ws.append(["رقم", "الصنف", "الكمية"])
    ws.append([1, "قلم", 5])
    ws.append([2, "دفتر", 8])
    ws["D5"] = "=SUM(C5:C6)"
    ws.append([])
    ws.append(["SKU", "Qty"])
    ws.append(["A1", 5])
    hidden = wb.create_sheet("Hidden")
    hidden.sheet_state = "hidden"
    hidden.append(["x", "y"])
    hidden.append([1, 2])
    wb.save(path)
    return path
