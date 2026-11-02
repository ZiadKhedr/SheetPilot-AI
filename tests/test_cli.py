import json
import os

import pytest

from excel_intelligence.cli import main
from excel_intelligence.schemas import WorkbookReport


def test_cli_round_trip_and_preserves_source(sample_workbook, tmp_path):
    output = tmp_path / "report.json"
    before = sample_workbook.read_bytes()
    assert main([str(sample_workbook), "-o", str(output)]) == 0
    report = WorkbookReport.model_validate_json(output.read_text(encoding="utf-8"))
    assert report.schema_version == "1.1"
    assert report.worksheets[0].formulas[0].value == "=SUM(C5:C6)"
    assert sample_workbook.read_bytes() == before


def test_same_output_rejected_before_analysis(sample_workbook, capsys):
    before = sample_workbook.read_bytes()
    assert main([str(sample_workbook), "-o", str(sample_workbook)]) == 2
    assert "source workbook" in capsys.readouterr().err
    assert sample_workbook.read_bytes() == before


def test_hardlink_output_rejected(sample_workbook, tmp_path):
    alias = tmp_path / "alias.json"
    os.link(sample_workbook, alias)
    before = sample_workbook.read_bytes()
    assert main([str(sample_workbook), "-o", str(alias)]) == 2
    assert sample_workbook.read_bytes() == before


def test_symlink_output_rejected(sample_workbook, tmp_path):
    alias = tmp_path / "alias.json"
    try:
        alias.symlink_to(sample_workbook)
    except OSError:
        pytest.skip("This Windows account cannot create symlinks.")
    before = sample_workbook.read_bytes()
    assert main([str(sample_workbook), "-o", str(alias)]) == 2
    assert sample_workbook.read_bytes() == before


def test_cli_stdout(sample_workbook, capsys):
    assert main([str(sample_workbook)]) == 0
    assert json.loads(capsys.readouterr().out)["sheet_count"] == 2


@pytest.mark.parametrize("flag", ["--max-file-mb", "--max-sheets", "--max-cells-per-sheet",
                                  "--max-total-cells", "--max-processing-seconds"])
def test_cli_rejects_zero_limits(sample_workbook, flag):
    with pytest.raises(SystemExit) as exc:
        main([str(sample_workbook), flag, "0"])
    assert exc.value.code == 2


def test_cli_output_errors_are_clear(sample_workbook, tmp_path, capsys):
    assert main([str(sample_workbook), "-o", str(tmp_path / "missing" / "out.json")]) == 2
    assert "excel-analyze:" in capsys.readouterr().err
    assert not list(tmp_path.glob(".excel-report-*.tmp"))


def test_cli_protects_other_workbooks(sample_workbook, tmp_path):
    output = tmp_path / "other.xlsx"
    output.write_bytes(b"preserve")
    assert main([str(sample_workbook), "-o", str(output)]) == 2
    assert output.read_bytes() == b"preserve"


def test_existing_report_replaced_atomically(sample_workbook, tmp_path):
    output = tmp_path / "report.json"
    output.write_text("old report")
    assert main([str(sample_workbook), "-o", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["sheet_count"] == 2
    assert not list(tmp_path.glob(".excel-report-*.tmp"))
