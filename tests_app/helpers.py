import json
from pathlib import Path
from sheetpilot.ingestion import ingest
from sheetpilot.mapping import review_mapping, discover_relationships
from sheetpilot.analytics import materialize
from sheetpilot.models import MappingInput


def load_company(store, company="company_a"):
    manifest = json.loads(Path("demo_data/manifest.json").read_text(encoding="utf-8"))["companies"][company]
    workspace = store.create_workspace(company)["id"]
    for config in manifest["files"].values():
        path = Path("demo_data") / company / config["filename"]
        workbook = ingest(store, workspace, path.name, path.read_bytes())
        tables = store.list(workspace, "table")
        table = next(t for t in tables if t["workbook_id"] == workbook["id"] and t["sheet"] == config["sheet"] and t["ref"] == config["ref"])
        entity = next(k for k,v in manifest["files"].items() if v is config)
        review_mapping(store, workspace, table["id"], MappingInput(
            entity=entity, fields=config["columns"], header_row=config["header_row"], expected_revision=table["revision"]))
    materialize(store, workspace)
    return workspace, manifest


def confirm_relationships(store, workspace):
    for relation in discover_relationships(store, workspace):
        if relation["overlap_count"]:
            relation["status"] = "confirmed"
            store.put(workspace, "relationship", relation)
