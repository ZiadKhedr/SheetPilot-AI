"""One local SQLite-backed worker; browser requests only enqueue/reconnect.

No broker is needed for this single-operator app. Claims, request deduplication
and cancellation are transactional. A heartbeat distinguishes a dead server
from a disconnected browser. Interrupted provider work never restarts itself.
"""
from datetime import datetime, timezone, timedelta
import json
from threading import Event, Thread, Lock
from time import monotonic

from pydantic import Field

from .actions import fingerprint
from .agent_work import JOBS, work_counts
from .ingestion import digest
from .job_control import StopJob
from .lifecycle import active_workbooks
from .models import AgentInput, Model
from .store import Problem, now, uid

ACTIVE={'queued','running'}
RETRYABLE={'failed','interrupted','cancelled'}
MAX_RUNTIME=180
LEASE_SECONDS=30


class JobRetry(Model):
    request_id:str=Field(pattern='^[a-f0-9]{32}$')
    expected_fingerprint:str=Field(pattern='^[a-f0-9]{64}$')


def enqueue(store,workspace,body,*,retry_of=None,attempt=1):
    store.workspace(workspace)
    request_id=body.request_id or uid()
    with store.connection(immediate=True) as con:
        old=next((j for j in store.list(workspace,'job',con) if j['request_id']==request_id),None)
        if old:
            if any(old[k]!=getattr(body,k) for k in ['message','mode','task']) or old.get('retry_of')!=retry_of:
                raise Problem('This request identifier already belongs to a different job.',409)
            return store.get(workspace,'run',old['run_id'],con)
        snapshot=fingerprint(store,workspace,con)
        if body.expected_fingerprint and snapshot!=body.expected_fingerprint:
            raise Problem('Reviewed data changed before this job was queued. Refresh first.',409)
        if retry_of:
            previous=store.get(workspace,'job',retry_of,con)
            if previous['status'] not in RETRYABLE or previous['input_fingerprint']!=snapshot:
                raise Problem('Retry requires unchanged source/review fingerprints and an interrupted, cancelled or failed job. Start a new job after data review.',409)
        sources=[{'id':w['id'],'name':w['name'],'sha256':w['sha256']} for w in active_workbooks(store,workspace,con)]
        job_id,run_id=uid(),uid()
        run=store.put(workspace,'run',{'id':run_id,'job_id':job_id,'request_id':request_id,'task':body.task,
            'title':JOBS[body.task][0],'message':body.message,'origin':'meta' if body.mode=='meta' else 'guided-tools',
            'status':'queued','summary':'Queued for the local worker. No tool or provider call has started.',
            'steps':[],'action_ids':[],'blockers':[],'input_fingerprint':snapshot,'source_versions':sources,
            'attempt':attempt,'retry_of':retry_of},con)
        store.put(workspace,'job',{'id':job_id,'run_id':run_id,'request_id':request_id,'message':body.message,
            'mode':body.mode,'task':body.task,'status':'queued','input_fingerprint':snapshot,'source_versions':sources,
            'cancel_requested':False,'attempt':attempt,'retry_of':retry_of,'max_runtime_seconds':MAX_RUNTIME},con)
        store.event(workspace,'job.queued','Queued a durable agent job; reconnecting does not restart provider work.',
                    {'job_id':job_id,'run_id':run_id,'origin':run['origin'],'attempt':attempt,'retry_of':retry_of},con)
        return run


def cancel_job(store,workspace,identifier):
    with store.connection(immediate=True) as con:
        job=store.get(workspace,'job',identifier,con)
        if job['status'] not in ACTIVE:return store.get(workspace,'run',job['run_id'],con)
        job.update(cancel_requested=True,cancel_requested_at=now())
        run=store.get(workspace,'run',job['run_id'],con)
        run['cancel_requested']=True
        if job['status']=='queued':
            job.update(status='cancelled',finished_at=now())
            run.update(status='cancelled',finished_at=now(),summary='Cancelled before execution. No provider call or tool started.')
        store.put(workspace,'job',job,con);store.put(workspace,'run',run,con)
        store.event(workspace,'job.cancel_requested','Cancellation requested; the worker stops between safe steps.',{'job_id':identifier},con)
        return run


def retry_job(store,workspace,identifier,body):
    old=store.get(workspace,'job',identifier)
    # enqueue repeats both status and fingerprint checks under its write lock.
    return enqueue(store,workspace,AgentInput(message=old['message'],mode=old['mode'],task=old['task'],
        request_id=body.request_id,durable=True,expected_fingerprint=body.expected_fingerprint),
        retry_of=identifier,attempt=old['attempt']+1)


def recover_interrupted(store,*,cutoff=None):
    cutoff=cutoff or (datetime.now(timezone.utc)-timedelta(seconds=LEASE_SECONDS)).isoformat()
    with store.connection(immediate=True) as con:
        rows=con.execute("SELECT workspace,payload FROM objects WHERE kind='job' AND json_extract(payload,'$.status')='running'").fetchall()
        for row in rows:
            job=json.loads(row['payload'])
            if job.get('heartbeat',job['created'])>=cutoff:continue
            job.update(status='interrupted',finished_at=now(),summary='Server worker heartbeat expired. Explicit retry is required; provider work was not restarted.')
            run=store.get(row['workspace'],'run',job['run_id'],con)
            run.update(status='interrupted',finished_at=now(),summary=job['summary'])
            for step in run['steps']:
                if step['status']=='running':step.update(status='interrupted',finished_at=now())
            run['work']=work_counts(run)
            store.put(row['workspace'],'job',job,con);store.put(row['workspace'],'run',run,con)
            store.event(row['workspace'],'job.interrupted',job['summary'],{'job_id':job['id'],'run_id':run['id']},con)


