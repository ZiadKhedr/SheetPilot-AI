from pathlib import Path
import secrets

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, ConfigDict

from .config import ROOT, Settings
from .ingestion import UPLOAD_LIMIT, ingest
from .store import Problem, Store
from .middleware import BodyLimitMiddleware


class WorkspaceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=80)


def create_app(settings=None):
    settings = settings or Settings.from_env()
    app = FastAPI(title="SheetPilot AI", version="0.1.0")
    store = Store(settings.data_dir)
    app.state.store = store
    app.state.settings = settings
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                       allow_methods=["GET", "POST", "PUT"], allow_headers=["Authorization", "Content-Type"])
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver"])

    @app.exception_handler(Problem)
    async def problem_handler(request, exc):
        return JSONResponse(status_code=exc.status, content={"detail": str(exc)})

    def auth(request: Request):
        token = request.headers.get("authorization", "").removeprefix("Bearer ")
        if settings.access_token:
            if secrets.compare_digest(token, settings.access_token):
                return "owner"
            if settings.read_token and secrets.compare_digest(token, settings.read_token):
                if request.method != "GET":
                    raise HTTPException(403, "Read-only access cannot change this workspace.")
                return "reader"
            raise HTTPException(401, "A valid workspace access token is required.")
        # Local single-operator mode: reject browser mutations from unexpected origins.
        origin = request.headers.get("origin", "")
        if origin and origin != str(request.base_url).rstrip("/") and origin not in {"http://localhost:5173", "http://127.0.0.1:5173",
                                     "http://localhost:8000", "http://127.0.0.1:8000"}:
            raise HTTPException(403, "This origin is not allowed.")
        return "local-operator"

    @app.get("/api/health")
    def health():
        return {"status": "ok", "application": "SheetPilot AI"}

    @app.get("/api/workspaces", dependencies=[Depends(auth)])
    def workspaces():
        return store.workspaces()

    @app.post("/api/workspaces", dependencies=[Depends(auth)])
    def create_workspace(body: WorkspaceInput):
        return store.create_workspace(body.name.strip())

    @app.get("/api/workspaces/{workspace}/state", dependencies=[Depends(auth)])
    def state(workspace: str):
        return {"workspace": store.workspace(workspace), "workbooks": store.list(workspace, "workbook"),
                "tables": store.list(workspace, "table"), "relationships": store.list(workspace, "relationship"),
                "actions": store.list(workspace, "action"), "runs": store.list(workspace, "run"),
                "events": store.events(workspace)}

    @app.post("/api/workspaces/{workspace}/uploads", dependencies=[Depends(auth)])
    async def upload(workspace: str, file: UploadFile = File(...)):
        content = await file.read(UPLOAD_LIMIT + 1)
        await file.close()
        if len(content) > UPLOAD_LIMIT:
            raise Problem("Workbook exceeds the 10 MiB upload limit.", 413)
        return ingest(store, workspace, file.filename, content)

    @app.get("/api/workspaces/{workspace}/workbooks/{identifier}/download", dependencies=[Depends(auth)])
    def original(workspace: str, identifier: str):
        workbook = store.get(workspace, "workbook", identifier)
        return FileResponse(store.root / "originals" / f"{workbook['id']}.xlsx", filename=workbook["name"])

    # Further vertical slices register their own explicit routes here.
    from .routes import register
    register(app, store, settings, auth)

    dist = ROOT / "frontend" / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
        @app.get("/{path:path}")
        def frontend(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "API route not found.")
            return FileResponse(dist / "index.html")
    return app


app = create_app()
