import json
from fastapi import Depends, Path
from fastapi.responses import FileResponse, Response, JSONResponse

from .actions import propose, review_action, procurement_readiness
from .agents import run_agents
from .ingestion import digest
from .models import AgentInput, DemandParameters, DemandPolicyInput, DraftArgs, ReviewInput
from .demand import demand_analysis, save_policy
from .store import Problem


def register_actions(app, store, auth):
    @app.get("/api/workspaces/{workspace}/demand", dependencies=[Depends(auth)])
    def demand(workspace:str):
        return demand_analysis(store,workspace)

    @app.post("/api/workspaces/{workspace}/demand/preview", dependencies=[Depends(auth)])
    def preview_demand(workspace:str,body:DemandParameters):
        return demand_analysis(store,workspace,body)

    @app.put("/api/workspaces/{workspace}/demand/policy")
    def review_policy(workspace:str,body:DemandPolicyInput,actor=Depends(auth)):
        return save_policy(store,workspace,body,actor)

    @app.get("/api/workspaces/{workspace}/procurement/readiness", dependencies=[Depends(auth)])
    def readiness(workspace: str):
        result = procurement_readiness(store, workspace)
        return {k: v for k, v in result.items() if k != "lines"}

    @app.post("/api/workspaces/{workspace}/actions/draft", dependencies=[Depends(auth)])
    def draft(workspace: str, body: DraftArgs):
        return propose(store, workspace, body.product_ids)

    @app.put("/api/workspaces/{workspace}/actions/{identifier}/review")
    def review(workspace: str, identifier: str, body: ReviewInput, actor=Depends(auth)):
        return review_action(store, workspace, identifier, body.decision, actor)

    @app.get("/api/workspaces/{workspace}/actions/{identifier}/download", dependencies=[Depends(auth)])
    def download(workspace: str, identifier: str):
        action = store.get(workspace, "action", identifier)
        if action["status"] != "executed" or not action["output"]:
            raise Problem("Only executed actions have downloadable workbooks.", 404)
        path = store.root / "outputs" / f"{action['id']}.xlsx"
        if not path.is_file() or digest(path) != action["output"]["sha256"]:
            raise Problem("The generated output is missing or changed; download refused.", 409)
        return FileResponse(path, filename=action["output"]["name"],
                            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    @app.post("/api/workspaces/{workspace}/agents", dependencies=[Depends(auth)])
    def agents(workspace: str, body: AgentInput):
        store.workspace(workspace)
        if body.durable:
            from .jobs import enqueue
            result=enqueue(store,workspace,body)
            app.state.worker.wake.set()
            return JSONResponse(result,status_code=202)
        return run_agents(store, workspace, body.message, body.mode, app.state.provider_factory(), body.task, body.request_id)

    from .jobs import JobRetry, cancel_job, retry_job
    @app.post('/api/workspaces/{workspace}/jobs/{identifier}/cancel',dependencies=[Depends(auth)])
    def cancel(workspace:str,identifier:str):return cancel_job(store,workspace,identifier)

    @app.post('/api/workspaces/{workspace}/jobs/{identifier}/retry',dependencies=[Depends(auth)])
    def retry(workspace:str,identifier:str,body:JobRetry):
        result=retry_job(store,workspace,identifier,body);app.state.worker.wake.set();return result

    @app.get("/api/workspaces/{workspace}/agents/progress/{request_id}", dependencies=[Depends(auth)])
    def progress(workspace: str, request_id: str = Path(pattern=r"^[a-f0-9]{32}$")):
        store.workspace(workspace)
        with store.connection() as con:
            row = con.execute("SELECT payload FROM objects WHERE workspace=? AND kind='run' "
                "AND json_extract(payload,'$.request_id')=? ORDER BY created DESC,rowid DESC LIMIT 1",
                (workspace,request_id)).fetchone()
        if row is None:
            raise Problem("This job has not started yet.",404)
        return json.loads(row[0])

    @app.get("/api/workspaces/{workspace}/agent-runs/{identifier}/report", dependencies=[Depends(auth)])
    def work_report(workspace: str, identifier: str):
        from .agent_work import report_text
        run = store.get(workspace,"run",identifier)
        if run["status"] in {'queued','running'}:
            raise Problem("Wait for this job to finish before downloading its report.",409)
        return Response(report_text(store,workspace,run),media_type="text/plain; charset=utf-8",
            headers={"Content-Disposition":f'attachment; filename="Agent-Work-{run["id"][:8]}.txt"'})