def interrupt_restored_jobs(store):
    """A restored queue must not replay work possibly executed since the backup."""
    with store.connection(immediate=True) as con:
        rows=con.execute("SELECT workspace,payload FROM objects WHERE kind='job' AND json_extract(payload,'$.status') IN ('queued','running')").fetchall()
        for row in rows:
            job=json.loads(row['payload'])
            summary='Restored from backup. Review partial work and explicitly retry; the original installation may have advanced.'
            job.update(status='interrupted',summary=summary,finished_at=now())
            run=store.get(row['workspace'],'run',job['run_id'],con)
            run.update(status='interrupted',summary=summary,finished_at=now())
            for step in run['steps']:
                if step['status']=='running':step['status']='interrupted'
            run['work']=work_counts(run)
            store.put(row['workspace'],'job',job,con);store.put(row['workspace'],'run',run,con)
            store.event(row['workspace'],'job.restore_interrupted',summary,{'job_id':job['id'],'run_id':run['id']},con)


class LocalWorker:
    def __init__(self,store,provider_factory):
        self.store,self.provider_factory=store,provider_factory
        self.owner=uid();self.stop_event=Event();self.wake=Event();self.thread=None;self.lock=Lock()

    def start(self):
        with self.lock:
            if self.thread and self.thread.is_alive():return
            self.stop_event.clear()
            self.thread=Thread(target=self.loop,name='sheetpilot-local-worker',daemon=True);self.thread.start()

    def stop(self):
        self.stop_event.set();self.wake.set()
        if self.thread:self.thread.join(timeout=2)

    def claim(self):
        with self.store.connection(immediate=True) as con:
            row=con.execute("SELECT workspace,payload FROM objects WHERE kind='job' AND json_extract(payload,'$.status')='queued' ORDER BY created,rowid LIMIT 1").fetchone()
            if not row:return None
            job=json.loads(row['payload']);job.update(status='running',owner=self.owner,heartbeat=now(),started_at=now())
            self.store.put(row['workspace'],'job',job,con)
            return row['workspace'],job

    def heartbeat(self,workspace,identifier,done):
        while not done.wait(1):
            try:
                with self.store.connection(immediate=True) as con:
                    job=self.store.get(workspace,'job',identifier,con)
                    if job['status']!='running' or job.get('owner')!=self.owner:return
                    job['heartbeat']=now();self.store.put(workspace,'job',job,con)
            except Exception:
                # A missing database is not permission to create a new one or
                # continue costly work. The next safe checkpoint fails closed.
                return

    def execute(self,workspace,job):
        from .agents import run_agents
        started=monotonic();done=Event()
        beat=Thread(target=self.heartbeat,args=(workspace,job['id'],done),daemon=True);beat.start()
        def checkpoint():
            current=self.store.get(workspace,'job',job['id'])
            if current['status']!='running' or current.get('owner')!=self.owner:
                raise StopJob('interrupted','This worker no longer owns the job. Explicit review/retry is required.')
            if self.stop_event.is_set():raise StopJob('interrupted','Server shutdown interrupted this job. Explicit retry is required.')
            if current['cancel_requested']:raise StopJob('cancelled','Cancelled between safe steps. Completed work and any pending proposals were preserved.')
            if monotonic()-started>=job['max_runtime_seconds']:
                raise StopJob('interrupted','Job execution budget reached at a safe boundary. Review partial results before an explicit retry.')
            if fingerprint(self.store,workspace)!=job['input_fingerprint']:
                raise StopJob('interrupted','Source or human-review context changed. Start a new job after reviewing the current data.')
            for source in job['source_versions']:
                path=self.store.root/'originals'/f"{source['id']}.xlsx"
                if not path.is_file() or digest(path)!=source['sha256']:
                    raise StopJob('interrupted','A source workbook is missing or changed. Restore the source before retrying.')
        try:
            checkpoint()
            provider=self.provider_factory()
            # One provider attempt per call. Reconnection, timeout and worker
            # recovery never replay a potentially billed generation silently.
            provider.request_attempts=1;provider.allow_completion_retry=False
            run=run_agents(self.store,workspace,job['message'],job['mode'],provider,job['task'],job['request_id'],
                           run_identifier=job['run_id'],checkpoint=checkpoint)
            status,summary=run['status'],run['summary']
        except StopJob as exc:
            status,summary=exc.state,str(exc)
        except Problem as exc:
            status,summary='failed',str(exc)
        except Exception:
            status,summary='failed','The worker stopped unexpectedly. Review the saved partial work before an explicit retry.'
        finally:
            done.set();beat.join(timeout=2)
        with self.store.connection(immediate=True) as con:
            current=self.store.get(workspace,'job',job['id'],con)
            if current.get('owner')!=self.owner or current['status']!='running':return
            current.update(status=status,summary=summary,finished_at=now(),heartbeat=now())
            run=self.store.get(workspace,'run',job['run_id'],con)
            if run['status'] in ACTIVE:run.update(status=status,summary=summary,finished_at=now(),work=work_counts(run))
            self.store.put(workspace,'job',current,con);self.store.put(workspace,'run',run,con)
            self.store.event(workspace,'job.'+status,'Durable agent job '+status+'.',{'job_id':job['id'],'run_id':run['id']},con)

    def loop(self):
        while not self.stop_event.is_set():
            try:
                recover_interrupted(self.store)
                claimed=self.claim()
                if claimed:self.execute(*claimed);continue
            except Exception:
                # Storage recovery retries the queue, never an already claimed
                # provider operation. Claimed work expires into interrupted.
                pass
            self.wake.wait(.5);self.wake.clear()
