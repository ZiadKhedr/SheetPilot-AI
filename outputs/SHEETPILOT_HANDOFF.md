# SheetPilot AI — delivery handoff

**Your Spreadsheets. Your AI Workforce.**

The application now connects real Excel uploads, preserved structural analysis, official Meta Muse Spark semantic mapping, human-reviewed cross-file relationships, a normalized SQLite mirror, eight responsive screens, logical specialist agents, human approval/rejection, actual purchase-order Excel generation and an execution timeline.

Repository: https://github.com/ZiadKhedr/SheetPilot-AI
Visibility: public, explicitly approved by the user.

Local project:
D:\Codex\referenced-chatgpt-conversation-this-is-an-2

## Run
From the project directory:
```powershell
.\scripts\start.ps1
```
Then open http://127.0.0.1:8000.

Equivalent command if script execution is restricted:
```powershell
.\.venv\Scripts\python.exe -m uvicorn sheetpilot.api:app --host 127.0.0.1 --port 8000
```

The user's real Meta key is in ignored .env. It was verified by a model-catalog lookup and actual generation. No key is embedded in the frontend or Git history.

## Verified workflow
Both electronics and Arabic restaurant companies passed real-Meta browser workflows through approval, download and audit. The downloaded workbooks were opened and checked against independent product-level expectations.

- Company A: revenue USD 1,258; 31 units sold; stock 34; 3 low-stock products; PO 82 units / USD 1,809.
- Company B: revenue EGP 11,890; 40 units sold; stock 24; 3 low-stock products; PO 47 units / EGP 12,630.

Final counts are in verification-summary.json. Detailed evidence is in ../docs/TEST_RESULTS.md. Screenshots and actual downloaded workbooks are included in this output folder.

## Demo and judges
See ../docs/DEMO_SCRIPT.md for a three-minute walkthrough and ../docs/JUDGE_DESCRIPTION.md for the project description. Both fictional datasets are under ../demo_data/.

## Practical limits
This is a local hackathon MVP. It generates additional workbooks and preserves originals; no supplier email, delivered-stock update, live OneDrive/SharePoint sync or enterprise SSO is claimed. Ambiguous layouts/mappings still require review.

Compose config validates; container execution remains unverified because the host Docker engine is stopped. Native startup and browser workflows are verified. The OS symlink regression is skipped due to account permissions; real hard-link protection is tested.
