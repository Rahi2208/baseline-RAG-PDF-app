# test how job status is read from Inngest, using a fake Inngest server (httpx.MockTransport)
import asyncio

import httpx
import pytest

from data_agent import jobs


def fake_inngest(monkeypatch, runs: list[dict], detail: dict) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if '/events/' in request.url.path:
            return httpx.Response(200, json={'data': runs})       # list of runs per event
        return httpx.Response(200, json={'data': detail})         # detail of one run

    real_client = httpx.AsyncClient
    monkeypatch.setattr(jobs.httpx, 'AsyncClient',
                        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))


def status_of(event_id: str = 'evt') -> jobs.JobStatus:
    return asyncio.run(jobs.get_job_status(event_id))


def test_run_not_created_yet(monkeypatch):
    fake_inngest(monkeypatch, runs=[], detail={})
    assert status_of().status == 'running'


def test_list_says_completed_but_run_still_going(monkeypatch):
    # real behavior in inngest-cli 1.46: the run list already says "Completed" while the run is still going
    fake_inngest(monkeypatch,
                 runs=[{'run_id': 'r1', 'status': 'Completed', 'ended_at': None}],
                 detail={'run_id': 'r1', 'status': 'Running', 'ended_at': None})
    assert status_of().status == 'running'


def test_finished_run_carries_result(monkeypatch):
    output = {'tables': [{'id': 'results'}]}
    fake_inngest(monkeypatch,
                 runs=[{'run_id': 'r1', 'status': 'Completed'}],
                 detail={'run_id': 'r1', 'status': 'Completed', 'output': output})
    job = status_of()
    assert job.status == 'completed' and job.result == output


@pytest.mark.parametrize('status', ['Failed', 'Cancelled'])
def test_failed_run_carries_only_the_error_message(monkeypatch, status):
    # real shape of Inngest's error output: it has a stack trace that shouldn't be shown to the user
    output = {'code': 'step_errored', 'name': 'PlanError',
              'message': 'plan still failed after 3 attempts', 'stack': 'Traceback ...'}
    fake_inngest(monkeypatch,
                 runs=[{'run_id': 'r1', 'status': status}],
                 detail={'run_id': 'r1', 'status': status, 'output': output})
    job = status_of()
    assert job.status == 'failed' and job.error == 'plan still failed after 3 attempts'
