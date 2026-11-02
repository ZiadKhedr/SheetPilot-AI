# Excel Intelligence — Phase 1

Read-only structural analysis for unfamiliar `.xlsx` files. The project vision, architecture, roadmap, and Codex instructions live in `PROJECT_BRIEF.md`, `ARCHITECTURE.md`, `ROADMAP.md`, and `AGENTS.md`.

## Installation

Python 3.10 or later:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Runtime dependencies: OpenPyXL, Pydantic 2, and defusedxml. Pytest is a development dependency. Workbook data is never sent to a network service.

## Usage

```powershell
excel-analyze .\workbook.xlsx --output .\report.json
# Equivalent after installing the package:
python -m excel_intelligence.cli .\workbook.xlsx -o .\report.json
# Omit --output to print JSON to stdout.
```

Output paths must end in `.json`. Paths resolving to the input workbook, including hard links and symlinks, are rejected. Existing JSON reports are replaced atomically; output directories must already exist. Input errors and write failures produce a readable stderr message and exit code 2. Success returns 0.

Python API:

```python
from excel_intelligence import AnalysisLimits, analyze_workbook

report = analyze_workbook("workbook.xlsx", AnalysisLimits(max_sheets=20))
print(report.model_dump_json(indent=2))
```

## Report contract

Schema version **1.1** adds explicit ambiguity, header candidates, and detection evidence. Version 1.0 consumers must update for these fields. Unknown fields and invalid types are rejected; confidence is constrained to 0–1 and counts cannot be negative. Export JSON Schema with `WorkbookReport.model_json_schema()` from `excel_intelligence.schemas`.

Reports contain all worksheet states, actual populated ranges, source coordinates, formulas as text, merged ranges, blank gaps, and candidate table profiles. `dimensions` includes Excel's styled/declared extent; `populated_range` considers nonempty values. Blank row/column indices are reported only inside the populated range.

Headers are selected from up to five leading rows, excluding the last row. Equal scores prefer the earliest row. Comparisons with following rows inform the score. A text-only table can have a provisional first-row header; its candidates, low confidence, warnings, and `ambiguous=true` must be reviewed. Scores are heuristic rankings, not calibrated probabilities. Ambiguous boundaries remain visible in the region reference and raw cell detail.

Profiles count missing values as `None` only. Whitespace, empty strings retained by the reader, and original header labels are not normalized. Formula cells are present even if their cached result is blank. Formula and error columns have explicit types.

Distinct values and duplicate rows use the same comparison policy: numeric 1 and 1.0 are equivalent; text "1", boolean True, dates, formula expressions, and errors remain separate. Text comparisons preserve case and whitespace. Duplicate count is the number of extra repeated data rows after the first occurrence.

## Resource limits

All limits must be positive integers. ZIP size/ratio checks and streaming XML inspection run **before** OpenPyXL loads a workbook; DTD/entity content is rejected.

| CLI option | Default |
|---|---:|
| `--max-file-mb` | 25 MiB compressed |
| `--max-expanded-mb` | 100 MiB expanded ZIP total |
| `--max-entry-mb` | 50 MiB expanded per ZIP entry |
| `--max-zip-entries` | 1,000 |
| `--max-compression-ratio` | 1,000 |
| `--max-sheets` | 100 |
| `--max-cells-per-sheet` | 1,000,000 |
| `--max-total-cells` | 2,000,000 |
| `--max-xml-elements` | 2,000,000 |
| `--max-processing-seconds` | 60 |

Worksheet cell limits bound the rectangle from A1 to the furthest declared/actual cell or merged range, including formatting extent. Very sparse or heavily formatted sheets can therefore be rejected. The API also configures the populated-cell detail cap (100,000 **per sheet**) and samples per column (5). Truncation produces a warning.

The deadline is cooperative: it is checked during XML preflight, scans, and between processing stages. It cannot interrupt an individual OpenPyXL call and is not an OS memory quota. A future hosted service should also use isolated workers with hard memory and time limits.

## Tests and synthetic example

```powershell
python -m pytest -q
python examples\generate_example.py --output-dir examples
excel-analyze examples\synthetic.xlsx -o examples\example-report.json
```

The generator creates only synthetic data. Committed example JSON and JSON Schema can be regenerated with that script. See `docs/PHASE_1_ACCEPTANCE.md` for verified cases and remaining acceptance work.

If the operating system's temporary directory is restricted, use a new directory inside `work/` with pytest's `--basetemp` option.

## Known limitations

- Only unencrypted `.xlsx`; renamed macro-bearing ZIP packages are also rejected.
- Blank rows and columns separate regions; an intentional blank column inside a logical table may split it.
- Single-column, adjacent tables without gaps, multilevel headers, irregular forms, charts, and embedded objects are not comprehensively understood.
- No formula calculation, business semantics, cross-file relationships, cleaning edits, cloud sync, dashboards, or agents.
- Source coordinates provide lineage for this snapshot; row insertion/reordering needs stable identities and version-aware mapping in a later phase.
- Synthetic tests do not establish accuracy on arbitrary company workbooks. Review representative workbook copies before moving to Phase 2.
