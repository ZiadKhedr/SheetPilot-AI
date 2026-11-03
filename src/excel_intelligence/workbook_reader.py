from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

from defusedxml.ElementTree import iterparse
from openpyxl import load_workbook
from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries

from .limits import AnalysisLimits, Deadline, WorkbookInputError


def _area(ref: str) -> tuple[int, int]:
    c1, r1, c2, r2 = range_boundaries(ref)
    if (not all(isinstance(v, int) for v in (r1, c1, r2, c2))
            or not (1 <= r1 <= r2 <= 1_048_576 and 1 <= c1 <= c2 <= 16_384)):
        raise WorkbookInputError("Invalid worksheet range.")
    return r2, c2


def preflight(path: Path, limits: AnalysisLimits, deadline: Deadline):
    """Inspect ZIP metadata and stream XML before allocating OpenPyXL objects."""
    with ZipFile(path) as archive:
        entries = archive.infolist()
        if len(entries) > limits.max_zip_entries:
            raise WorkbookInputError("Workbook exceeds the ZIP entry limit.")
        if len({e.filename for e in entries}) != len(entries):
            raise WorkbookInputError("Workbook contains duplicate ZIP entries.")
        if sum(e.file_size for e in entries) > limits.max_archive_bytes:
            raise WorkbookInputError("Workbook exceeds the expanded archive size limit.")
        for entry in entries:
            if entry.flag_bits & 1 or entry.filename.lower().endswith("vbaproject.bin"):
                raise WorkbookInputError("Encrypted or macro-bearing workbooks are unsupported.")
            if entry.file_size > limits.max_entry_bytes:
                raise WorkbookInputError("Workbook exceeds the expanded entry size limit.")
            if entry.file_size / max(1, entry.compress_size) > limits.max_compression_ratio:
                raise WorkbookInputError("Workbook exceeds the ZIP compression ratio limit.")
        element_count = sheets = total_area = 0
        for entry in entries:
            deadline.check()
            if not entry.filename.lower().endswith((".xml", ".rels")):
                continue
            with archive.open(entry) as stream:
                stack, is_sheet, max_row, max_col, cell_count = [], False, 1, 1, 0
                merged_area = 0
                for event, element in iterparse(stream, events=("start", "end"), forbid_dtd=True):
                    tag = element.tag.rsplit("}", 1)[-1]
                    if event == "start":
                        if not stack:
                            is_sheet = tag == "worksheet"
                        stack.append(element)
                        element_count += 1
                        if element_count > limits.max_xml_elements:
                            raise WorkbookInputError("Workbook exceeds the XML element limit.")
                        if element_count % 1024 == 0:
                            deadline.check()
                        if tag == "sheet" and entry.filename == "xl/workbook.xml":
                            sheets += 1
                            if sheets > limits.max_sheets:
                                raise WorkbookInputError("Workbook exceeds the worksheet limit.")
                        if is_sheet:
                            if tag in {"dimension", "mergeCell"}:
                                r, c = _area(element.attrib["ref"])
                                max_row, max_col = max(max_row, r), max(max_col, c)
                                if tag == "mergeCell":
                                    c1, r1, _, _ = range_boundaries(element.attrib["ref"])
                                    merged_area += (r - r1 + 1) * (c - c1 + 1)
                                    if merged_area > limits.max_cells_per_sheet:
                                        raise WorkbookInputError("Workbook exceeds the merged cell expansion limit.")
                            elif tag == "row":
                                r = int(element.attrib.get("r", max_row))
                                if not 1 <= r <= 1_048_576:
                                    raise WorkbookInputError("Invalid worksheet row.")
                                max_row = max(max_row, r)
                            elif tag == "c":
                                cell_count += 1
                                if "r" in element.attrib:
                                    r, c = coordinate_to_tuple(element.attrib["r"])
                                    _area(element.attrib["r"])
                                    max_row, max_col = max(max_row, r), max(max_col, c)
                            if max_row * max_col > limits.max_cells_per_sheet or cell_count > limits.max_cells_per_sheet:
                                raise WorkbookInputError("Workbook exceeds the worksheet cell limit.")
                    else:
                        stack.pop()
                        if stack:
                            stack[-1].remove(element)
                        element.clear()
                if is_sheet:
                    total_area += max_row * max_col
                    if total_area > limits.max_total_cells:
                        raise WorkbookInputError("Workbook exceeds the total cell limit.")


def open_workbook(path: Path, limits: AnalysisLimits, deadline: Deadline):
    try:
        if not path.is_file():
            raise WorkbookInputError(f"Workbook does not exist or is not a file: {path}")
        if path.suffix.lower() != ".xlsx":
            raise WorkbookInputError("Only .xlsx files are supported in Phase 1.")
        if path.stat().st_size > limits.max_file_size_bytes:
            raise WorkbookInputError("Workbook exceeds the file size limit.")
        preflight(path, limits, deadline)
        deadline.check()
        # Editable mode exposes merges, but the analyzer never saves the workbook.
        workbook = load_workbook(path, read_only=False, data_only=False, keep_links=False)
        try:
            deadline.check()
            areas = [s.max_row * s.max_column for s in workbook.worksheets]
            if len(areas) > limits.max_sheets:
                raise WorkbookInputError("Workbook exceeds the worksheet limit.")
            if any(a > limits.max_cells_per_sheet for a in areas):
                raise WorkbookInputError("Workbook exceeds the worksheet cell limit.")
            if sum(areas) > limits.max_total_cells:
                raise WorkbookInputError("Workbook exceeds the total cell limit.")
        except Exception:
            workbook.close()
            raise
        return workbook
    except WorkbookInputError:
        raise
    except Exception as exc:
        raise WorkbookInputError(f"Could not read workbook: {exc}") from exc


def cell_value(cell):
    value = cell.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def populated_bounds(sheet, deadline=None):
    r1, c1, r2, c2 = sheet.max_row + 1, sheet.max_column + 1, 0, 0
    for row in sheet.iter_rows():
        if deadline:
            deadline.check()
        for cell in row:
            if cell.value is not None:
                r1, c1 = min(r1, cell.row), min(c1, cell.column)
                r2, c2 = max(r2, cell.row), max(c2, cell.column)
    return (r1, c1, r2, c2) if r2 else None


def bounds_ref(bounds):
    if bounds is None:
        return None
    r1, c1, r2, c2 = bounds
    return f"{get_column_letter(c1)}{r1}:{get_column_letter(c2)}{r2}"
