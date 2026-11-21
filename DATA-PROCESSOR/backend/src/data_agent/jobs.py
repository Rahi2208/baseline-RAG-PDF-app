# jobs.py: asks the Inngest dev server for job status + builds the Excel file from the result
import io
from typing import Any, Literal

import httpx
import pandas as pd
from pydantic import BaseModel

from data_agent import config


class JobStatus(BaseModel):
    status: Literal['running', 'completed', 'failed']
    result: dict[str, Any] | None = None   # JobResult contents once finished
    error: str | None = None


async def get_job_status(event_id: str) -> JobStatus:
    # one event -> one "run" in Inngest. We ask for its status through the dev server's REST API
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f'{config.INNGEST_API_BASE}/events/{event_id}/runs')
        resp.raise_for_status()
        runs = resp.json().get('data') or []
        if not runs:
            return JobStatus(status='running')  # run not created yet, wait a moment

        # the per-event run list is only used to find the run_id: its status can already be
        # "Completed" while the run is still going (and its output doesn't exist yet).
        # the real status + output come from the run's own detail
        resp = await client.get(f"{config.INNGEST_API_BASE}/runs/{runs[0]['run_id']}")
        resp.raise_for_status()

    run = resp.json().get('data') or {}
    status = run.get('status')
    if status == 'Completed':
        return JobStatus(status='completed', result=run.get('output'))
    if status in ('Failed', 'Cancelled'):
        # Inngest's error output looks like {name, message, stack, ...}: take only the message
        output = run.get('output')
        message = output.get('message') if isinstance(output, dict) else None
        return JobStatus(status='failed', error=message or str(output))
    return JobStatus(status='running')


def tables_to_excel(result: dict[str, Any]) -> bytes:
    # each table becomes one sheet in the Excel file
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        for i, table in enumerate(result.get('tables', []), start=1):
            df = pd.DataFrame(table['rows'], columns=table['columns'])
            sheet = f"{i}_{table['id']}"[:31]  # Excel sheet names are at most 31 characters
            df.to_excel(writer, sheet_name=sheet, index=False)
    return buffer.getvalue()
