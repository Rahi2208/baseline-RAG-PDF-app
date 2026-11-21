# main.py: FastAPI server + Inngest function
# run: uv run uvicorn data_agent.main:app --reload --port 8000
import asyncio
import logging
import uuid
from collections.abc import Callable
from pathlib import Path

import inngest
import inngest.fast_api
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from data_agent import config, pipeline
from data_agent.custom_types import InputBundle, Instructions, JobResult, Plan, Review, TableSet
from data_agent.doc_loader import classify
from data_agent.jobs import JobStatus, get_job_status, tables_to_excel

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = FastAPI(title='Data Process Agent')

# CORS: allow the frontend (different port = different "origin") to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.FRONTEND_ORIGIN],
    allow_methods=['*'],
    allow_headers=['*'],
)

inngest_client = inngest.Inngest(
    app_id='data-process-agent',
    logger=logging.getLogger('uvicorn'),
    is_production=False,
    serializer=inngest.PydanticSerializer(),
)


def in_thread(fn: Callable) -> Callable:
    # the pipeline functions are "blocking" (waiting on the LLM / reading files).
    # run them in another thread so the server can keep serving other requests
    async def wrapper(*args):
        return await asyncio.to_thread(fn, *args)
    return wrapper


# ---------- Inngest function: 5 steps ----------
@inngest_client.create_function(
    fn_id='process-data-job',
    trigger=inngest.TriggerEvent(event='data/process'),
    retries=1,
)
async def process_job(ctx: inngest.Context) -> dict:
    data = ctx.event.data
    guide_paths = [str(p) for p in data['guide_paths']]
    data_path = str(data['data_path'])
    work_dir = str(data['work_dir'])

    bundle = await ctx.step.run('load_inputs', in_thread(pipeline.step_load),
                                guide_paths, data_path, work_dir, output_type=InputBundle)
    instructions = await ctx.step.run('extract_instructions', in_thread(pipeline.step_extract),
                                      bundle, output_type=Instructions)
    plan = await ctx.step.run('make_plan', in_thread(pipeline.step_plan),
                              bundle, instructions, output_type=Plan)
    tables = await ctx.step.run('run_plan', in_thread(pipeline.step_run),
                                bundle, plan, output_type=TableSet)
    review = await ctx.step.run('review', in_thread(pipeline.step_review),
                                instructions, tables, output_type=Review)

    result = JobResult(instructions=instructions, plan=plan, tables=tables.tables, review=review)
    return result.model_dump(mode='json')


inngest.fast_api.serve(app, inngest_client, [process_job])


# ---------- endpoints for the frontend ----------
@app.get('/api/health')
async def health() -> dict:
    return {'ok': True, 'model': config.LLM_MODEL}


@app.post('/api/jobs')
async def create_job(files: list[UploadFile]) -> dict:
    # 1. check the files: at least 1 guide, exactly 1 data file
    guides = [f for f in files if classify(f.filename or '') == 'guide']
    datas = [f for f in files if classify(f.filename or '') == 'data']
    unknown = [f.filename for f in files if classify(f.filename or '') is None]
    if unknown:
        raise HTTPException(400, f'unsupported file type: {unknown}')
    if not guides:
        raise HTTPException(400, 'need at least 1 guide file (PDF/image)')
    if len(datas) != 1:
        raise HTTPException(400, 'need exactly 1 data file (.xlsx/.csv)')

    # 2. save the files to uploads/<job_id>/
    job_id = uuid.uuid4().hex
    job_dir = config.UPLOAD_DIR / job_id
    job_dir.mkdir(parents=True)
    saved: dict[str, list[str]] = {'guide': [], 'data': []}
    for f in guides + datas:
        content = await f.read()
        if len(content) > config.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(413, f'{f.filename} is larger than {config.MAX_UPLOAD_MB} MB')
        path = job_dir / Path(f.filename or 'file').name  # file name only, so it can't "escape" the folder
        path.write_bytes(content)
        saved[classify(path.name)].append(str(path))

    # 3. send an event to Inngest -> the process_job function runs in the background
    ids = await inngest_client.send(inngest.Event(name='data/process', data={
        'job_id': job_id,
        'work_dir': str(job_dir),
        'guide_paths': saved['guide'],
        'data_path': saved['data'][0],
    }))
    logger.info('job %s created, event %s', job_id, ids[0])
    return {'job_id': job_id, 'event_id': ids[0]}


@app.get('/api/jobs/{event_id}')
async def job_status(event_id: str) -> JobStatus:
    return await get_job_status(event_id)


@app.get('/api/jobs/{event_id}/export')
async def export_job(event_id: str) -> Response:
    status = await get_job_status(event_id)
    if status.status != 'completed' or not status.result:
        raise HTTPException(409, 'job is not finished yet')
    return Response(
        content=tables_to_excel(status.result),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename="result_{event_id[:8]}.xlsx"'},
    )
