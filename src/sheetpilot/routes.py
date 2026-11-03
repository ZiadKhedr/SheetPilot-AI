from hashlib import sha256
import json
from os import replace

from fastapi import Depends, Query
from datetime import date
from fastapi.responses import FileResponse

from .analytics import dashboard, materialize, records, sales_evidence
from .config import ROOT
from .ingestion import columns_for, ingest
from .mapping import discover_relationships, meta_mapping, review_mapping, suggest_labels
from .models import AnalyzeInput, MappingInput, RegionInput, ReviewInput, SalesArgs
from .provider import MetaProvider
from .store import Problem, now, uid


def register(app, store, settings, auth):
    app.state.provider_factory = MetaProvider
    verified_path = store.root / "provider-verification.json"

    def provider_status():
        provider = app.state.provider_factory()
        status = provider.status() | {"verified": False, "generation_verified": False}
        try:
            saved = json.loads(verified_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = None
        if (isinstance(saved, dict) and saved.get("fingerprint") == sha256(provider.key.encode()).hexdigest()
                and saved.get("model") == provider.model and saved.get("verified_at")):
            status.update(verified=True, generation_verified=True, verified_at=saved["verified_at"])
        return status

    @app.get("/api/provider", dependencies=[Depends(auth)])
    def status():
        return provider_status()

    @app.post("/api/provider/verify", dependencies=[Depends(auth)])
    def verify():
        provider = app.state.provider_factory()
        try:
            result = provider.verify()
        except Problem:
            verified_path.unlink(missing_ok=True)
            raise
        saved = dict(model=provider.model, verified_at=now(), fingerprint=sha256(provider.key.encode()).hexdigest())
        temporary = verified_path.with_suffix("." + uid() + ".tmp")
        try:
            temporary.write_text(json.dumps(saved), encoding="utf-8")
            replace(temporary, verified_path)
        finally:
            temporary.unlink(missing_ok=True)
        return result | {"verified_at": saved["verified_at"]}

    @app.post("/api/demo/{company}", dependencies=[Depends(auth)])
    def demo(company: str):
        if company not in {"company_a", "company_b"}:
            raise Problem("Unknown demo company.", 404)
        label = json.loads((ROOT / "demo_data" / "manifest.json").read_text(encoding="utf-8"))["companies"][company]["name"]
        workspace = store.create_workspace(label + " · demo")
        for path in sorted((ROOT / "demo_data" / company).glob("*.xlsx")):
            ingest(store, workspace["id"], path.name, path.read_bytes())
        store.event(workspace["id"], "demo.loaded", "Loaded fictional company workbooks. Mappings still require review.")
        return workspace

    @app.get("/api/catalog", dependencies=[Depends(auth)])
    def catalog():
        from .semantics import FIELDS, ENTITIES, FIELD_CATALOG, ENTITY_CATALOG
        return {"fields": FIELDS, "entities": ENTITIES, "field_catalog": FIELD_CATALOG, "entity_catalog": ENTITY_CATALOG}

    @app.post("/api/workspaces/{workspace}/suggest-labels", dependencies=[Depends(auth)])
    def labels(workspace: str):
        store.workspace(workspace)
        result = suggest_labels(store, workspace)
        discover_relationships(store, workspace)
        return result

    @app.post("/api/workspaces/{workspace}/analyze-meta", dependencies=[Depends(auth)])
    def analyze_meta(workspace: str, body: AnalyzeInput | None = None):
        store.workspace(workspace)
        try:
            body = body or AnalyzeInput()
            result = meta_mapping(store, workspace, app.state.provider_factory(), body.table_ids, body.include_confirmed)
            discover_relationships(store, workspace)
            return result
        except Problem as exc:
            store.event(workspace, "meta.failed", str(exc))
            raise

    @app.get("/api/workspaces/{workspace}/tables/{identifier}/preview", dependencies=[Depends(auth)])
    def preview(workspace: str, identifier: str, header_row: int | None = None):
        from .profiling import table_profile, arithmetic_evidence
        table = store.get(workspace, "table", identifier)
        result = table_profile(store, workspace, table, header_row)
        result["arithmetic_evidence"] = arithmetic_evidence(result)
        return result

    @app.put("/api/workspaces/{workspace}/tables/{identifier}", dependencies=[Depends(auth)])
    def review(workspace: str, identifier: str, body: MappingInput):
        value = review_mapping(store, workspace, identifier, body)
        # Keep existing previews current after each mapping review. This never accepts a link.
        if store.list(workspace, "relationship"):
            discover_relationships(store, workspace)
        return value

    @app.post("/api/workspaces/{workspace}/workbooks/{identifier}/regions", dependencies=[Depends(auth)])
    def region(workspace: str, identifier: str, body: RegionInput):
        workbook = store.get(workspace, "workbook", identifier)
        columns = columns_for(workbook["report"], body.sheet, body.ref, body.header_row)
        table = store.put(workspace, "table", dict(id=uid(), workbook_id=identifier, sheet=body.sheet, ref=body.ref,
            header_row=body.header_row, columns=columns, entity="unknown", fields={}, confidence=0.0,
            evidence=["Manually selected source region."], status="unreviewed", origin="human-region",
            revision=0, ambiguous=True, structure_warnings=["Manual region must be mapped and confirmed."]))
        store.event(workspace, "region.created", f"Added region {body.ref} on {body.sheet}.", dict(table_id=table["id"]))
        return table

    @app.post("/api/workspaces/{workspace}/relationships/discover", dependencies=[Depends(auth)])
    def discover(workspace: str):
        store.workspace(workspace)
        return discover_relationships(store, workspace)

    @app.put("/api/workspaces/{workspace}/relationships/{identifier}", dependencies=[Depends(auth)])
    def relationship(workspace: str, identifier: str, body: ReviewInput):
        with store.connection(immediate=True) as con:
            relation = store.get(workspace, "relationship", identifier, con)
            tables = [store.get(workspace, "table", relation[key], con) for key in ["left_table", "right_table"]]
            if body.decision == "approve":
                if relation["revisions"] != [t["revision"] for t in tables] or any(t["status"] != "confirmed" for t in tables):
                    raise Problem("Confirm both source mappings, then discover relationships again.", 409)
                if relation.get("match_mode", "exact") != "exact":
                    raise Problem("Normalized matches are preview only. Resolve source identifier formatting before confirming an operational join.")
                if relation["overlap_count"] < 1:
                    raise Problem("Cannot confirm a relationship without matching source values.")
                for table, key in zip(tables, ("left_column", "right_column")):
                    if key in relation and table["fields"].get(relation[key]) != relation["field"]:
                        raise Problem("Identifier meanings changed; review both source mappings first.", 409)
            relation["status"] = "confirmed" if body.decision == "approve" else "rejected"
            result = store.put(workspace, "relationship", relation, con)
            store.event(workspace, "relationship.reviewed", f"Relationship {relation['status']}.",
                        dict(relationship_id=identifier, field=relation["field"], evidence=relation["evidence"]), con)
            materialize(store, workspace, con)
        return result

    @app.get("/api/workspaces/{workspace}/dashboard", dependencies=[Depends(auth)])
    def analytics(workspace: str):
        store.workspace(workspace)
        return dashboard(store, workspace)

    @app.get("/api/workspaces/{workspace}/records", dependencies=[Depends(auth)])
    def normalized(workspace: str):
        store.workspace(workspace)
        return records(store, workspace)[:1000]

    @app.get("/api/workspaces/{workspace}/sales/evidence", dependencies=[Depends(auth)])
    def sales_rows(workspace: str, product_id: str | None = Query(None, min_length=1, max_length=180),
                   currency: str | None = Query(None, pattern="^[A-Z]{3}$"),
                   date_from: date | None = None, date_to: date | None = None,
                   offset: int = Query(0, ge=0, le=2_147_483_647), limit: int = Query(20, ge=1, le=100)):
        if date_from and date_to and date_from > date_to:
            raise Problem("The start date must precede or equal the end date.")
        scope = SalesArgs(product_id=product_id, currency=currency, date_from=date_from, date_to=date_to)
        return sales_evidence(store, workspace, scope, offset, limit)

    from .action_routes import register_actions
    register_actions(app, store, auth)
