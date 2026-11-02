"""Conservative region proposals; scores are heuristics, not probabilities."""
from openpyxl.utils import get_column_letter

from .schemas import HeaderCandidate


def _runs(values):
    result = []
    for value in values:
        if not result or value != result[-1][-1] + 1:
            result.append([])
        result[-1].append(value)
    return result


def _candidate_header(sheet, row, cols, last_row):
    cells = [sheet.cell(row, col) for col in cols]
    filled = [c for c in cells if c.value is not None]
    coverage = len(filled) / len(cols)
    text_ratio = sum(isinstance(c.value, str) and c.data_type not in {"f", "e"} for c in filled) / max(1, len(filled))
    uniqueness = len({str(c.value).strip().casefold() for c in filled}) / max(1, len(filled))
    # Compare the candidate with a bounded sample of subsequent rows.
    comparisons = contrasts = 0
    for col in cols:
        head = sheet.cell(row, col)
        if not isinstance(head.value, str) or head.data_type in {"f", "e"}:
            continue
        for r in range(row + 1, min(last_row, row + 3) + 1):
            value = sheet.cell(r, col).value
            if value is not None:
                comparisons += 1
                contrasts += not isinstance(value, str)
    contrast = contrasts / max(1, comparisons)
    score = .45 * text_ratio + .2 * coverage + .15 * uniqueness + .2 * contrast
    if coverage < .5:
        score = min(score, .4)
    return HeaderCandidate(row=row, score=round(score, 3), type_contrast=round(contrast, 3), evidence=[
        f"Text fraction: {text_ratio:.2f}",
        f"Filled fraction: {coverage:.2f}",
        f"Unique-label fraction: {uniqueness:.2f}",
        f"Type contrast with following rows: {contrast:.2f}",
    ])


def detect_regions(sheet, bounds, deadline=None):
    r_min, c_min, r_max, c_max = bounds
    active_rows = [r for r in range(r_min, r_max + 1)
                   if any(sheet.cell(r, c).value is not None for c in range(c_min, c_max + 1))]
    regions = []
    for row_run in _runs(active_rows):
        if deadline:
            deadline.check()
        active_cols = [c for c in range(c_min, c_max + 1)
                       if any(sheet.cell(r, c).value is not None for r in row_run)]
        for cols in _runs(active_cols):
            if len(cols) < 2:
                continue
            # Each side-by-side table has its own row extent.
            local_rows = [r for r in row_run if any(sheet.cell(r, c).value is not None for c in cols)]
            for rows in _runs(local_rows):
                if len(rows) < 2:
                    continue
                r1, r2, c1, c2 = rows[0], rows[-1], cols[0], cols[-1]
                candidates = [_candidate_header(sheet, r, cols, r2)
                              for r in range(r1, min(r1 + 4, r2 - 1) + 1)]
                candidates.sort(key=lambda candidate: (-candidate.score, candidate.row))
                best = candidates[0]
                header_row = best.row if best.score >= .65 else None
                tied = len(candidates) > 1 and best.score - candidates[1].score <= .1
                # Without type contrast, an all-text first row may itself be data.
                no_contrast = best.type_contrast == 0
                ambiguous = header_row is None or tied or no_contrast
                warnings = []
                if header_row is None:
                    warnings.append("No confident header; every row is included in the profile.")
                elif ambiguous:
                    warnings.append("Header is provisional; competing candidates or weak type contrast require review.")
                if len(rows) == 2:
                    ambiguous = True
                    warnings.append("Only two rows; header/data distinction requires review.")
                table_r1 = header_row if header_row is not None and not ambiguous else r1
                score = min(.6, best.score) if ambiguous else best.score
                regions.append(dict(
                    ref=f"{get_column_letter(c1)}{table_r1}:{get_column_letter(c2)}{r2}",
                    r1=table_r1, r2=r2, c1=c1, c2=c2, header_row=header_row,
                    data_start=header_row + 1 if header_row is not None else r1,
                    header_confidence=score, confidence=min(.65 if ambiguous else .95, .6 + .35 * score),
                    warnings=warnings, ambiguous=ambiguous, header_candidates=candidates,
                    evidence=["Region bounded by populated row/column bands; blank gaps are separators.",
                              "Earliest row wins equal header scores; final row cannot be a header."],
                ))
    return regions
