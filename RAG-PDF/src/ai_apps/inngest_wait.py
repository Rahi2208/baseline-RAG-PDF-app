#wait for the result of an inngest run, used by the streamlit frontend
#why graphql: the dev server REST endpoint /v1/events/{id}/runs is not reliable. it only shows a run after ~15s,
#and then says "Completed" with an empty output even while the run is still going (seen: a 45s ingest was
#reported Completed at 15s). the dev server GraphQL endpoint shows the real status within a second.
#graphql is an internal api that can change between versions, so REST stays as a fallback when graphql
#never shows the run.
import json
import os
import time

import httpx

def _api() -> str:
    #read lazily so a .env loaded after import still counts. looks like http://127.0.0.1:8288/v1
    return os.getenv('INNGEST_API_BASE', 'http://127.0.0.1:8288/v1')

_GQL = 'query($id: ID!){ event(query:{eventId:$id}){ functionRuns{ status output } } }'
_DONE = ('COMPLETED', 'FAILED', 'CANCELLED')


def _from_gql(event_id: str):
    #returns (status, output) or None when the run is not visible yet / graphql not usable
    try:
        r = httpx.post(f"{_api().rsplit('/v1', 1)[0]}/v0/gql", json={'query': _GQL, 'variables': {'id': event_id}}, timeout=5).json()
        runs = (((r.get('data') or {}).get('event')) or {}).get('functionRuns') or []
        if not runs:
            return None
        out = runs[0].get('output')
        return runs[0]['status'].upper(), (json.loads(out) if isinstance(out, str) and out else out)
    except Exception:
        return None


def _from_rest(event_id: str):
    try:
        resp = httpx.get(f'{_api()}/events/{event_id}/runs', timeout=5)
        resp.raise_for_status()
        runs = resp.json().get('data') or []
        if not runs:
            return None
        return str(runs[0].get('status', '')).upper(), runs[0].get('output')
    except Exception:
        return None


_GQL_GRACE = 5.0  #seconds to wait for graphql to show the run before we fall back to REST


def wait_for_output(event_id: str, timeout: float = 120.0) -> dict:
    start = time.time()
    gql_seen = False
    while time.time() - start < timeout:
        got = _from_gql(event_id)
        if got:
            gql_seen = True
        elif not gql_seen and time.time() - start > _GQL_GRACE:
            got = _from_rest(event_id)
        if got and got[0] in _DONE:
            status, output = got
            if status != 'COMPLETED':
                raise RuntimeError(f'Run {status.lower()}: {output}')
            return output or {}
        time.sleep(0.3)
    raise TimeoutError('No answer from Inngest in time. Is the FastAPI server running?')
