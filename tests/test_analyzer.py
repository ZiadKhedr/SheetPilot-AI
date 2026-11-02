import pytest

from excel_intelligence import AnalysisLimits, analyze_workbook
from excel_intelligence.workbook_reader import WorkbookInputError


def test_reports_sheets_tables_formulas_and_coordinates(sample_workbook):
    report = analyze_workbook(sample_workbook)
    assert report.sheet_count == 2
    sales = report.worksheets[0]
    assert sales.state == "visible"
    assert "A1:C1" in sales.merged_ranges
    assert sales.formulas[0].coordinate == "D5"
    assert sales.formulas[0].value == "=SUM(C5:C6)"
    assert len(sales.tables) >= 2
    assert any(t.header_row == 4 for t in sales.tables)
    assert report.worksheets[1].state == "hidden"
    assert sales.tables[0].columns


def test_does_not_modify_original(sample_workbook):
    before = sample_workbook.read_bytes()
    analyze_workbook(sample_workbook)
    assert sample_workbook.read_bytes() == before


def test_enforces_cell_limit(sample_workbook):
    with pytest.raises(WorkbookInputError, match="cell limit"):
        analyze_workbook(sample_workbook, AnalysisLimits(max_cells_per_sheet=1))


def test_rejects_unsupported_extension(tmp_path):
    path = tmp_path / "book.xls"
    path.write_bytes(b"not an xlsx")
    with pytest.raises(WorkbookInputError, match="Only .xlsx"):
        analyze_workbook(path)
