import pytest
from pydantic import ValidationError

from excel_intelligence.schemas import ColumnProfile, HeaderCandidate, WorkbookReport


@pytest.mark.parametrize("score", [-.01, 1.01, float("nan"), float("inf")])
def test_confidence_bounds(score):
    with pytest.raises(ValidationError):
        HeaderCandidate(row=1, score=score, type_contrast=0.0, evidence=[])


@pytest.mark.parametrize("changes", [
    dict(non_empty_count=-1), dict(index=0), dict(coordinate="invalid"),
    dict(inferred_type="guessed"), dict(missing_count="2"), dict(unknown=1),
])
def test_profile_schema_rejects_invalid_fields(changes):
    values = dict(index=1, coordinate="A1", header="ID", inferred_type="number",
                  non_empty_count=2, missing_count=0, distinct_count=2)
    with pytest.raises(ValidationError):
        ColumnProfile(**(values | changes))


def test_report_json_roundtrip(sample_workbook):
    from excel_intelligence import analyze_workbook
    report = analyze_workbook(sample_workbook)
    assert WorkbookReport.model_validate_json(report.model_dump_json()) == report
