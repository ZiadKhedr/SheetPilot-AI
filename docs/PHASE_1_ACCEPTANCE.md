# Phase 1 acceptance and verification

Status: implementation available; synthetic regression checks pass. Representative company-workbook acceptance remains open.

## Implemented and verified

- [x] Source workbook byte preservation through the API and CLI.
- [x] CLI rejects the source path, hard-link aliases, and other Excel output paths.
- [x] Atomic JSON report replacement and clear output errors.
- [x] Arabic headers, merged titles, formula expressions, hidden and very-hidden worksheets.
- [x] Headers on row 5, text-only tables, numeric tables without a header, missing values.
- [x] Multiple tables separated vertically and horizontally, with their own extents.
- [x] Duplicate source header labels remain unchanged and coordinate-addressable.
- [x] Explicit provisional header candidates, evidence, ambiguity, and bounded confidence.
- [x] Type-aware distinct values and duplicate rows; formulas/errors retain their types.
- [x] File, ZIP expansion, ratio, entry count, worksheet, cell, and XML-element checks before OpenPyXL loads.
- [x] Rejection of corrupt files, invalid coordinates/extents, DTDs, and renamed macro packages.
- [x] Positive resource-limit validation and cooperative deadline checks.
- [x] Strict report schemas and JSON round trips.
- [x] Reproducible synthetic workbook, report, and JSON Schema.

## Verification run

2026-11-01: pytest 8.4.2, Python runtime bundled with this workspace, OpenPyXL 3.1.5, Pydantic 2.14.1, defusedxml 0.7.1.

Final suite result: **57 passed, 1 skipped** in 1.71 seconds. Hard-link protection was tested with normal Windows file permissions. The real symlink test was skipped because this Windows account cannot create symlinks; path resolution protection is implemented but that platform-specific case is not verified on this host.

The initial test attempt failed because the system temporary directory was restricted. Tests were rerun with a fresh workspace-local temporary directory.

## Still requires acceptance

- [ ] Review at least ten representative, authorized copies of company workbooks with varied layouts.
- [ ] Record expected table/header boundaries and compare misses, false positives, and ambiguous results.
- [ ] Benchmark memory/runtime near configured limits before hosted use.
- [ ] Verify real symlink protection on a host permitting symlink creation.
- [ ] Approve the Phase 2 semantic mapping contract after structural accuracy is acceptable.

These unchecked items do not imply missing ERP services should be built now. Phase 1 remains offline and read-only.

## Next development decision

Use the representative-file results to improve deterministic detection. Then design reviewable semantic mapping with retained source lineage, explicit alternatives, and user-approved mappings.
