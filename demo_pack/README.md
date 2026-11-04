# SheetPilot AI synthetic demo pack

Start with RECORDING_GUIDE.md. Upload only the three core/*.xlsx files into a clean workspace. Every challenge/optional folder is a separate workspace unless the version guide explicitly uses New snapshot. Mapping and relationship references do not grant application approval.

Requires Python 3.10+ and openpyxl 3.1+. Reproduce:

```powershell
python generate_demo_pack.py --as-of 2026-11-03 --seed 42 --output-dir ./generated
python validate_demo_pack.py --pack-dir ./generated --reproduce
```

From the SheetPilot repository with its app dependencies installed:

```powershell
.venv/Scripts/python demo_pack/validate_demo_pack.py --pack-dir demo_pack --app --reproduce
```

Validation writes VALIDATION_RESULTS.md and validation_results.json, then packages SheetPilot_Demo_Pack.zip. The ZIP contains the workbooks, Python sources, manifests and guides. All XLSX archives and package entries use stable timestamps for byte reproducibility. No application fixtures are changed. Provider configuration/live Meta validation is outside the generator and validator.

All Excel business values are literals. Decimal arithmetic uses ROUND_HALF_UP to cents. Quotes are per base unit and may retain six decimal places. Source coordinates are recorded in the mapping manifest and scenario cards. Synthetic contacts use example.invalid. No real personal data is included.
