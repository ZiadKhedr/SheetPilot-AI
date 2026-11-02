# Phase 1 improvement handoff

The implementation now protects source workbook paths, writes JSON reports atomically, proposes early header rows without dropping text-only data, and exposes uncertainty and competing candidates.

Resource checks inspect compressed and expanded ZIP sizes, compression ratios, entry counts, XML safety and complexity, sheet counts, actual coordinates and merged extents before OpenPyXL loads. A cooperative deadline and total workbook grid limit also apply.

Column profiles and duplicate rows share a type-aware comparison policy. Report schema 1.1 constrains confidence, counts, coordinates, worksheet states, and inferred types.

The test suite covers the original behaviors and review regressions. Final result on 2026-11-01: **57 passed, 1 skipped** in 1.71 seconds. The skip is the real symlink case because this Windows account cannot create symlinks. The real hard-link case passed.

Final command: `python -m pytest -q --basetemp=work/pytest-run-3 --tb=short -rs`. The run used the bundled Python runtime with dependencies installed into `work/test-deps` and `src` available on the Python import path. Standard development setup remains `python -m pip install -e ".[dev]"` followed by `python -m pytest -q`.

The repository README explains installation, CLI/API usage, report interpretation, bounds and limitations. The acceptance checklist distinguishes synthetic verification from pending representative-company tests. Example workbook, report, and JSON Schema contain synthetic data only.

Delivered examples: `synthetic.xlsx`, `example-report.json`, and `report.schema.json` in this output folder. Reproducible source and generated copies are also in the repository's `examples/` folder.

Known verification limitation: this Windows account cannot create symlinks. Hard-link protection is verified. The processing deadline is cooperative, not an OS-enforced timeout. Representative workbook review and memory/runtime benchmarks remain pending.
