import json
from pathlib import Path
import runpy

from excel_intelligence.schemas import WorkbookReport


def test_example_generator_produces_valid_synthetic_artifacts(tmp_path):
    module = runpy.run_path(str(Path(__file__).parents[1] / "examples" / "generate_example.py"))
    report = module["generate"](tmp_path)
    assert report.worksheets[0].tables[0].header_row == 5
    assert report.worksheets[0].tables[0].duplicate_data_row_count == 1
    assert report.worksheets[1].state == "hidden"
    assert (tmp_path / "synthetic.xlsx").is_file()
    decoded = WorkbookReport.model_validate_json((tmp_path / "example-report.json").read_text(encoding="utf-8"))
    assert decoded == report
    schema = json.loads((tmp_path / "report.schema.json").read_text(encoding="utf-8"))
    assert schema["properties"]["schema_version"]["const"] == "1.1"
