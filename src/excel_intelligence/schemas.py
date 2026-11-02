from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Count = Annotated[int, Field(ge=0)]
Positive = Annotated[int, Field(ge=1)]
Confidence = Annotated[float, Field(ge=0, le=1)]
Coordinate = Annotated[str, Field(pattern=r"^[A-Z]+[1-9][0-9]*$")]
RangeRef = Annotated[str, Field(pattern=r"^[A-Z]+[1-9][0-9]*:[A-Z]+[1-9][0-9]*$")]
Value = str | int | float | bool | None


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class CellValue(StrictModel):
    coordinate: Coordinate
    value: Value = None
    data_type: Literal["s", "n", "b", "f", "e", "d", "inlineStr", "str"]


class ColumnProfile(StrictModel):
    index: Positive
    coordinate: Coordinate
    header: str | None
    inferred_type: Literal["empty", "boolean", "number", "date", "text", "formula", "error", "mixed"]
    non_empty_count: Count
    missing_count: Count
    distinct_count: Count
    sample_values: list[Value] = Field(default_factory=list)


class HeaderCandidate(StrictModel):
    row: Positive
    score: Confidence
    type_contrast: Confidence
    evidence: list[str]


class TableRegion(StrictModel):
    id: str
    ref: RangeRef
    header_row: Positive | None
    header_confidence: Confidence
    confidence: Confidence
    row_count: Positive
    column_count: Positive
    columns: list[ColumnProfile]
    ambiguous: bool
    header_candidates: list[HeaderCandidate]
    evidence: list[str]
    warnings: list[str] = Field(default_factory=list)
    duplicate_data_row_count: Count = 0


class WorksheetReport(StrictModel):
    title: str
    state: Literal["visible", "hidden", "veryHidden"]
    dimensions: str
    populated_range: RangeRef | None
    populated_cell_count: Count
    blank_rows: list[Positive]
    blank_columns: list[Positive]
    merged_ranges: list[str]
    formulas: list[CellValue]
    populated_cells: list[CellValue]
    tables: list[TableRegion]
    warnings: list[str] = Field(default_factory=list)


class WorkbookReport(StrictModel):
    schema_version: Literal["1.1"] = "1.1"
    file_name: str
    file_size_bytes: Count
    sheet_count: Count
    worksheets: list[WorksheetReport]
    warnings: list[str] = Field(default_factory=list)
