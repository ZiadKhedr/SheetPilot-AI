from openpyxl import Workbook

from excel_intelligence import analyze_workbook


def save_rows(tmp_path, rows, start=1):
    workbook = Workbook()
    sheet = workbook.active
    for r, values in enumerate(rows, start):
        for c, value in enumerate(values, 1):
            sheet.cell(r, c, value)
    path = tmp_path / "layout.xlsx"
    workbook.save(path)
    return path


def test_text_only_table_keeps_data_and_reports_ambiguity(tmp_path):
    path = save_rows(tmp_path, [["Code", "Name"], ["A", "Alpha"], ["B", "Beta"]])
    table = analyze_workbook(path).worksheets[0].tables[0]
    assert table.header_row == 1
    assert table.ref == "A1:B3"
    assert [c.non_empty_count for c in table.columns] == [2, 2]
    assert table.ambiguous and table.warnings
    assert len(table.header_candidates) == 2
    assert all(c.evidence for c in table.header_candidates)
    assert table.header_confidence <= .6


def test_header_on_row_five_and_missing_values(tmp_path):
    path = save_rows(tmp_path, [["ID", "Qty"], [1, 3], [2, None], [3, 7]], start=5)
    sheet = analyze_workbook(path).worksheets[0]
    table = sheet.tables[0]
    assert table.ref == "A5:B8" and table.header_row == 5
    assert table.columns[1].coordinate == "B5"
    assert table.columns[1].missing_count == 1
    assert table.columns[1].non_empty_count == 2
    assert not table.ambiguous


def test_numeric_table_without_header_includes_all_rows(tmp_path):
    path = save_rows(tmp_path, [[1, 2], [3, 4], [5, 6]])
    table = analyze_workbook(path).worksheets[0].tables[0]
    assert table.header_row is None and table.ambiguous
    assert table.columns[0].header is None
    assert table.columns[0].non_empty_count == 3


def test_side_by_side_tables_and_blank_columns(tmp_path):
    path = save_rows(tmp_path, [
        ["ID", "Qty", None, "Product", "Cost"],
        [1, 2, None, "A", 10],
        [2, 4, None, None, None],
    ])
    sheet = analyze_workbook(path).worksheets[0]
    assert sheet.blank_columns == [3]
    assert [t.ref for t in sheet.tables] == ["A1:B3", "D1:E2"]


def test_blank_rows_separate_tables(tmp_path):
    path = save_rows(tmp_path, [["ID", "Qty"], [1, 2], [None, None], ["SKU", "Cost"], ["A", 9]])
    sheet = analyze_workbook(path).worksheets[0]
    assert sheet.blank_rows == [3]
    assert [t.ref for t in sheet.tables] == ["A1:B2", "A4:B5"]


def test_merged_title_is_not_header(tmp_path):
    path = save_rows(tmp_path, [["Report", None, None], ["ID", "Qty", "Cost"], [1, 2, 3], [2, 3, 4]])
    from openpyxl import load_workbook
    wb = load_workbook(path)
    wb.active.merge_cells("A1:C1")
    wb.save(path)
    sheet = analyze_workbook(path).worksheets[0]
    assert sheet.merged_ranges == ["A1:C1"]
    assert sheet.tables[0].header_row == 2
    assert sheet.tables[0].ref == "A2:C4"


def test_duplicate_headers_preserved_as_source_labels(tmp_path):
    path = save_rows(tmp_path, [["ID", "Qty", "Qty"], [1, 2, 3], [2, 3, 4]])
    table = analyze_workbook(path).worksheets[0].tables[0]
    assert [c.header for c in table.columns] == ["ID", "Qty", "Qty"]
    assert [c.coordinate for c in table.columns] == ["A1", "B1", "C1"]


def test_empty_and_very_hidden_sheets(tmp_path):
    wb = Workbook()
    wb.create_sheet("private").sheet_state = "veryHidden"
    path = tmp_path / "empty.xlsx"
    wb.save(path)
    report = analyze_workbook(path)
    assert report.worksheets[0].populated_range is None
    assert report.worksheets[0].tables == []
    assert report.worksheets[1].state == "veryHidden"
