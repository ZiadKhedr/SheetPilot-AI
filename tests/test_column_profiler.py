from datetime import datetime

from openpyxl import Workbook

from excel_intelligence.column_profiler import profile_columns, typed_key


def profile(rows):
    sheet = Workbook().active
    for row in rows:
        sheet.append(row)
    return profile_columns(sheet, dict(r1=1, r2=sheet.max_row, c1=1, c2=sheet.max_column,
                                      header_row=1, data_start=2))


def test_distinct_values_and_duplicates_use_same_type_policy():
    profiles, duplicates = profile([
        ["Value", "Other"], [1, "x"], ["1", "x"], [True, "x"],
        [1.0, "x"], ["1 ", "x"], ["X", "x"], ["x", "x"],
    ])
    assert profiles[0].distinct_count == 6
    assert profiles[0].inferred_type == "mixed"
    assert duplicates == 1  # Numeric 1 and 1.0 only.


def test_formulas_errors_and_strings_are_distinct():
    sheet = Workbook().active
    for row in [["Formula", "Error"], ["=1+1", "#DIV/0!"], ["=1+1", "#DIV/0!"]]:
        sheet.append(row)
    profiles, duplicates = profile_columns(sheet, dict(r1=1,r2=3,c1=1,c2=2,header_row=1,data_start=2))
    assert profiles[0].inferred_type == "formula"
    assert profiles[1].inferred_type == "error"
    assert duplicates == 1
    sheet["A4"] = "=1+1"
    sheet["A4"].data_type = "s"
    assert typed_key(sheet["A2"]) != typed_key(sheet["A4"])


def test_dates_stay_separate_from_iso_text():
    value = datetime(2026, 1, 2)
    profiles, duplicates = profile([["Date", "ID"], [value, 1], [value.isoformat(), 1]])
    assert profiles[0].distinct_count == 2
    assert profiles[0].inferred_type == "mixed"
    assert duplicates == 0
