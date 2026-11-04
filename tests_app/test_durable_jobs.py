from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from threading import Event
from time import monotonic, sleep
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from sheetpilot.actions import fingerprint
from sheetpilot.api import create_app
from sheetpilot.backups import create_backup, restore_backup
from sheetpilot.config import Settings
from sheetpilot.jobs import (LocalWorker, JobRetry, cancel_job, enqueue, recover_interrupted, retry_job)
from sheetpilot.models import AgentInput
from sheetpilot.provider import MetaProvider, MetaError
from sheetpilot.store import Store, Problem
from .helpers import load_company, confirm_relationships


def wait_run(store,workspace,run,timeout=8):
    deadline=monotonic()+timeout
    while monotonic()<deadline:
        current=store.get(workspace,'run',run['id'])
        if current['status'] not in {'queued','running'}:return current
        sleep(.03)
    raise AssertionError('The durable test job did not finish within its bound.')


def body(task='daily_review',mode='guided',request_id=None):
    return AgentInput(message='Review fictional business data.',mode=mode,task=task,request_id=request_id or uuid4().hex,durable=True)


class GateProvider:
    def __init__(self,started,release,calls):self.started,self.release,self.calls=started,release,calls;self.turn=0
    def completion(self,messages,tools=None):
        self.calls.append('provider-call');self.started.set();assert self.release.wait(5)
        self.turn+=1
        if self.turn==1:return {'content':None,'tool_calls':[{'id':'stock','type':'function','function':{'name':'inventory_analysis','arguments':'{}'}}]}
        return {'content':'Reviewed stock.','tool_calls':[]}


def test_durable_api_persists_actual_progress_and_duplicate_submission(tmp_path):
    app=create_app(Settings(tmp_path));workspace,_=load_company(app.state.store)
    app.state.provider_factory=lambda:SimpleNamespace()
    payload=body().model_dump()
    with TestClient(app) as client:
        response=client.post(f'/api/workspaces/{workspace}/agents',json=payload)
        assert response.status_code==202
        run=response.json();completed=wait_run(app.state.store,workspace,run)
        assert completed['status']=='completed' and len(completed['steps'])==4
        assert completed['origin']=='guided-tools' and completed['work']['completed_checks']==4
        assert client.post(f'/api/workspaces/{workspace}/agents',json=payload).json()['id']==run['id']
        progress=client.get(f'/api/workspaces/{workspace}/agents/progress/{payload["request_id"]}').json()
        assert progress['id']==run['id'] and progress['status']=='completed'
        assert len(app.state.store.list(workspace,'job'))==1
        assert not app.state.store.list(workspace,'action')


def test_browser_disconnect_does_not_cancel_provider_and_explicit_cancel_retry(tmp_path):
    store=Store(tmp_path);workspace=store.create_workspace('Fictional stock')['id']
    started,release,calls=Event(),Event(),[]
    worker=LocalWorker(store,lambda:GateProvider(started,release,calls));worker.start()
    try:
        run=enqueue(store,workspace,body('stock_review','meta'));worker.wake.set();assert started.wait(3)
        # No request remains open. The provider is still running with a live lease.
        recover_interrupted(store)
        assert store.get(workspace,'job',run['job_id'])['status']=='running' and len(calls)==1
        cancel_job(store,workspace,run['job_id']);release.set()
        cancelled=wait_run(store,workspace,run)
        assert cancelled['status']=='cancelled' and cancelled['steps']==[]
        sleep(.1);assert len(calls)==1
        retried=retry_job(store,workspace,run['job_id'],JobRetry(request_id=uuid4().hex,expected_fingerprint=fingerprint(store,workspace)))
        worker.wake.set();completed=wait_run(store,workspace,retried)
        assert completed['status']=='completed' and completed['attempt']==2
        assert len(calls)==3 and len(store.list(workspace,'job'))==2
    finally:release.set();worker.stop()


def test_expired_server_lease_is_interrupted_without_automatic_replay(tmp_path):
    store=Store(tmp_path);workspace=store.create_workspace('Interrupted')['id'];run=enqueue(store,workspace,body())
    job=store.get(workspace,'job',run['job_id']);job.update(status='running',owner='dead',heartbeat='2000-01-01T00:00:00+00:00')
    store.put(workspace,'job',job);store.put(workspace,'run',run|{'status':'running','steps':[{'tool':'inventory_analysis','agent':'Inventory Agent','status':'running','result':{}}]})
    recover_interrupted(store);first_events=store.events(workspace);recover_interrupted(store)
    recovered=store.get(workspace,'run',run['id'])
    assert recovered['status']=='interrupted' and recovered['steps'][0]['status']=='interrupted'
    assert store.events(workspace)==first_events
    assert not store.list(workspace,'action')


