"""Validated resource limits and cooperative processing deadline."""
from dataclasses import dataclass, fields
from time import monotonic


class WorkbookInputError(ValueError):
    """Invalid, unsupported, or over-limit workbook input."""


@dataclass(frozen=True)
class AnalysisLimits:
    max_file_size_bytes: int = 25 * 1024 * 1024
    max_sheets: int = 100
    max_cells_per_sheet: int = 1_000_000
    max_total_cells: int = 2_000_000
    max_populated_cells_reported: int = 100_000
    sample_values_per_column: int = 5
    max_archive_bytes: int = 100 * 1024 * 1024
    max_entry_bytes: int = 50 * 1024 * 1024
    max_zip_entries: int = 1000
    max_compression_ratio: int = 1000
    max_xml_elements: int = 2_000_000
    max_processing_seconds: int = 60

    def __post_init__(self):
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{field.name} must be a positive integer.")


class Deadline:
    def __init__(self, seconds: int):
        self.end = monotonic() + seconds

    def check(self):
        if monotonic() > self.end:
            raise WorkbookInputError("Workbook exceeds the processing time limit.")
