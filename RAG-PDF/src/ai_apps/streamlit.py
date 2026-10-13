#frontend for the RAG app: upload pdf -> rag/ingest_pdf, ask question -> rag/query_pdf
#run: streamlit run src/ai_apps/streamlit.py  (fastapi + inngest dev server must be running)
import os
import time
from pathlib import Path

import httpx
import inngest
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = Path('uploads')
INNGEST_API = os.getenv('INNGEST_API_BASE', 'http://127.0.0.1:8288/v1')

st.set_page_config(page_title='RAG PDF', page_icon='📄', layout='centered')


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    #same app_id as main.py so the events land in the same app
    return inngest.Inngest(app_id='rag app', is_production=False)


def send_event(name: str, data: dict) -> str:
    ids = get_inngest_client().send_sync(inngest.Event(name=name, data=data))
    return ids[0]


def wait_for_output(event_id: str, timeout: float = 120.0) -> dict:
    #ask the inngest dev server for the run triggered by this event until it finishes
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = httpx.get(f'{INNGEST_API}/events/{event_id}/runs', timeout=10)
        resp.raise_for_status()
        runs = resp.json().get('data', [])
        if runs:
            run = runs[0]
            status = run.get('status')
            if status == 'Completed':
                return run.get('output') or {}
            if status in ('Failed', 'Cancelled'):
                raise RuntimeError(f'Run {status.lower()}: {run.get("output")}')
        time.sleep(0.5)
    raise TimeoutError('No answer from Inngest in time. Is the FastAPI server running?')


def save_upload(file) -> Path:
    UPLOAD_DIR.mkdir(exist_ok=True)
    path = UPLOAD_DIR / Path(file.name).name  #basename only, so a crafted name like ../x can't escape uploads/
    path.write_bytes(file.getbuffer())
    return path.resolve()


st.title('RAG PDF')
st.caption('Upload PDFs, then ask questions answered only from their content.')

#ingest
st.header('1 · Upload a PDF')
uploaded = st.file_uploader('Choose a PDF', type=['pdf'])

if uploaded is not None and st.session_state.get('ingested_file') != uploaded.file_id:
    path = save_upload(uploaded)
    try:
        with st.spinner(f'Ingesting {uploaded.name}…'):
            event_id = send_event('rag/ingest_pdf', {'pdf_path': str(path), 'source_id': uploaded.name})
            output = wait_for_output(event_id, timeout=300)
        st.session_state['ingested_file'] = uploaded.file_id
        st.success(f'Ingested **{uploaded.name}** — {output.get("ingested", 0)} chunks stored.')
    except Exception as e:
        st.error(f'Ingestion failed: {e}')

st.divider()

#query
st.header('2 · Ask a question')
with st.form('ask'):
    question = st.text_input('Your question', placeholder='What is this document about?')
    top_k = st.number_input('Chunks to retrieve', min_value=1, max_value=20, value=5, step=1)
    asked = st.form_submit_button('Ask', type='primary')

if asked:
    if not question.strip():
        st.warning('Type a question first.')
    else:
        try:
            with st.spinner('Searching and generating answer…'):
                event_id = send_event('rag/query_pdf', {'question': question.strip(), 'top_k': int(top_k)})
                output = wait_for_output(event_id)
            st.subheader('Answer')
            st.write(output.get('answer') or '_No answer returned._')
            sources = output.get('sources') or []
            if sources:
                st.caption(f'Sources · {output.get("num_context", len(sources))} chunks used')
                for s in sources:
                    st.markdown(f'- {s}')
        except Exception as e:
            st.error(f'Query failed: {e}')
