from dataclasses import replace
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

from excel_intelligence import AnalysisLimits, analyze_workbook
from excel_intelligence.limits import Deadline, WorkbookInputError
from excel_intelligence import workbook_reader


def rewrite_zip(source, destination, edit):
    with ZipFile(source) as incoming, ZipFile(destination, "w", ZIP_DEFLATED) as outgoing:
        for entry in incoming.infolist():
            outgoing.writestr(entry.filename, edit(entry.filename, incoming.read(entry.filename)))


@pytest.mark.parametrize(("changes", "message"), [
    (dict(max_file_size_bytes=1), "file size"),
    (dict(max_sheets=1), "worksheet limit"),
    (dict(max_cells_per_sheet=1), "cell limit"),
    (dict(max_total_cells=2), "total cell"),
    (dict(max_archive_bytes=1), "expanded archive"),
    (dict(max_entry_bytes=1), "expanded entry"),
    (dict(max_zip_entries=1), "ZIP entry"),
    (dict(max_compression_ratio=1), "compression ratio"),
    (dict(max_xml_elements=1), "XML element"),
])
def test_limits_reject_before_openpyxl(sample_workbook, monkeypatch, changes, message):
    def forbidden(*args, **kwargs):
        pytest.fail("OpenPyXL must not run before rejecting this workbook.")
    monkeypatch.setattr(workbook_reader, "load_workbook", forbidden)
    with pytest.raises(WorkbookInputError, match=message):
        analyze_workbook(sample_workbook, replace(AnalysisLimits(), **changes))


def test_missing_and_corrupt_files(tmp_path):
    with pytest.raises(WorkbookInputError, match="does not exist"):
        analyze_workbook(tmp_path / "missing.xlsx")
    bad = tmp_path / "bad.xlsx"
    bad.write_bytes(b"not a zip")
    with pytest.raises(WorkbookInputError, match="Could not read"):
        analyze_workbook(bad)


def test_actual_cell_coordinates_checked_when_dimension_is_false(sample_workbook, tmp_path, monkeypatch):
    path = tmp_path / "false-dimension.xlsx"
    def edit(name, data):
        if name == "xl/worksheets/sheet1.xml":
            return data.replace(b'r="A1"', b'r="XFD1048576"')
        return data
    rewrite_zip(sample_workbook, path, edit)
    monkeypatch.setattr(workbook_reader, "load_workbook", lambda *a, **k: pytest.fail("Loaded oversized grid"))
    with pytest.raises(WorkbookInputError, match="cell limit"):
        analyze_workbook(path)


def test_dtd_rejected_before_openpyxl(sample_workbook, tmp_path, monkeypatch):
    path = tmp_path / "entity.xlsx"
    def edit(name, data):
        if name == "xl/workbook.xml":
            return b'<!DOCTYPE workbook [<!ENTITY x "data">]>' + data
        return data
    rewrite_zip(sample_workbook, path, edit)
    monkeypatch.setattr(workbook_reader, "load_workbook", lambda *a, **k: pytest.fail("Loaded DTD"))
    with pytest.raises(WorkbookInputError, match="Could not read"):
        analyze_workbook(path)


def test_renamed_macro_workbook_rejected(sample_workbook, tmp_path):
    path = tmp_path / "macro.xlsx"
    rewrite_zip(sample_workbook, path, lambda name, data: data)
    with ZipFile(path, "a") as archive:
        archive.writestr("xl/vbaProject.bin", b"not executable")
    with pytest.raises(WorkbookInputError, match="macro-bearing"):
        analyze_workbook(path)


def test_deadline_is_enforced(monkeypatch):
    from excel_intelligence import limits
    monkeypatch.setattr(limits, "monotonic", lambda: 0)
    deadline = Deadline(1)
    monkeypatch.setattr(limits, "monotonic", lambda: 2)
    with pytest.raises(WorkbookInputError, match="processing time"):
        deadline.check()


@pytest.mark.parametrize("value", [0, -1, True, 1.5])
def test_invalid_resource_limit(value):
    with pytest.raises(ValueError, match="positive integer"):
        AnalysisLimits(max_cells_per_sheet=value)
