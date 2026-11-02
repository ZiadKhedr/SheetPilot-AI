from collections import Counter
from datetime import date, datetime, time

from .schemas import ColumnProfile
from .workbook_reader import cell_value


def typed_key(cell):
    """Source-exact comparison: no trimming, case folding, or type coercion.

    Excel numeric 1 and 1.0 are equivalent, while text '1', boolean True,
    formulas, errors and date values remain separate.
    """
    value = cell.value
    if value is None:
        return ("empty", None)
    if cell.data_type == "f":
        return ("formula", str(value))
    if cell.data_type == "e":
        return ("error", value)
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, (int, float)):
        return ("number", value)
    if isinstance(value, (date, datetime, time)):
        return (type(value).__name__, value.isoformat())
    return ("text", str(value))


def _type(cells):
    kinds = {typed_key(cell)[0] for cell in cells}
    kinds = {"date" if k in {"date", "datetime", "time"} else k for k in kinds}
    return next(iter(kinds)) if len(kinds) == 1 else ("mixed" if kinds else "empty")


def profile_columns(sheet, region, sample_limit=5, deadline=None):
    r1, r2, c1, c2 = region["r1"], region["r2"], region["c1"], region["c2"]
    header_row = region["header_row"]
    data_start = region["data_start"]
    profiles = []
    for col in range(c1, c2 + 1):
        if deadline:
            deadline.check()
        cells = [sheet.cell(r, col) for r in range(data_start, r2 + 1)]
        present = [cell for cell in cells if cell.value is not None]
        header = sheet.cell(header_row, col).value if header_row else None
        profiles.append(ColumnProfile(
            index=col, coordinate=sheet.cell(header_row or r1, col).coordinate,
            header=str(header) if header is not None else None,
            inferred_type=_type(present), non_empty_count=len(present),
            missing_count=len(cells) - len(present),
            distinct_count=len({typed_key(cell) for cell in present}),
            sample_values=[cell_value(cell) for cell in present[:sample_limit]],
        ))
    counts = Counter(tuple(typed_key(sheet.cell(r, c)) for c in range(c1, c2 + 1))
                     for r in range(data_start, r2 + 1))
    return profiles, sum(n - 1 for n in counts.values())
