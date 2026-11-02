import argparse
import os
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

from .analyzer import AnalysisLimits, analyze_workbook
from .workbook_reader import WorkbookInputError


def _positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def _safe_output(source, output):
    if source.resolve() == output.resolve() or (output.exists() and os.path.samefile(source, output)):
        raise WorkbookInputError("Output must not refer to the source workbook.")
    # Prevent accidental replacement of any Excel workbook, even a different one.
    if output.suffix.lower() != ".json":
        raise WorkbookInputError("Output must have a .json extension.")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Analyze an .xlsx workbook without modifying it.")
    parser.add_argument("workbook", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="JSON report path (default: stdout).")
    for flag, default in [("max-file-mb", 25), ("max-sheets", 100),
                          ("max-cells-per-sheet", 1_000_000), ("max-total-cells", 2_000_000),
                          ("max-expanded-mb", 100), ("max-entry-mb", 50),
                          ("max-zip-entries", 1000), ("max-compression-ratio", 1000),
                          ("max-xml-elements", 2_000_000), ("max-processing-seconds", 60)]:
        parser.add_argument("--" + flag, type=_positive, default=default)
    args = parser.parse_args(argv)
    temporary = None
    try:
        if args.output:
            _safe_output(args.workbook, args.output)
        limits = AnalysisLimits(
            max_file_size_bytes=args.max_file_mb * 1024 * 1024,
            max_sheets=args.max_sheets, max_cells_per_sheet=args.max_cells_per_sheet,
            max_total_cells=args.max_total_cells, max_archive_bytes=args.max_expanded_mb * 1024 * 1024,
            max_entry_bytes=args.max_entry_mb * 1024 * 1024, max_zip_entries=args.max_zip_entries,
            max_compression_ratio=args.max_compression_ratio, max_xml_elements=args.max_xml_elements,
            max_processing_seconds=args.max_processing_seconds,
        )
        rendered = analyze_workbook(args.workbook, limits).model_dump_json(indent=2)
        if args.output:
            _safe_output(args.workbook, args.output)
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=args.output.parent,
                                    prefix=".excel-report-", suffix=".tmp", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(rendered + "\n")
            # Replace the directory entry rather than writing through links.
            os.replace(temporary, args.output)
            temporary = None
        else:
            print(rendered)
        return 0
    except (WorkbookInputError, OSError, ValueError) as exc:
        print(f"excel-analyze: {exc}", file=sys.stderr)
        return 2
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
