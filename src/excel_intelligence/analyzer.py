from __future__ import annotations

from pathlib import Path

from .column_profiler import profile_columns
from .schemas import CellValue, TableRegion, WorkbookReport, WorksheetReport
from .limits import AnalysisLimits, Deadline
from .structure_detector import detect_regions
from .workbook_reader import WorkbookInputError, bounds_ref, cell_value, open_workbook, populated_bounds


def analyze_workbook(path: str | Path, limits: AnalysisLimits | None = None) -> WorkbookReport:
    path = Path(path)
    limits = limits or AnalysisLimits()
    deadline = Deadline(limits.max_processing_seconds)
    workbook = open_workbook(path, limits, deadline)
    try:
        reports = []
        for sheet in workbook.worksheets:
            deadline.check()
            bounds = populated_bounds(sheet, deadline)
            populated, formulas = [], []
            row_counts, col_counts = {}, {}
            warnings = []
            for row in sheet.iter_rows():
                deadline.check()
                for cell in row:
                    if cell.value is None:
                        continue
                    row_counts[cell.row] = row_counts.get(cell.row, 0) + 1
                    col_counts[cell.column] = col_counts.get(cell.column, 0) + 1
                    item = CellValue(coordinate=cell.coordinate, value=cell_value(cell), data_type=cell.data_type)
                    if cell.data_type == "f":
                        formulas.append(item)
                    if len(populated) < limits.max_populated_cells_reported:
                        populated.append(item)
            if sum(row_counts.values()) > limits.max_populated_cells_reported:
                warnings.append(f"Populated cell detail truncated at {limits.max_populated_cells_reported} cells.")
            blank_rows, blank_cols, table_regions = [], [], []
            if bounds:
                r1, c1, r2, c2 = bounds
                blank_rows = [r for r in range(r1, r2 + 1) if row_counts.get(r, 0) == 0]
                blank_cols = [c for c in range(c1, c2 + 1) if col_counts.get(c, 0) == 0]
                for i, region in enumerate(detect_regions(sheet, bounds, deadline), 1):
                    deadline.check()
                    columns, duplicate_count = profile_columns(sheet, region, limits.sample_values_per_column, deadline)
                    table_regions.append(TableRegion(id=f"{sheet.title}-table-{i}", ref=region["ref"],
                        header_row=region["header_row"], header_confidence=region["header_confidence"],
                        confidence=region["confidence"], row_count=region["r2"]-region["r1"]+1,
                        ambiguous=region["ambiguous"], header_candidates=region["header_candidates"],
                        evidence=region["evidence"],
                        column_count=region["c2"]-region["c1"]+1, columns=columns,
                        warnings=region["warnings"], duplicate_data_row_count=duplicate_count))
            reports.append(WorksheetReport(title=sheet.title, state=sheet.sheet_state,
                dimensions=sheet.calculate_dimension(), populated_range=bounds_ref(bounds),
                populated_cell_count=sum(row_counts.values()), blank_rows=blank_rows,
                blank_columns=blank_cols, merged_ranges=[str(r) for r in sheet.merged_cells.ranges],
                formulas=formulas, populated_cells=populated, tables=table_regions, warnings=warnings))
        deadline.check()
        return WorkbookReport(file_name=path.name, file_size_bytes=path.stat().st_size,
                              sheet_count=len(reports), worksheets=reports)
    finally:
        workbook.close()


__all__ = ["AnalysisLimits", "WorkbookInputError", "analyze_workbook"]