def test_context_drift_blocks_tools_and_retry_after_provider_returns(tmp_path):
    store=Store(tmp_path);workspace=store.create_workspace('Drift')['id'];started,release,calls=Event(),Event(),[]
    worker=LocalWorker(store,lambda:GateProvider(started,release,calls));worker.start()
    try:
        run=enqueue(store,workspace,body('stock_review','meta'));worker.wake.set();assert started.wait(3)
        store.put(workspace,'demand_policy',{'revision':1,'enabled':False})
        release.set();interrupted=wait_run(store,workspace,run)
        assert interrupted['status']=='interrupted' and not interrupted['steps']
        with pytest.raises(Problem,match='unchanged'):
            retry_job(store,workspace,run['job_id'],JobRetry(request_id=uuid4().hex,expected_fingerprint=fingerprint(store,workspace)))
        assert len(calls)==1
    finally:release.set();worker.stop()


def test_concurrent_enqueue_and_queued_cancellation_are_idempotent(tmp_path):
    store=Store(tmp_path);workspace=store.create_workspace('Duplicates')['id'];request=body()
    with ThreadPoolExecutor(max_workers=2) as pool:runs=list(pool.map(lambda _:enqueue(store,workspace,request),range(2)))
    assert runs[0]['id']==runs[1]['id'] and len(store.list(workspace,'job'))==1
    cancelled=cancel_job(store,workspace,runs[0]['job_id'])
    assert cancelled['status']=='cancelled'
    assert cancel_job(store,workspace,runs[0]['job_id'])==cancelled
    with pytest.raises(Problem,match='different'):
        enqueue(store,workspace,body('stock_review',request_id=request.request_id))


def test_cancel_after_pending_draft_and_retry_do_not_duplicate_purchase(tmp_path,monkeypatch):
    import sheetpilot.agents as agents
    store=Store(tmp_path);workspace,_=load_company(store);confirm_relationships(store,workspace)
    run=enqueue(store,workspace,body('replenishment'))
    original=agents.propose
    def draft_and_cancel(*args,**kwargs):
        result=original(*args,**kwargs);cancel_job(store,workspace,run['job_id']);return result
    monkeypatch.setattr(agents,'propose',draft_and_cancel)
    worker=LocalWorker(store,lambda:SimpleNamespace());worker.start()
    try:
        cancelled=wait_run(store,workspace,run)
        assert cancelled['status']=='cancelled' and len(cancelled['action_ids'])==1
        monkeypatch.setattr(agents,'propose',original)
        retried=retry_job(store,workspace,run['job_id'],JobRetry(request_id=uuid4().hex,expected_fingerprint=fingerprint(store,workspace)))
        worker.wake.set();completed=wait_run(store,workspace,retried)
        assert completed['status']=='completed' and completed['action_ids']==cancelled['action_ids']
        assert len(store.list(workspace,'action'))==1 and store.list(workspace,'action')[0]['status']=='pending'
        assert not list((store.root/'outputs').glob('*.xlsx'))
    finally:worker.stop()


def test_changed_source_and_zero_budget_stop_before_provider(tmp_path):
    store=Store(tmp_path);workspace,_=load_company(store);calls=[]
    run=enqueue(store,workspace,body('stock_review','meta'))
    job=store.get(workspace,'job',run['job_id']);job['max_runtime_seconds']=0;store.put(workspace,'job',job)
    worker=LocalWorker(store,lambda:calls.append('factory') or SimpleNamespace());worker.start()
    try:
        assert wait_run(store,workspace,run)['status']=='interrupted'
        assert not calls
    finally:worker.stop()


def test_changed_original_stops_before_provider(tmp_path):
    store=Store(tmp_path);workspace,_=load_company(store);calls=[]
    run=enqueue(store,workspace,body('stock_review','meta'))
    source=store.list(workspace,'workbook')[0]
    (store.root/'originals'/f"{source['id']}.xlsx").write_bytes(b'tampered')
    worker=LocalWorker(store,lambda:calls.append('factory') or SimpleNamespace());worker.start()
    try:
        assert wait_run(store,workspace,run)['status']=='interrupted' and not calls
    finally:worker.stop()


def test_restored_queued_jobs_never_automatically_replay(tmp_path):
    store=Store(tmp_path/'live');workspace=store.create_workspace('Restore queue')['id'];run=enqueue(store,workspace,body())
    restored=Store(Path(restore_backup(store,create_backup(store))['data_dir']))
    assert store.get(workspace,'job',run['job_id'])['status']=='queued'
    assert restored.get(workspace,'job',run['job_id'])['status']=='interrupted'
    assert restored.get(workspace,'run',run['id'])['status']=='interrupted'
    assert any(e['kind']=='job.restore_interrupted' for e in restored.events(workspace))


def test_durable_provider_does_not_repeat_timeout_or_length_generation():
    calls=[]
    def timeout(request):calls.append(request);raise httpx.ReadTimeout('test-only timeout')
    provider=MetaProvider(key='fictional-test-key',transport=httpx.MockTransport(timeout));provider.request_attempts=1
    with pytest.raises(MetaError,match='timed out'):provider.completion([{'role':'user','content':'fictional'}])
    assert len(calls)==1
    calls.clear()
    def length(request):calls.append(request);return httpx.Response(200,json={'choices':[{'finish_reason':'length','message':{}}]})
    provider=MetaProvider(key='fictional-test-key',transport=httpx.MockTransport(length));provider.allow_completion_retry=False
    with pytest.raises(MetaError,match='did not replay'):provider.completion([{'role':'user','content':'fictional'}])
    assert len(calls)==1
