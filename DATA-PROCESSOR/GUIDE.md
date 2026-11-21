# 📘 Data Process Agent: Complete Guide

> One file with the **concepts, prompts, dependencies, workflow, and all the code** until the app is done and maintainable.
> All the code here has been tested: **36 tests pass** and the frontend **builds successfully**. The parts that call the real Ollama model were tested with a "fake LLM", so the real model's behavior is still checked in Steps 5 and 12.
>
> 🔄 **Update 2026-10-18** (when it was actually built): adjusted for npm 12, shadcn 4, and inngest-cli 1.46.
> There are fixes in `jobs.py` (+ `tests/test_jobs.py`) and in the Inngest/shadcn commands. The details are marked with 🔄 in each step.

---

## 🧭 How to use this guide

- Work through it **in order**, one step at a time, until its ✅ Check passes, then move on
- Each step contains: 🎯 goal → 💡 concept → 🧩 commands/code → ✅ check
- All commands are written for **Arch Linux + fish**
- The code is written **in full**. Your job: type/copy it, run it, and **read the comments** so you understand it
- If you get stuck, jump to [🆘 Troubleshooting](#-troubleshooting)

### Table of contents

- [A. Concepts](#a-concepts)
- [B. Prompt for Claude](#b-prompt-for-claude)
- [C. Dependencies](#c-dependencies)
- [D. Final folder structure](#d-final-folder-structure)
- [E. Part 1: Backend (AI Agent)](#e-part-1-backend-ai-agent)
- [F. Part 2: Frontend (React)](#f-part-2-frontend-react)
- [G. Maintenance](#g-maintenance)
- [🆘 Troubleshooting](#-troubleshooting)
- [H. Next steps](#h-next-steps)

---

# A. Concepts

## A1. What does this app do?

```
INPUT                                   OUTPUT
┌──────────────────────┐                ┌───────────────────────────────┐
│ guide.pdf / photo    │                │ Table 1: Calculation Results  │
│ "compute T = t/10,   │   drag & drop  │ Table 2: Summary              │
│  g = 4π²L/T², ..."   │ ─────────────→ │ (+ formulas used)             │
│                      │   press Enter  │ (+ check of each instruction) │
│ data.xlsx            │                │ (+ Excel download)            │
│ (raw data)           │                └───────────────────────────────┘
└──────────────────────┘
```

- **Guide**: a PDF or image that explains how to process the data (formulas, rounding, table format)
- **Data**: 1 Excel/CSV file containing raw data (e.g. experiment results)
- **Result**: as many tables as the guide asks for, with columns matching the template in the guide

## A2. Main idea: the LLM understands, pandas calculates

An LLM is great at **understanding language**, but can't be relied on to **calculate thousands of numbers**. So the work is split:

```
guide.pdf ──→ LLM ──→ PLAN (JSON)          ← the LLM only translates the guide
                         ↑
data.xlsx ──→ pandas ──→ column names + 5 example rows   ← the LLM doesn't see all the data

PLAN + data.xlsx ──→ pandas ──→ result tables   ← the numbers are guaranteed correct
```

Example of a plan made by the LLM:

```json
{"tables": [{
  "id": "results", "title": "Calculation Results", "source": "data",
  "steps": [
    {"op": "compute", "new_column": "t_period", "expr": "time_10_swings_s / 10"},
    {"op": "compute", "new_column": "g", "expr": "4 * pi ** 2 * string_length_m / t_period ** 2"},
    {"op": "round", "columns": ["t_period", "g"], "decimals": 3}
  ]
}]}
```

Each `op` is a small pandas function that **we write ourselves** and that has tests. The LLM can only pick an op from the list; it can't run arbitrary code.

## A3. Process flow: 5 Inngest steps

```
1. load_inputs           read the guide (text + images) & Excel summary      [no LLM]
2. extract_instructions  LLM makes an instruction checklist from the guide   [LLM]
3. make_plan             LLM makes a JSON plan, dry-run on the real data     [LLM]
                         on error → the error message is sent back to the LLM (max 3x)
4. run_plan              pandas runs the plan                                [no LLM]
5. review                LLM checks: was each instruction followed?          [LLM]
```

Why use **Inngest**:
- Every step is **recorded**: its input, output, and errors are visible in the dashboard
- A failed step is **retried** without repeating the steps that already succeeded
- The process runs in the **background**, so the user doesn't wait on one long request

## A4. Why doesn't React talk to Inngest directly?

React runs in the **user's browser**, so it must not have access to internal systems. Everything goes through FastAPI:

```
Browser (React)
   │  POST /api/jobs (upload files)     GET /api/jobs/{id} (check status, every 1.5 seconds)
   ▼
FastAPI ──send event──→ Inngest ──runs──→ process_job function (5 steps)
   │                        │
   └──── asks for status ────┘
```

## A5. Technical decisions & why

| Decision | Reason |
|---|---|
| Ollama, model name in `.env` | Local = free & data never leaves the laptop. Moving to the cloud only needs a `.env` change. 🔄 The laptop is CPU-only right now, so use `qwen3-vl:2b-instruct` for now, then move to `glm-5.3-flash:cloud` later |
| **JSON plan + pandas** | Numbers are guaranteed correct, it's safe (no AI-written code gets executed), and easy to test |
| One `Step` model for all ops | The JSON schema stays simple, easier for a small local model to follow |
| Column names cleaned up (`String Length (m)` → `string_length_m`) | So they're safe to use in formulas |
| Every step is "dry-run" on the real data | A wrong plan is caught before the result reaches the user |
| `review` step + formulas shown in the UI | The LLM can misread a formula (e.g. `T²` becomes `T*2`), so the user must be able to check |
| Qdrant **postponed** | Guides are usually short and fit in the model's context. RAG would actually risk dropping instructions |
| One place per concern (`config.py`, `llm.py`, `prompts.py`) | Want to change a setting / model / prompt? Just open 1 file |

---

# B. Prompt for Claude

Use this prompt if you want to keep learning together with Claude (in chat or Claude Code). It's already adjusted to all the decisions above.

````markdown
# Project: Data Process Agent App

## 🎯 Concept
The user drags & drops a GUIDE file (PDF/image explaining how to process data: formulas, rounding,
table format) + 1 raw DATA file (.xlsx/.csv, e.g. experiment results), presses Enter,
and the app returns tables following the guide: the number of tables & columns follows the guide.

Project folder: DATA-PROCESSOR/ (backend/ + frontend/).
The full guide + all the code is in the GUIDE.md file at the project root. Read it first.

## 👤 About me
- Fullstack beginner, learn best through hands-on projects
- Arch Linux, fish shell, using uv for Python
- CPU-only laptop (Intel, 11.5 GB RAM): local models ≥ 8B run out of RAM
- I want to understand and be able to maintain this app. No vibe coding.

## 🧠 Architecture (already decided)
- LLM: Ollama, model name in .env. Right now LOCAL `qwen3-vl:2b-instruct`
  (LLM_NUM_CTX=8192, LLM_THINK=false), moving to `glm-5.3-flash:cloud` later.
  The LLM only makes a JSON PLAN, pandas does the calculating through the list of ops in operations.py
  (compute, filter, select, rename, sort, round, group_agg, aggregate, linear_fit).
  Formulas are validated with ast.
- Backend: uv, Python 3.12, src/data_agent/, FastAPI + Inngest (5 steps:
  load_inputs → extract_instructions → make_plan → run_plan → review),
  Pydantic in custom_types.py, all LLM calls go through llm.py, prompts in prompts.py
- Frontend: Vite + React + TypeScript, Tailwind, shadcn/ui, TanStack Query (polling),
  TanStack Table v9, react-dropzone. React only talks to FastAPI, never to Inngest.
- Qdrant is postponed until the basic flow works.

## 🧭 Working rules (REQUIRED)
1. One step per reply. YOU write the full code, but in stages.
2. Each step: 💡 short concept → 🧩 full code + comments → ✅ how to check.
3. Stop and wait until I say "continue" or send a result/error.
   If I send an error, review it first before continuing.
4. Simple explanations, one idea per section, no long paragraphs.
5. Want to change an architecture decision above? Give reasons + alternatives, ask me first.

## 🔧 Maintenance (keep doing this)
- uv.lock & package-lock.json are committed, .env is not committed
- every new feature has a test (uv run pytest)
- every time the prompt/model changes: run uv run data-agent-eval
- types.ts in the frontend must match custom_types.py

## ▶️ Now
[write which step I'm on / what I want to do]
````

---

# C. Dependencies

## C1. Tools on your computer

| Tool | What it's for | Install (Arch) |
|---|---|---|
| `uv` | manages the Python project & packages | `sudo pacman -S uv` |
| `nodejs` + `npm` | React frontend + Inngest dev server | `sudo pacman -S nodejs npm` |
| `ollama` | local AI model server | `sudo pacman -S ollama-cuda` (NVIDIA) / `ollama-rocm` (AMD) / `ollama` (CPU) |
| `git` | version control | `sudo pacman -S git` |

## C2. Backend (Python)

| Package | What it's for |
|---|---|
| `ollama` | Python client for calling the model |
| `python-dotenv` | reads the `.env` file |
| `pydantic` | data shapes + validation (comes with FastAPI automatically) |
| `pymupdf` | extracts PDF text + renders scanned pages to images |
| `pandas` | processes tables / calculates formulas |
| `numpy` | linear regression (`linear_fit`) |
| `openpyxl` | lets pandas read & write `.xlsx` |
| `fastapi` | API server |
| `uvicorn` | runs the FastAPI server |
| `python-multipart` | required so FastAPI can accept file uploads |
| `inngest` | background process steps + dashboard |
| `httpx` | asks Inngest for job status |
| `pytest` *(dev)* | testing |

## C3. Frontend (npm)

| Package | What it's for |
|---|---|
| `react`, `vite`, `typescript` | app skeleton (from the Vite template) |
| `tailwindcss`, `@tailwindcss/vite` | styling |
| shadcn/ui (`button`, `card`, `table`, `badge`, `alert`) | ready-made components, the code is copied into your project |
| `@tanstack/react-query` | submitting the job + status polling |
| `@tanstack/react-table` (v9) | sortable result tables |
| `react-dropzone` | drag & drop files |
| `lucide-react` | icons (installed along with `shadcn init`) |
| `@types/node` *(dev)* | so `vite.config.ts` recognizes the `node:path` module |

---

# D. Final folder structure

```
DATA-PROCESSOR/
├─ GUIDE.md                    ← this file
├─ README.md
├─ backend/
│  ├─ .env / .env.example
│  ├─ .gitignore
│  ├─ pyproject.toml / uv.lock / .python-version
│  ├─ playground/              ← place for experiments, not part of the app
│  │  ├─ try_ask.py
│  │  └─ try_structured.py
│  ├─ samples/
│  │  ├─ make_pendulum.py      ← builds the pendulum sample
│  │  └─ pendulum/  guide.pdf  data.xlsx  expected.json
│  ├─ src/data_agent/
│  │  ├─ __init__.py
│  │  ├─ config.py             ← reads .env
│  │  ├─ custom_types.py       ← data shapes (Pydantic)
│  │  ├─ llm.py                ← the only thing that calls the model
│  │  ├─ doc_loader.py         ← reads the guide & Excel
│  │  ├─ operations.py         ← list of pandas ops + formula validation
│  │  ├─ executor.py           ← runs the plan
│  │  ├─ prompts.py            ← all prompts
│  │  ├─ pipeline.py           ← 5 process stages (plain functions)
│  │  ├─ cli.py                ← run from the terminal
│  │  ├─ evaluate.py           ← checks all samples
│  │  ├─ jobs.py               ← job status + Excel export
│  │  └─ main.py               ← FastAPI + Inngest
│  └─ tests/
│     ├─ conftest.py
│     ├─ test_doc_loader.py  test_operations.py  test_executor.py
│     ├─ test_pipeline.py  test_api.py  test_jobs.py  test_inngest_function.py
└─ frontend/
   ├─ .env / .env.example
   ├─ components.json          ← created by shadcn
   ├─ vite.config.ts / tsconfig*.json / package.json / package-lock.json
   └─ src/
      ├─ main.tsx / App.tsx / index.css
      ├─ api/       types.ts  client.ts  files.ts
      ├─ hooks/     useJob.ts
      ├─ lib/       utils.ts   ← created by shadcn
      └─ components/
         ├─ FileDropzone.tsx  ResultTable.tsx  ReviewList.tsx
         └─ ui/     ← created by shadcn (button, card, table, badge, alert)
```

---
# E. Part 1: Backend (AI Agent)

## Step 0: Set up tools

🎯 **Goal:** all tools installed, model downloaded, Ollama server running.

💡 **Concept:** Ollama runs as a **background server**. The terminal & Python code just "talk" to that server:

```
Python code → Ollama server (localhost:11434) → qwen3-vl model on your GPU/CPU
```

🧩 **Commands:**

```fish
# 1. check the GPU: to choose the model size
lspci | grep -iE 'vga|3d'
nvidia-smi          # if NVIDIA: look at the Memory column (VRAM)
free -h             # if CPU only: look at "available" RAM

# 2. install tools (pick ONE ollama package for your GPU)
sudo pacman -S uv nodejs npm git
sudo pacman -S ollama-cuda      # NVIDIA
# sudo pacman -S ollama-rocm    # AMD
# sudo pacman -S ollama         # CPU only

# 3. start the ollama server (starts automatically on every boot)
sudo systemctl enable --now ollama

# 4. download the model + test it (change the model name per the table below)
ollama pull qwen3-vl:8b
ollama run qwen3-vl:8b "hello, answer in one sentence"
```

Pick the model size:

| VRAM | Model |
|---|---|
| ≥ 8 GB | `qwen3-vl:8b` ⭐ |
| 4–6 GB | `qwen3-vl:4b` |
| < 4 GB / CPU | `qwen3-vl:2b-instruct` (slow) |

> 🔄 **If CPU only:** use the `-instruct` version (not `-thinking`): a "thinking" model writes hundreds of tokens before answering, and on CPU every token is expensive.
> Also add `LLM_NUM_CTX=8192` and `LLM_THINK=false` to `.env` (Step 1).
> Real example: Intel laptop without a GPU, 11.5 GB RAM → `qwen3-vl:8b` with a 16384 context was **killed by the kernel (OOM)**, and a 1B model only managed ~2.7 tokens/second.

✅ **Check:**

```fish
uv --version; node --version; npm --version; ollama --version
curl http://localhost:11434      # → Ollama is running
ollama list                      # → the model you pulled is listed
ollama ps                        # (while the model is loaded) PROCESSOR column: 100% GPU = great
```

---

## Step 1: Init the backend project

🎯 **Goal:** the Python project skeleton using `uv`.

💡 **Concept:** what's inside a uv project:

```
pyproject.toml   → the list of dependencies you asked for
uv.lock          → the EXACT versions of all packages (locked, committed)
.venv/           → where packages are installed (not committed)
src/data_agent/  → your code
```

`uv run ...` automatically uses `.venv`, so **no need to activate** it.

🧩 **Commands:**

```fish
cd ~/Projects/"AI APPS"          # adjust to your location
mkdir -p DATA-PROCESSOR/backend
cd DATA-PROCESSOR/backend

uv init --package --name data-agent --python 3.12 --vcs none
uv add ollama python-dotenv pymupdf pandas numpy openpyxl fastapi uvicorn python-multipart inngest httpx
uv add --dev pytest
```

| Flag | Meaning |
|---|---|
| `--package` | `src/` layout, same as RAG-PDF |
| `--name data-agent` | the code folder becomes `src/data_agent/` |
| `--python 3.12` | if it's not installed, uv downloads it itself |
| `--vcs none` | don't create a git repo here (there's only one git repo, in `DATA-PROCESSOR/`) |

> ⚠️ Because of `--vcs none`, uv does **not** create a `.gitignore`. We create it manually below.

Create `backend/.gitignore`:

```gitignore
# python junk files
__pycache__/
*.py[oc]
.pytest_cache/

# where packages are installed, can be recreated with `uv sync`
.venv/

# secrets & local settings
.env

# files uploaded by users (may contain personal data)
uploads/
```

Create `backend/.env` (the real settings, **not** committed). Adjust the model name to your choice in Step 0:

```fish
printf 'OLLAMA_HOST=http://localhost:11434\nLLM_MODEL=qwen3-vl:8b\n' > .env
```

> Fish has no `<<EOF` like bash, so `printf` is used to write multiple lines (`\n` = newline).

🔄 Version for a CPU-only laptop (the one in use now):

```fish
printf 'OLLAMA_HOST=http://localhost:11434\nLLM_MODEL=qwen3-vl:2b-instruct\nLLM_NUM_CTX=8192\nLLM_THINK=false\n' > .env
```

Create `backend/.env.example` (a full example of all settings, **committed**):

```bash
# --- LLM ---
OLLAMA_HOST=http://localhost:11434
LLM_MODEL=qwen3-vl:8b
# context length; lower it (e.g. 8192) if the GPU runs out of memory
LLM_NUM_CTX=16384
# set to "false" if the model "thinks" too long
LLM_THINK=

# --- documents ---
MAX_GUIDE_PAGES=20
MAX_UPLOAD_MB=20
UPLOAD_DIR=uploads

# --- server ---
INNGEST_API_BASE=http://127.0.0.1:8288/v1
FRONTEND_ORIGIN=http://localhost:5173
```

Edit `pyproject.toml` to look exactly like this. What changed: `description`, the `[project.scripts]` section (2 commands), and `[tool.pytest.ini_options]`. The version numbers (in `dependencies` and `build-system`) may differ, follow yours:

```toml
[project]
name = "data-agent"
version = "0.1.0"
description = "Agent that turns raw data into tables following a guide"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.143.3",
    "httpx>=0.28.1",
    "inngest>=0.5.19",
    "numpy>=2.5.4",
    "ollama>=0.6.3",
    "openpyxl>=3.1.5",
    "pandas>=3.0.6",
    "pymupdf>=1.28.2",
    "python-dotenv>=1.2.4",
    "python-multipart>=0.0.32",
    "uvicorn>=0.54.0",
]

[project.scripts]
data-agent = "data_agent.cli:main"
data-agent-eval = "data_agent.evaluate:main"

[build-system]
requires = ["uv_build>=0.12.23,<0.13.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "pytest>=9.1.1",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

Replace the contents of `src/data_agent/__init__.py` with a single comment line:

```python
# data_agent: agent that turns raw data into tables following a guide
```

> Why empty it? `uv init` puts a `main()` function here. We move that function to `cli.py` (Step 12), so the name doesn't clash with the `main.py` file (the server).

✅ **Check:**

```fish
ls -a                 # you should see .env .env.example .gitignore pyproject.toml uv.lock .venv src
uv run python -c "import ollama, pandas, fastapi, inngest, pymupdf; print('all packages OK')"
```

---

## Step 2: `config.py`: one door for `.env`

🎯 **Goal:** all settings are read in one place.

💡 **Concept:**

```python
os.getenv('OLLAMA_HOST', 'http://localhost:11434')  # missing? use the default
os.environ['LLM_MODEL']                              # missing? CRASH right away
```

Crashing is **good** for required settings: better a clear error at startup than the app quietly using the wrong model.

🧩 Create `src/data_agent/config.py`:

```python
# config.py: the only file that reads .env
# every other file just does: from data_agent import config
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # find the .env file and load its contents into environment variables


def _optional_bool(name: str) -> bool | None:
    # "true"/"false" -> True/False, empty -> None (let ollama use the model default)
    value = os.getenv(name, '').strip().lower()
    if value in ('true', '1', 'yes'):
        return True
    if value in ('false', '0', 'no'):
        return False
    return None


# --- LLM ---
OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
LLM_MODEL = os.environ['LLM_MODEL']  # required: crash right away if it's missing
LLM_NUM_CTX = int(os.getenv('LLM_NUM_CTX', '16384'))  # context length (tokens)
LLM_THINK = _optional_bool('LLM_THINK')  # turn off "thinking mode" if it's too slow: LLM_THINK=false

# --- documents ---
MAX_GUIDE_PAGES = int(os.getenv('MAX_GUIDE_PAGES', '20'))
MAX_UPLOAD_MB = int(os.getenv('MAX_UPLOAD_MB', '20'))
UPLOAD_DIR = Path(os.getenv('UPLOAD_DIR', 'uploads')).resolve()

# --- server ---
INNGEST_API_BASE = os.getenv('INNGEST_API_BASE', 'http://127.0.0.1:8288/v1')
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173')
```

✅ **Check:**

```fish
uv run python -c "from data_agent import config; print(config.LLM_MODEL, config.UPLOAD_DIR)"
```

Your model name + `/.../backend/uploads` should appear. Try deleting the `LLM_MODEL` line from `.env` → you should get `KeyError: 'LLM_MODEL'`. Then put it back.

---

## Step 3: `llm.py`: the only door to the model

🎯 **Goal:** be able to call the model from Python, while logging tokens & speed.

💡 **Concept 1:** every other file calls the model **through `llm.py`**. Want to change the model / provider / add retries? Just change this file.

💡 **Concept 2:** Ollama's response contains more than the answer:

```python
res.message.content     # the answer text
res.prompt_eval_count   # INPUT tokens
res.eval_count          # OUTPUT tokens
res.total_duration      # time in NANOseconds (÷ 1e9 = seconds)
```

💡 **Concept 3:** `logging` > `print`: every line automatically has the time, level, and name of the file it came from.

💡 **Concept 4:** `structured()` forces the model to answer according to a **Pydantic schema** (`format=`), then validates the result. If the JSON is wrong, the model is told what was wrong and asked again.

🧩 Create `src/data_agent/llm.py`:

```python
# llm.py: the only file that talks to the model
# want to switch model/provider? just change this file
import logging
from typing import TypeVar

from ollama import Client
from pydantic import BaseModel, ValidationError

from data_agent import config

logger = logging.getLogger(__name__)
client = Client(host=config.OLLAMA_HOST)  # connection to the ollama server

T = TypeVar('T', bound=BaseModel)
MAX_FORMAT_RETRIES = 2  # if the model's JSON doesn't match the schema, retry this many times


def _chat(messages: list[dict], schema: dict | None, label: str) -> str:
    res = client.chat(
        model=config.LLM_MODEL,
        messages=messages,
        format=schema,                    # force the answer to match the JSON schema
        think=config.LLM_THINK,           # None = model default
        options={
            'temperature': 0,             # 0 = most consistent answers
            'num_ctx': config.LLM_NUM_CTX,
        },
    )
    # ollama reports time in NANOseconds -> divide by 1e9 to get seconds
    seconds = (res.total_duration or 0) / 1e9
    tps = (res.eval_count or 0) / ((res.eval_duration or 1) / 1e9)
    logger.info(
        '[%s] model=%s input=%s output=%s time=%.1fs speed=%.1f tok/s',
        label, config.LLM_MODEL, res.prompt_eval_count, res.eval_count, seconds, tps,
    )
    return res.message.content


def ask(prompt: str) -> str:
    # plain text answer
    return _chat([{'role': 'user', 'content': prompt}], schema=None, label='ask')


def structured(prompt: str, schema: type[T], images: list[str] | None = None,
               label: str = 'llm') -> T:
    # answer as a Pydantic model (schema)
    message: dict = {'role': 'user', 'content': prompt}
    if images:
        message['images'] = images  # image paths, ollama reads the files itself
    messages = [message]

    for attempt in range(1, MAX_FORMAT_RETRIES + 2):
        content = _chat(messages, schema.model_json_schema(), f'{label}#{attempt}')
        try:
            return schema.model_validate_json(content)
        except ValidationError as e:
            logger.warning('[%s] output does not match schema (attempt %s): %s', label, attempt, e)
            # tell the model what was wrong, then ask again
            messages = [
                message,
                {'role': 'assistant', 'content': content},
                {'role': 'user', 'content': f'Your JSON was invalid:\n{e}\nReturn corrected JSON only.'},
            ]
    raise ValueError(f'[{label}] model failed to give valid JSON')
```

Create a folder for experiments (`mkdir playground`), then create `playground/try_ask.py`:

```python
# try_ask.py: first test of chatting with the model (not part of the app, just for trying things out)
# run: uv run python playground/try_ask.py
import logging

from data_agent import config, llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)

print('host :', config.OLLAMA_HOST)
print('model:', config.LLM_MODEL)
print(llm.ask('State the formula for the period of a simple pendulum in one line'))
```

✅ **Check:**

```fish
uv run python playground/try_ask.py
uv run python playground/try_ask.py     # run it twice
```

Expected result, roughly:

```
host : http://localhost:11434
model: qwen3-vl:8b
2026-10-18 05:00:12 INFO data_agent.llm: [ask] model=qwen3-vl:8b input=24 output=31 time=2.3s speed=35.2 tok/s
T = 2π √(L/g)
```

| `speed` | Meaning |
|---|---|
| ≥ 20 tok/s | running on the GPU 👍 |
| 5–20 | partly spilling over to the CPU |
| < 5 | full CPU → consider a smaller model, or Ollama cloud |

The first run takes longer because the model has to be loaded into the GPU/RAM first.

---

## Step 4: `custom_types.py`: data shapes between steps

🎯 **Goal:** all data passed between steps has a clear shape.

💡 **Concept:** Pydantic = the data "security guard". If the LLM gives JSON with the wrong shape, it's caught right here, not later in the middle of a calculation.

The models follow the process flow in order:

```
InputBundle → Instructions → Plan (TablePlan → Step) → ResultTable → Review → JobResult
```

💡 Why is `Step` just **one model** with many optional fields (instead of one model per op)? The JSON schema stays simple, easier for a small local model to follow. The required parameters per op are checked in `operations.py`.

🧩 Create `src/data_agent/custom_types.py`:

```python
# custom_types.py: the "shape" of the data passed between steps
# Pydantic checks the shape automatically, so bad data is caught right away
from typing import Any, Literal

from pydantic import BaseModel


# ---------- 1. input after reading ----------
class SheetSummary(BaseModel):
    name: str                      # sheet name in the Excel file
    columns: list[str]             # column names (already cleaned up, see doc_loader)
    dtypes: dict[str, str]         # data type of each column
    n_rows: int
    sample_rows: list[dict[str, Any]]  # a few example rows for the LLM


class InputBundle(BaseModel):
    guide_text: str                # text from the guide (PDF)
    guide_images: list[str]        # image paths (guide photos / scanned PDF pages)
    data_path: str                 # path to the Excel/CSV file
    sheets: list[SheetSummary]


# ---------- 2. LLM output: list of instructions ----------
class Instructions(BaseModel):
    items: list[str]               # each instruction in the guide, one per item
    expected_tables: list[str]     # which tables the guide asks for


# ---------- 3. LLM output: processing plan ----------
OpName = Literal[
    'compute', 'filter', 'select', 'rename', 'sort',
    'round', 'group_agg', 'aggregate', 'linear_fit',
]
AggFunc = Literal['mean', 'sum', 'min', 'max', 'count', 'std', 'median']


class Aggregation(BaseModel):
    column: str                    # column to aggregate
    func: AggFunc                  # function: mean, sum, ...
    output: str                    # name of the resulting column


class RenamePair(BaseModel):
    old: str
    new: str


class Step(BaseModel):
    # one model for all ops (not one model per op),
    # so the schema stays simple and easy for a small local model to follow.
    # the required parameters per op are checked in operations.py
    op: OpName
    new_column: str | None = None          # compute
    expr: str | None = None                # compute (formula) / filter (condition)
    columns: list[str] | None = None       # select / round
    renames: list[RenamePair] | None = None  # rename
    by: list[str] | None = None            # sort / group_agg
    descending: bool | None = None         # sort
    decimals: int | None = None            # round
    aggregations: list[Aggregation] | None = None  # group_agg / aggregate
    x: str | None = None                   # linear_fit
    y: str | None = None                   # linear_fit


class TablePlan(BaseModel):
    id: str                        # unique id, e.g. "result_g"
    title: str                     # title to display
    source: str                    # sheet name OR the id of an earlier table
    steps: list[Step]


class Plan(BaseModel):
    tables: list[TablePlan]


# ---------- 4. final result ----------
class ResultTable(BaseModel):
    id: str
    title: str
    columns: list[str]
    rows: list[list[Any]]
    formulas: list[str]            # steps/formulas used, shown in the UI


class TableSet(BaseModel):
    tables: list[ResultTable]


class CheckItem(BaseModel):
    instruction: str
    done: bool
    note: str


class Review(BaseModel):
    items: list[CheckItem]


class JobResult(BaseModel):
    instructions: Instructions
    plan: Plan
    tables: list[ResultTable]
    review: Review
```

✅ **Check:**

```fish
uv run python -c "from data_agent.custom_types import Plan; import json; print(json.dumps(Plan.model_json_schema())[:300])"
```

A snippet of the JSON schema appears = this is what will be sent to the model through `format=`.

---

## Step 5: Test structured output (important!)

🎯 **Goal:** make sure your local model **follows the JSON schema**. This is the foundation of the whole app.

🧩 Create `playground/try_structured.py`:

```python
# try_structured.py: test the model answering in JSON that matches a Pydantic schema
# run: uv run python playground/try_structured.py
import logging

from pydantic import BaseModel

from data_agent import llm

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logging.getLogger('httpx').setLevel(logging.WARNING)


class Formula(BaseModel):
    name: str
    formula: str
    variables: list[str]


result = llm.structured('Explain the formula for the period of a simple pendulum.', Formula, label='try')
print(type(result))    # <class '__main__.Formula'>  -> already a Python object, not text
print(result.formula)
print(result.variables)
```

✅ **Check:**

```fish
uv run python playground/try_structured.py
```

Expected: `<class '__main__.Formula'>` + the formula + the list of variables.

If it fails:
- the warning "output does not match schema" appears many times → the model is too small, try a bigger model or Ollama cloud
- extremely slow → set `LLM_THINK=false` in `.env` (turns off thinking mode)
- `out of memory` / Ollama dies on its own → lower `LLM_NUM_CTX=8192` in `.env`, or use a smaller model

---

## Step 6: `doc_loader.py` + first sample

🎯 **Goal:** read the guide (PDF/image) & data (Excel/CSV), plus build a sample for tests.

💡 **Concept 1:** PDF pages with little text (scans) or with images (e.g. a formula as an image) are **rendered to PNG**, so a vision model can "see" them.

💡 **Concept 2:** column names are cleaned up:

```
"String Length (m)"    → "string_length_m"
"Time 10 Swings (s)"   → "time_10_swings_s"
"10 cm"                → "c_10_cm"   (can't start with a digit)
```

💡 **Concept 3:** the LLM is only given **5 example rows** + column names & types, not all the data.

🧩 Create `src/data_agent/doc_loader.py`:

```python
# doc_loader.py: reads the input files
#   guide (PDF/image) -> text + images for the LLM
#   data (Excel/CSV)  -> pandas DataFrame + column summary for the LLM
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Literal

import pandas as pd
import pymupdf

from data_agent import config
from data_agent.custom_types import InputBundle, SheetSummary

logger = logging.getLogger(__name__)

GUIDE_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.webp'}
DATA_EXTENSIONS = {'.xlsx', '.csv'}
SAMPLE_ROWS = 5          # example rows given to the LLM (not all the data!)
MIN_TEXT_CHARS = 50      # pages with less text than this are treated as scans
RENDER_DPI = 110         # resolution when rendering PDF pages to images


def classify(filename: str) -> Literal['guide', 'data'] | None:
    # guess the file type from its extension
    ext = Path(filename).suffix.lower()
    if ext in GUIDE_EXTENSIONS:
        return 'guide'
    if ext in DATA_EXTENSIONS:
        return 'data'
    return None


def normalize_column(name: object) -> str:
    # "String Length (m)" -> "string_length_m"
    # so column names are safe to use in formulas (no spaces / symbols)
    text = str(name).strip().lower()
    text = re.sub(r'[^0-9a-z]+', '_', text).strip('_')
    if not text:
        text = 'column'
    if text[0].isdigit():
        text = f'c_{text}'
    return text


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    seen: dict[str, int] = {}
    new_names = []
    for col in df.columns:
        name = normalize_column(col)
        if name in seen:  # duplicate name -> add a number: value, value_2
            seen[name] += 1
            name = f'{name}_{seen[name]}'
        else:
            seen[name] = 1
        new_names.append(name)
    df = df.copy()
    df.columns = new_names
    return df


def read_data(path: str) -> dict[str, pd.DataFrame]:
    # return {sheet_name: DataFrame}; a CSV counts as one sheet named "data"
    p = Path(path)
    if p.suffix.lower() == '.csv':
        sheets = {'data': pd.read_csv(p)}
    else:
        sheets = pd.read_excel(p, sheet_name=None)  # None = read all sheets
    return {
        normalize_column(name): _normalize_columns(df.dropna(how='all'))
        for name, df in sheets.items()
    }


def summarize_sheets(sheets: dict[str, pd.DataFrame]) -> list[SheetSummary]:
    summaries = []
    for name, df in sheets.items():
        # to_json -> json.loads: easy way to turn numpy/NaN types into plain JSON types
        sample = json.loads(df.head(SAMPLE_ROWS).to_json(orient='records'))
        summaries.append(SheetSummary(
            name=name,
            columns=list(df.columns),
            dtypes={col: str(dtype) for col, dtype in df.dtypes.items()},
            n_rows=len(df),
            sample_rows=sample,
        ))
    return summaries


def load_guide(path: str, out_dir: Path) -> tuple[str, list[str]]:
    # PDF -> extract the text; scanned / image pages are also rendered to PNG
    # image (photo) -> used as is
    p = Path(path)
    if p.suffix.lower() != '.pdf':
        return '', [str(p)]

    texts: list[str] = []
    images: list[str] = []
    with pymupdf.open(p) as doc:
        for i, page in enumerate(doc):
            if i >= config.MAX_GUIDE_PAGES:
                logger.warning('guide %s truncated at %s pages', p.name, config.MAX_GUIDE_PAGES)
                break
            text = page.get_text().strip()
            if text:
                texts.append(f'--- {p.name} page {i + 1} ---\n{text}')
            if len(text) < MIN_TEXT_CHARS or page.get_images():
                img_path = out_dir / f'{p.stem}_page{i + 1}.png'
                page.get_pixmap(dpi=RENDER_DPI).save(img_path)
                images.append(str(img_path))
    return '\n\n'.join(texts), images


def load_inputs(guide_paths: list[str], data_path: str, work_dir: str) -> InputBundle:
    out_dir = Path(work_dir) / 'rendered'
    shutil.rmtree(out_dir, ignore_errors=True)  # clear leftovers from the previous run (on retry)
    out_dir.mkdir(parents=True)

    all_text: list[str] = []
    all_images: list[str] = []
    for gp in guide_paths:
        text, images = load_guide(gp, out_dir)
        if text:
            all_text.append(text)
        all_images.extend(images)

    sheets = read_data(data_path)
    logger.info('input: %s guide(s), %s image(s), sheets=%s',
                len(guide_paths), len(all_images), list(sheets))
    return InputBundle(
        guide_text='\n\n'.join(all_text),
        guide_images=all_images,
        data_path=data_path,
        sheets=summarize_sheets(sheets),
    )
```

🧩 Create the `samples/` and `tests/` folders first:

```fish
mkdir -p samples tests
```

🧩 Create `samples/make_pendulum.py`. This script builds a guide PDF, an Excel data file, and the **correct answer** (calculated by hand, not with the app):

```python
# make_pendulum.py: builds the first sample (simple pendulum lab) for tests & evaluation
# run from the backend folder: uv run python samples/make_pendulum.py
import json
import math
from pathlib import Path

import pandas as pd
import pymupdf

OUT = Path(__file__).parent / 'pendulum'
OUT.mkdir(exist_ok=True)

# ---------- 1. raw data (Excel) ----------
data = pd.DataFrame({
    'Trial': [1, 2, 3, 4, 5],
    'String Length (m)': [0.3, 0.5, 0.7, 0.9, 1.1],
    'Time 10 Swings (s)': [11.02, 14.15, 16.83, 19.01, 21.10],
})
data.to_excel(OUT / 'data.xlsx', sheet_name='Data', index=False)

# ---------- 2. guide (PDF) ----------
GUIDE = """DATA PROCESSING GUIDE - SIMPLE PENDULUM LAB

The raw data is in the Excel file (sheet Data).

Processing steps:
1. Calculate the period of one swing: T = t / 10, where t = time for 10 swings.
2. Calculate the gravitational acceleration: g = 4 x pi^2 x L / T^2, where L = string length.
3. Round T and g to 3 decimal places.

Table 1 - Calculation Results, with columns in this order:
| Trial | L (m) | T (s) | g (m/s2) |

Table 2 - Summary, containing:
- mean g (rounded to 3 decimals)
- percent error against the literature g of 9.8 m/s2:
  error = |mean g - 9.8| / 9.8 x 100 (rounded to 2 decimals)
"""
doc = pymupdf.open()
page = doc.new_page()
page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), GUIDE, fontsize=11)
doc.save(OUT / 'guide.pdf')

# ---------- 3. the correct answer (calculated by hand, NOT using the app) ----------
rows = []
for p, L, t in data.itertuples(index=False):
    T = round(t / 10, 3)
    g = round(4 * math.pi ** 2 * L / (t / 10) ** 2, 3)
    rows.append([p, L, T, g])
g_mean = round(sum(r[3] for r in rows) / len(rows), 3)
error = round(abs(g_mean - 9.8) / 9.8 * 100, 2)

expected = {'tables': [
    {'title': 'Calculation Results', 'columns': ['Trial', 'L (m)', 'T (s)', 'g (m/s2)'], 'rows': rows},
    {'title': 'Summary', 'columns': ['mean g', 'error (%)'], 'rows': [[g_mean, error]]},
]}
(OUT / 'expected.json').write_text(json.dumps(expected, indent=2))
print('sample created at', OUT)
```

```fish
uv run python samples/make_pendulum.py
```

🧩 Create `tests/conftest.py`. This file is set up by pytest before any test runs, and contains the **correct plan** for the pendulum sample:

```python
# conftest.py: set up by pytest before any test runs
import os
import subprocess
import sys
from pathlib import Path

import pytest

# tests don't need a real .env; config.py only needs LLM_MODEL to be non-empty
os.environ.setdefault('LLM_MODEL', 'test-model')

from data_agent.custom_types import Aggregation, Plan, RenamePair, Step, TablePlan  # noqa: E402

BACKEND = Path(__file__).parent.parent
SAMPLE = BACKEND / 'samples' / 'pendulum'


@pytest.fixture(scope='session')
def pendulum_dir() -> Path:
    # create the sample files if they don't exist yet
    if not (SAMPLE / 'expected.json').exists():
        subprocess.run([sys.executable, str(SAMPLE.parent / 'make_pendulum.py')], check=True)
    return SAMPLE


@pytest.fixture
def pendulum_plan() -> Plan:
    # the CORRECT plan for the pendulum sample (an ideal LLM answer)
    return Plan(tables=[
        TablePlan(id='results', title='Calculation Results', source='data', steps=[
            Step(op='compute', new_column='t_period', expr='time_10_swings_s / 10'),
            Step(op='compute', new_column='g', expr='4 * pi ** 2 * string_length_m / t_period ** 2'),
            Step(op='round', columns=['t_period', 'g'], decimals=3),
            Step(op='rename', renames=[
                RenamePair(old='trial', new='Trial'),
                RenamePair(old='string_length_m', new='L (m)'),
                RenamePair(old='t_period', new='T (s)'),
                RenamePair(old='g', new='g (m/s2)'),
            ]),
            Step(op='select', columns=['Trial', 'L (m)', 'T (s)', 'g (m/s2)']),
        ]),
        TablePlan(id='summary', title='Summary', source='results', steps=[
            Step(op='aggregate', aggregations=[
                Aggregation(column='g (m/s2)', func='mean', output='g_mean'),
            ]),
            Step(op='round', columns=['g_mean'], decimals=3),
            Step(op='compute', new_column='error', expr='abs(g_mean - 9.8) / 9.8 * 100'),
            Step(op='round', columns=['error'], decimals=2),
            Step(op='rename', renames=[
                RenamePair(old='g_mean', new='mean g'),
                RenamePair(old='error', new='error (%)'),
            ]),
        ]),
    ])
```

🧩 Create `tests/test_doc_loader.py`:

```python
import pandas as pd
import pymupdf
import pytest

from data_agent.doc_loader import classify, load_inputs, normalize_column, read_data


@pytest.mark.parametrize('raw, clean', [
    ('String Length (m)', 'string_length_m'),
    ('  Time 10 Swings (s) ', 'time_10_swings_s'),
    ('10 cm', 'c_10_cm'),
    ('%%%', 'column'),
])
def test_normalize_column(raw, clean):
    assert normalize_column(raw) == clean


def test_classify():
    assert classify('guide.PDF') == 'guide'
    assert classify('photo.jpg') == 'guide'
    assert classify('data.xlsx') == 'data'
    assert classify('virus.exe') is None


def test_read_data_duplicate_column_names(tmp_path):
    path = tmp_path / 'd.csv'
    pd.DataFrame([[1, 2]], columns=['Value', 'value ']).to_csv(path, index=False)
    sheets = read_data(str(path))
    assert list(sheets['data'].columns) == ['value', 'value_2']


def test_load_inputs_scanned_pdf_page_is_rendered(tmp_path):
    # page 1 has text, page 2 is empty (like a scan) -> page 2 becomes an image
    pdf = tmp_path / 'guide.pdf'
    doc = pymupdf.open()
    doc.new_page().insert_text((50, 72), 'Calculate the average of the value column. ' * 5)
    doc.new_page()
    doc.save(pdf)
    data = tmp_path / 'data.csv'
    pd.DataFrame({'Value': [1, 2, 3]}).to_csv(data, index=False)

    bundle = load_inputs([str(pdf)], str(data), str(tmp_path / 'job'))

    assert 'average' in bundle.guide_text
    assert len(bundle.guide_images) == 1 and bundle.guide_images[0].endswith('page2.png')
    assert bundle.sheets[0].columns == ['value'] and bundle.sheets[0].n_rows == 3
```

✅ **Check:**

```fish
uv run pytest tests/test_doc_loader.py -v
```

All `PASSED`. Also look at the `samples/pendulum/` folder: open `guide.pdf` and `data.xlsx`.

---

## Step 7: `operations.py`: list of ops + formula validation

🎯 **Goal:** the pandas functions a plan is allowed to use, plus a formula guard.

💡 **Concept 1: formula validation with `ast`.** The formula is broken into a "tree", then each piece is checked:

```
"4 * pi ** 2 * string_length_m"  ✅ number, constant, column
"__import__('os').system('ls')"  ❌ function not allowed
"a.__class__"                    ❌ attribute access
"T ^ 2"                          ❌ ^ isn't power in Python → message: use **
```

💡 **Concept 2: `PlanError`.** Every plan mistake becomes a `PlanError` with a clear message. This message is later **sent back to the LLM** so it can fix its own plan.

💡 **Concept 3: the `OPERATIONS` registry.** A dictionary `op name → function`. Adding a new op = write a function + register it in the dictionary (see [G4](#g4-how-to-add-a-new-op)).

🧩 Create `src/data_agent/operations.py`:

```python
# operations.py: the "dictionary" of pandas operations a plan is allowed to use
# the LLM only picks an op + parameters; our code does the calculating (so results are deterministic)
import ast
import math

import numpy as np
import pandas as pd

from data_agent.custom_types import Step


class PlanError(Exception):
    # error caused by a bad plan (missing column, odd formula, etc.)
    # the message is sent back to the LLM so it can fix the plan
    pass


CONSTANTS = {'pi': math.pi, 'e': math.e}
ALLOWED_FUNCS = {'sqrt', 'abs', 'log', 'log10', 'exp', 'sin', 'cos', 'tan'}

# allowed kinds of formula "pieces". Anything else (attribute access, import, lambda, etc.) is rejected
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.Name, ast.Load, ast.Constant, ast.Call,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.FloorDiv,
    ast.USub, ast.UAdd, ast.Not, ast.And, ast.Or, ast.BitAnd, ast.BitOr,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)


def validate_expr(expr: str, columns: list[str]) -> None:
    # check the formula BEFORE running it: only numbers, column names, constants, math functions allowed
    if '^' in expr:
        raise PlanError(f"formula '{expr}' uses '^'. For powers use '**'")
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError as e:
        raise PlanError(f"formula '{expr}' is not valid: {e.msg}") from e

    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise PlanError(f"formula '{expr}' uses disallowed syntax: {type(node).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ALLOWED_FUNCS:
                raise PlanError(f"formula '{expr}': the only allowed functions are {sorted(ALLOWED_FUNCS)}")
            if node.keywords:
                raise PlanError(f"formula '{expr}': functions cannot take named arguments")
        if isinstance(node, ast.Name):
            allowed = set(columns) | set(CONSTANTS) | ALLOWED_FUNCS
            if node.id not in allowed:
                raise PlanError(f"formula '{expr}': '{node.id}' is not a column. Available columns: {columns}")


def _need(step: Step, *names: str) -> None:
    # make sure the required parameters for this op are filled in
    for name in names:
        if getattr(step, name) in (None, [], ''):
            raise PlanError(f"op '{step.op}' needs parameter '{name}'")


def _check_columns(df: pd.DataFrame, cols: list[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise PlanError(f'columns {missing} do not exist. Available columns: {list(df.columns)}')


# ---------- one function per op ----------

def op_compute(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # create a new column from a formula, e.g. T = time_10_swings / 10
    _need(step, 'new_column', 'expr')
    validate_expr(step.expr, list(df.columns))
    df = df.copy()
    df[step.new_column] = df.eval(step.expr, resolvers=[CONSTANTS])
    return df


def op_filter(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # filter rows, e.g. trial > 1 and string_length <= 1
    _need(step, 'expr')
    validate_expr(step.expr, list(df.columns))
    return df.query(step.expr, resolvers=[CONSTANTS])


def op_select(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # pick + order columns (used to match a template's format)
    _need(step, 'columns')
    _check_columns(df, step.columns)
    return df[step.columns]


def op_rename(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    _need(step, 'renames')
    mapping = {r.old: r.new for r in step.renames}
    _check_columns(df, list(mapping))
    return df.rename(columns=mapping)


def op_sort(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    _need(step, 'by')
    _check_columns(df, step.by)
    return df.sort_values(step.by, ascending=not step.descending)


def op_round(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # if columns is empty: round all numeric columns
    _need(step, 'decimals')
    cols = step.columns or list(df.select_dtypes('number').columns)
    _check_columns(df, cols)
    df = df.copy()
    df[cols] = df[cols].round(step.decimals)
    return df


def op_group_agg(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # mean/sum per group, e.g. mean g per string_length
    _need(step, 'by', 'aggregations')
    _check_columns(df, step.by + [a.column for a in step.aggregations])
    named = {a.output: (a.column, a.func) for a in step.aggregations}
    return df.groupby(step.by, as_index=False).agg(**named)


def op_aggregate(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # one-row summary of the whole data, e.g. mean g
    _need(step, 'aggregations')
    _check_columns(df, [a.column for a in step.aggregations])
    row = {a.output: df[a.column].agg(a.func) for a in step.aggregations}
    return pd.DataFrame([row])


def op_linear_fit(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # linear regression y = slope * x + intercept, plus R²
    _need(step, 'x', 'y')
    _check_columns(df, [step.x, step.y])
    x = df[step.x].astype(float).to_numpy()
    y = df[step.y].astype(float).to_numpy()
    if len(x) < 2:
        raise PlanError('linear_fit needs at least 2 rows of data')
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = float(((y - y_pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else 1.0
    return pd.DataFrame([{'slope': slope, 'intercept': intercept, 'r2': r2}])


OPERATIONS = {
    'compute': op_compute,
    'filter': op_filter,
    'select': op_select,
    'rename': op_rename,
    'sort': op_sort,
    'round': op_round,
    'group_agg': op_group_agg,
    'aggregate': op_aggregate,
    'linear_fit': op_linear_fit,
}


def apply_step(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    try:
        return OPERATIONS[step.op](df, step)
    except PlanError:
        raise
    except Exception as e:  # other pandas errors are also turned into PlanError so the LLM can fix them
        raise PlanError(f"op '{step.op}' failed: {type(e).__name__}: {e}") from e


def describe_step(step: Step) -> str:
    # "human" version of each step, shown under the table
    match step.op:
        case 'compute':
            return f'{step.new_column} = {step.expr}'
        case 'filter':
            return f'filter: {step.expr}'
        case 'select':
            return f"columns: {', '.join(step.columns or [])}"
        case 'rename':
            return 'rename: ' + ', '.join(f'{r.old} → {r.new}' for r in step.renames or [])
        case 'sort':
            direction = 'high → low' if step.descending else 'low → high'
            return f"sort {', '.join(step.by or [])} ({direction})"
        case 'round':
            cols = ', '.join(step.columns) if step.columns else 'all numbers'
            return f'round {cols} to {step.decimals} decimals'
        case 'group_agg' | 'aggregate':
            aggs = ', '.join(f'{a.output} = {a.func}({a.column})' for a in step.aggregations or [])
            per = f" per {', '.join(step.by)}" if step.op == 'group_agg' and step.by else ''
            return f'{aggs}{per}'
        case 'linear_fit':
            return f'linear regression: {step.y} = slope × {step.x} + intercept'
    return step.op
```

🧩 Create `tests/test_operations.py`:

```python
import pandas as pd
import pytest

from data_agent.custom_types import Aggregation, Step
from data_agent.operations import PlanError, apply_step, validate_expr

COLS = ['a', 'b']


def df() -> pd.DataFrame:
    return pd.DataFrame({'a': [1.0, 4.0, 9.0], 'b': [2, 2, 3], 'group': ['x', 'y', 'x']})


# ---------- formula validation ----------
def test_valid_formula_passes():
    validate_expr('sqrt(a) * pi + b ** 2', COLS)


@pytest.mark.parametrize('expr', [
    "__import__('os').system('ls')",  # trying to run a system command
    'a.__class__',                     # attribute access
    'c + 1',                           # column does not exist
    'a ^ 2',                           # ^ is not power in Python
    'max(a)',                          # function not allowed
])
def test_dangerous_or_wrong_formula_rejected(expr):
    with pytest.raises(PlanError):
        validate_expr(expr, COLS)


# ---------- each op ----------
def test_compute():
    out = apply_step(df(), Step(op='compute', new_column='c', expr='a / b'))
    assert out['c'].tolist() == [0.5, 2.0, 3.0]


def test_filter():
    out = apply_step(df(), Step(op='filter', expr="a > 2 and group == 'x'"))
    assert out['a'].tolist() == [9.0]


def test_round_all_numeric_columns():
    data = pd.DataFrame({'x': [1.23456], 'y': [2.98765], 'name': ['a']})
    out = apply_step(data, Step(op='round', decimals=2))
    assert out.iloc[0].tolist() == [1.23, 2.99, 'a']


def test_group_agg():
    step = Step(op='group_agg', by=['group'],
                aggregations=[Aggregation(column='a', func='sum', output='total')])
    out = apply_step(df(), step)
    assert dict(zip(out['group'], out['total'])) == {'x': 10.0, 'y': 4.0}


def test_aggregate_becomes_one_row():
    step = Step(op='aggregate', aggregations=[Aggregation(column='a', func='mean', output='avg')])
    out = apply_step(df(), step)
    assert out.shape == (1, 1) and out['avg'][0] == pytest.approx(14 / 3)


def test_linear_fit():
    data = pd.DataFrame({'x': [1, 2, 3], 'y': [3, 5, 7]})  # y = 2x + 1
    out = apply_step(data, Step(op='linear_fit', x='x', y='y'))
    assert out['slope'][0] == pytest.approx(2)
    assert out['intercept'][0] == pytest.approx(1)
    assert out['r2'][0] == pytest.approx(1)


def test_missing_required_parameter():
    with pytest.raises(PlanError, match="needs parameter 'expr'"):
        apply_step(df(), Step(op='compute', new_column='c'))


def test_column_does_not_exist():
    with pytest.raises(PlanError, match='do not exist'):
        apply_step(df(), Step(op='select', columns=['zzz']))
```

✅ **Check:**

```fish
uv run pytest tests/test_operations.py -v
```

---

## Step 8: `executor.py`: run the plan

🎯 **Goal:** run the `Plan` table by table, step by step.

💡 **Concept:** tables that are already built are kept in `frames`, so they can be used as the `source` of the next table. Example: the "Summary" table takes the average from the "Results" table.

```
frames = {"data": <Excel sheet>}
table "results"  (source="data")    → frames["results"] = ...
table "summary"  (source="results") → uses the previous table's result
```

🧩 Create `src/data_agent/executor.py`:

```python
# executor.py: runs the plan (Plan) step by step with pandas
import json

import pandas as pd

from data_agent.custom_types import Plan, ResultTable
from data_agent.operations import PlanError, apply_step, describe_step


def to_result_table(table_id: str, title: str, df: pd.DataFrame, formulas: list[str]) -> ResultTable:
    # to_json -> json.loads: turn NaN into null and numpy types into plain numbers
    data = json.loads(df.to_json(orient='split', index=False))
    return ResultTable(id=table_id, title=title, columns=data['columns'],
                       rows=data['data'], formulas=formulas)


def run_plan(plan: Plan, sheets: dict[str, pd.DataFrame]) -> list[ResultTable]:
    frames = dict(sheets)  # data sources: Excel sheets + tables already built
    results: list[ResultTable] = []

    for table in plan.tables:
        if table.source not in frames:
            raise PlanError(
                f"table '{table.id}': source '{table.source}' does not exist. "
                f'Available: {list(frames)}'
            )
        df = frames[table.source]
        for i, step in enumerate(table.steps, start=1):
            try:
                df = apply_step(df, step)
            except PlanError as e:
                raise PlanError(f"table '{table.id}', step {i}: {e}") from e

        frames[table.id] = df  # this table can be the source of the next table
        formulas = [describe_step(s) for s in table.steps]
        results.append(to_result_table(table.id, table.title, df, formulas))

    return results
```

🧩 Create `src/data_agent/evaluate.py` right now too, because its `compare()` function is used in tests (how to run the eval script is in Step 13):

```python
# evaluate.py: runs every example in samples/ and compares it with expected.json
# run: uv run data-agent-eval
# use it every time you change the model / edit a prompt, to see whether results got better or worse
import json
import logging
import math
import sys
import tempfile
from pathlib import Path

from data_agent.doc_loader import classify

SAMPLES_DIR = Path('samples')
TOLERANCE = 1e-3  # relative difference still counted as equal


def _same(a, b) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=TOLERANCE, abs_tol=TOLERANCE)
    return str(a).strip() == str(b).strip()


def compare(expected: list[dict], actual: list[dict]) -> list[str]:
    # return a list of problems; empty = pass
    problems = []
    if len(expected) != len(actual):
        problems.append(f'number of tables: expected {len(expected)}, got {len(actual)}')
    for i, (exp, act) in enumerate(zip(expected, actual), start=1):
        if len(exp['rows']) != len(act['rows']):
            problems.append(f"table {i}: {len(act['rows'])} rows, expected {len(exp['rows'])}")
            continue
        for r, (er, ar) in enumerate(zip(exp['rows'], act['rows']), start=1):
            if len(er) != len(ar) or not all(_same(x, y) for x, y in zip(er, ar)):
                problems.append(f'table {i} row {r}: got {ar}, expected {er}')
                break
    return problems


def main() -> None:
    # imported inside the function: compare() can be used in tests without setting up the pipeline/LLM
    from data_agent.pipeline import run_all

    logging.basicConfig(level=logging.WARNING)
    folders = sorted(p for p in SAMPLES_DIR.iterdir() if (p / 'expected.json').exists())
    passed = 0
    for folder in folders:
        files = [str(f) for f in folder.iterdir() if classify(f.name)]
        guides = [f for f in files if classify(f) == 'guide']
        data = [f for f in files if classify(f) == 'data'][0]
        expected = json.loads((folder / 'expected.json').read_text())['tables']

        with tempfile.TemporaryDirectory() as work_dir:
            try:
                result = run_all(guides, data, work_dir)
                problems = compare(expected, [t.model_dump() for t in result.tables])
            except Exception as e:
                problems = [f'error: {e}']

        if problems:
            print(f'❌ {folder.name}')
            for p in problems:
                print('   -', p)
        else:
            passed += 1
            print(f'✅ {folder.name}')

    print(f'\n{passed}/{len(folders)} samples passed')
    sys.exit(0 if passed == len(folders) else 1)
```

🧩 Create `tests/test_executor.py`:

```python
import json

import pytest

from data_agent.custom_types import Plan, Step, TablePlan
from data_agent.doc_loader import read_data
from data_agent.evaluate import compare
from data_agent.executor import run_plan
from data_agent.operations import PlanError


def test_pendulum_plan_matches_answer(pendulum_dir, pendulum_plan):
    sheets = read_data(str(pendulum_dir / 'data.xlsx'))
    tables = run_plan(pendulum_plan, sheets)
    expected = json.loads((pendulum_dir / 'expected.json').read_text())['tables']

    assert compare(expected, [t.model_dump() for t in tables]) == []
    assert tables[0].columns == ['Trial', 'L (m)', 'T (s)', 'g (m/s2)']  # template format
    assert 'g = 4 * pi ** 2 * string_length_m / t_period ** 2' in tables[0].formulas


def test_wrong_source(pendulum_dir):
    sheets = read_data(str(pendulum_dir / 'data.xlsx'))
    plan = Plan(tables=[TablePlan(id='x', title='X', source='does_not_exist', steps=[])])
    with pytest.raises(PlanError, match="source 'does_not_exist'"):
        run_plan(plan, sheets)


def test_error_mentions_table_and_step(pendulum_dir):
    sheets = read_data(str(pendulum_dir / 'data.xlsx'))
    plan = Plan(tables=[TablePlan(id='results', title='R', source='data', steps=[
        Step(op='compute', new_column='T', expr='time / 10'),  # column "time" does not exist
    ])])
    with pytest.raises(PlanError, match="table 'results', step 1"):
        run_plan(plan, sheets)
```

✅ **Check:**

```fish
uv run pytest tests/test_executor.py -v
```

`test_pendulum_plan_matches_answer` passes = the ops + executor calculate exactly like the manual answer. 🎉

---

## Step 9: `prompts.py`: all prompts in one place

🎯 **Goal:** 3 prompts: extract instructions, make the plan, review.

💡 **Concept:**
- prompts are written in **English** (the model is more consistent), but the model is asked to keep the **document's language** for table titles & contents
- `OPS_REFERENCE` = the ops "manual" for the LLM. **It must always match** the contents of `operations.py`
- `make_plan()` can accept a previous plan + error message for retries

🧩 Create `src/data_agent/prompts.py`:

```python
# prompts.py: all prompt texts are collected here
# prompts are written in English because the model is more consistent that way,
# but the model is asked to keep the document's language for table titles & contents
import json

from data_agent.custom_types import InputBundle, Instructions, Plan, ResultTable

OPS_REFERENCE = """
Available operations (field "op") and their parameters:
- compute:    new_column, expr   -> add a column from a formula, e.g. expr "time / 10"
- filter:     expr               -> keep rows where the condition is true, e.g. "value > 0 and group == 'A'"
- select:     columns            -> keep and ORDER these columns (use it last to match a template)
- rename:     renames [{old, new}] -> rename columns (use it to match column names in a template)
- sort:       by, descending
- round:      decimals, columns (optional, empty = all numeric columns)
- group_agg:  by, aggregations [{column, func, output}] -> one row per group
- aggregate:  aggregations [{column, func, output}]     -> ONE summary row for the whole table
- linear_fit: x, y               -> one row with slope, intercept, r2
func is one of: mean, sum, min, max, count, std, median

Formula rules (expr):
- use ONLY column names that exist at that point (listed below, plus columns you created earlier)
- power is ** (never ^). Constants: pi, e. Functions: sqrt, abs, log, log10, exp, sin, cos, tan
- strings in conditions use single quotes: group == 'A'

Table rules:
- each table has: id (snake_case, unique), title (in the document's language), source, steps
- source is a sheet name from the data OR the id of an EARLIER table
  (e.g. a summary table can use source = id of the detailed table)
- make exactly one table for each table the guide asks for, in the same order
""".strip()


def _data_block(bundle: InputBundle) -> str:
    parts = []
    for s in bundle.sheets:
        parts.append(
            f'Sheet "{s.name}" ({s.n_rows} rows)\n'
            f'Columns and types: {json.dumps(s.dtypes)}\n'
            f'First rows: {json.dumps(s.sample_rows, ensure_ascii=False)}'
        )
    return '\n\n'.join(parts)


def _guide_block(bundle: InputBundle) -> str:
    text = bundle.guide_text or '(no extractable text, read the attached images)'
    note = f'\n({len(bundle.guide_images)} guide image(s) attached)' if bundle.guide_images else ''
    return text + note


def extract_instructions(bundle: InputBundle) -> str:
    return f"""You read a GUIDE that explains how to process raw (experimental) data into tables.

List every instruction in the guide as short, self-contained items:
formulas (write them exactly), rounding, filters, units, sorting,
and the required table layout (column names and their order) if the guide shows a template.
Also list the tables the guide asks for, in order.
Do not invent instructions that are not in the guide. Keep the guide's language.

GUIDE:
{_guide_block(bundle)}

DATA (only the structure and first rows, for context):
{_data_block(bundle)}"""


def make_plan(bundle: InputBundle, instructions: Instructions,
              previous: Plan | None = None, error: str | None = None) -> str:
    retry = ''
    if previous is not None and error:
        retry = f"""

Your previous plan FAILED with this error:
{error}
Previous plan:
{previous.model_dump_json()}
Fix the problem and return the full corrected plan."""

    return f"""Turn these instructions into a processing plan that will be executed with pandas.
Do NOT calculate numbers yourself; only describe the steps.

{OPS_REFERENCE}

INSTRUCTIONS:
{json.dumps(instructions.items, ensure_ascii=False, indent=1)}

TABLES REQUESTED:
{json.dumps(instructions.expected_tables, ensure_ascii=False)}

DATA:
{_data_block(bundle)}{retry}"""


def review(instructions: Instructions, tables: list[ResultTable]) -> str:
    preview = [
        {'title': t.title, 'columns': t.columns, 'first_rows': t.rows[:5], 'steps': t.formulas}
        for t in tables
    ]
    return f"""Check whether each instruction was followed in the result tables.
For every instruction give: instruction (copy it), done (true/false), note (short reason,
in the instruction's language). Be strict: a wrong formula or a missing column means done = false.

INSTRUCTIONS:
{json.dumps(instructions.items, ensure_ascii=False, indent=1)}

RESULT TABLES:
{json.dumps(preview, ensure_ascii=False, indent=1)}"""
```

✅ **Check:**

```fish
uv run python -c "from data_agent import prompts; print(prompts.OPS_REFERENCE[:200])"
```

---

## Step 10: `pipeline.py`: 5 stages as plain functions

🎯 **Goal:** each process stage becomes a plain function that can be tested without Inngest.

💡 **Concept 1:** `main.py` will just wrap each of these functions as 1 Inngest step. Since they're plain functions, they're easy to test & run from the terminal.

💡 **Concept 2: self-correction.** In `step_plan`, the plan is **tested right away on the real data**. On error, the error message is sent to the LLM to fix (max 3x):

```
LLM: compute T = time / 10
pandas: ❌ 'time' is not a column. Available columns: [trial, string_length_m, time_10_swings_s]
LLM: compute T = time_10_swings_s / 10   ✅
```

💡 **Concept 3: tests with a fake LLM (`monkeypatch`).** In tests, `llm.structured` is replaced by a fake function whose answers we decided in advance. So tests run fast, free, and always give the same result.

🧩 Create `src/data_agent/pipeline.py`:

```python
# pipeline.py: the processing stages, each a plain function
# main.py wraps each of these functions as one Inngest step,
# but since they're plain functions, they're easy to test and run without Inngest
import logging

from data_agent import llm, prompts
from data_agent.custom_types import InputBundle, Instructions, JobResult, Plan, Review, TableSet
from data_agent.doc_loader import load_inputs, read_data
from data_agent.executor import run_plan
from data_agent.operations import PlanError

logger = logging.getLogger(__name__)
MAX_PLAN_ATTEMPTS = 3  # plan failed to run -> the error is sent to the LLM to fix


def step_load(guide_paths: list[str], data_path: str, work_dir: str) -> InputBundle:
    return load_inputs(guide_paths, data_path, work_dir)


def step_extract(bundle: InputBundle) -> Instructions:
    return llm.structured(prompts.extract_instructions(bundle), Instructions,
                          images=bundle.guide_images, label='extract')


def step_plan(bundle: InputBundle, instructions: Instructions) -> Plan:
    sheets = read_data(bundle.data_path)
    plan: Plan | None = None
    error: str | None = None

    for attempt in range(1, MAX_PLAN_ATTEMPTS + 1):
        prompt = prompts.make_plan(bundle, instructions, previous=plan, error=error)
        plan = llm.structured(prompt, Plan, label='plan')
        try:
            run_plan(plan, sheets)  # "dry run" on the real data: errors show up here
            return plan
        except PlanError as e:
            error = str(e)
            logger.warning('plan failed (attempt %s): %s', attempt, error)

    raise PlanError(f'plan still failed after {MAX_PLAN_ATTEMPTS} attempts: {error}')


def step_run(bundle: InputBundle, plan: Plan) -> TableSet:
    return TableSet(tables=run_plan(plan, read_data(bundle.data_path)))


def step_review(instructions: Instructions, tables: TableSet) -> Review:
    return llm.structured(prompts.review(instructions, tables.tables), Review, label='review')


def run_all(guide_paths: list[str], data_path: str, work_dir: str) -> JobResult:
    # all stages in order, without Inngest (for the CLI & evaluation)
    bundle = step_load(guide_paths, data_path, work_dir)
    instructions = step_extract(bundle)
    plan = step_plan(bundle, instructions)
    tables = step_run(bundle, plan)
    review = step_review(instructions, tables)
    return JobResult(instructions=instructions, plan=plan, tables=tables.tables, review=review)
```

🧩 Create `tests/test_pipeline.py`:

```python
# test the pipeline WITHOUT a real model: llm.structured is replaced by a fake function (monkeypatch)
from data_agent import pipeline
from data_agent.custom_types import Instructions, Plan, Review, Step, TablePlan


def test_bad_plan_gets_fixed_using_the_error_message(pendulum_dir, pendulum_plan, monkeypatch):
    bad_plan = Plan(tables=[TablePlan(id='results', title='R', source='data', steps=[
        Step(op='compute', new_column='T', expr='time / 10'),  # wrong column
    ])])
    answers = [bad_plan, pendulum_plan]  # first answer is wrong, second is correct
    prompts_seen = []

    def fake_structured(prompt, schema, images=None, label=''):
        prompts_seen.append(prompt)
        return answers.pop(0)

    monkeypatch.setattr(pipeline.llm, 'structured', fake_structured)
    bundle = pipeline.step_load([str(pendulum_dir / 'guide.pdf')], str(pendulum_dir / 'data.xlsx'),
                                str(pendulum_dir.parent.parent / 'uploads' / 'test'))
    plan = pipeline.step_plan(bundle, Instructions(items=['T = t / 10'], expected_tables=['R']))

    assert plan == pendulum_plan
    assert 'FAILED' in prompts_seen[1] and "'time' is not a column" in prompts_seen[1]


def test_run_all_with_fake_llm(pendulum_dir, pendulum_plan, monkeypatch, tmp_path):
    def fake_structured(prompt, schema, images=None, label=''):
        if schema is Instructions:
            return Instructions(items=['calculate T', 'calculate g'], expected_tables=['Results', 'Summary'])
        if schema is Plan:
            return pendulum_plan
        return Review(items=[])

    monkeypatch.setattr(pipeline.llm, 'structured', fake_structured)
    result = pipeline.run_all([str(pendulum_dir / 'guide.pdf')], str(pendulum_dir / 'data.xlsx'), str(tmp_path))
    assert [t.title for t in result.tables] == ['Calculation Results', 'Summary']
    assert result.tables[1].rows == [[9.791, 0.09]]
```

✅ **Check:**

```fish
uv run pytest -v
```

All the tests so far pass.

---

## Step 11: (break) first commit

🎯 **Goal:** save progress to git.

```fish
cd ..                     # to the DATA-PROCESSOR folder
git init                  # if DATA-PROCESSOR isn't inside another repo yet
git add backend
git status                # make sure .env, .venv, uploads are NOT in the list
git commit -m "backend: loader, operations, executor, pipeline + tests"
cd backend
```

> If `DATA-PROCESSOR` is **inside** the `AI APPS` repo (next to RAG-PDF), skip `git init` and just `git add`. A git repo inside another git repo is a hassle.

---

## Step 12: `cli.py`: run it with the real model 🚀

🎯 **Goal:** run the **whole pipeline** with Ollama for the first time, from the terminal.

🧩 Create `src/data_agent/cli.py`:

```python
# cli.py: CLI for running the pipeline straight from the terminal (no server)
# example: uv run data-agent samples/pendulum/guide.pdf samples/pendulum/data.xlsx
import argparse
import json
import logging
import tempfile


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    logging.getLogger('httpx').setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(description='Process raw data following a guide')
    parser.add_argument('files', nargs='+', help='guide file(s) (PDF/image) + 1 data file (.xlsx/.csv)')
    parser.add_argument('--json', action='store_true', help='print the full result as JSON')
    args = parser.parse_args()

    # imported here so `--help` still works even without a .env file
    from data_agent.doc_loader import classify
    from data_agent.pipeline import run_all

    guides = [f for f in args.files if classify(f) == 'guide']
    datas = [f for f in args.files if classify(f) == 'data']
    if not guides or len(datas) != 1:
        parser.error('need at least 1 guide and exactly 1 data file')

    with tempfile.TemporaryDirectory() as work_dir:
        result = run_all(guides, datas[0], work_dir)

    if args.json:
        print(json.dumps(result.model_dump(mode='json'), ensure_ascii=False, indent=2))
        return

    for table in result.tables:
        print(f'\n=== {table.title} ===')
        print(' | '.join(table.columns))
        for row in table.rows:
            print(' | '.join(str(v) for v in row))
        print('formulas:', '; '.join(table.formulas))
    print('\n=== instruction check ===')
    for item in result.review.items:
        print('✅' if item.done else '❌', item.instruction, '-', item.note)
```

✅ **Check:**

```fish
uv run data-agent samples/pendulum/guide.pdf samples/pendulum/data.xlsx
```

Expected: logs of 3 LLM calls (`extract`, `plan`, `review`), then 2 tables:

```
=== Calculation Results ===
Trial | L (m) | T (s) | g (m/s2)
1 | 0.3 | 1.102 | 9.753
...
=== Summary ===
mean g | error (%)
9.791 | 0.09
```

Want to see the plan the LLM made? Add `--json`. If the numbers differ, compare its plan with `pendulum_plan` in `tests/conftest.py`. It usually differs in the order of rounding or in column names.

> 🔄 On a CPU-only laptop, this command can take **a dozen to several dozen minutes**. Watch the log: each `data_agent.llm` line = 1 model call finished.

---

## Step 13: `evaluate.py`: automatic report card

🎯 **Goal:** one command to check all samples. Run it every time you **change the model** or **edit a prompt**.

`evaluate.py` was already created in Step 8, and its command was already registered in `pyproject.toml` (Step 1).

✅ **Check:**

```fish
uv run data-agent-eval
```

```
✅ pendulum

1/1 samples passed
```

Adding a new sample = create a new folder in `samples/` containing a guide + data + `expected.json` (see [G5](#g5-how-to-add-a-new-sample)).

---

## Step 14: `jobs.py` + `main.py`: FastAPI + Inngest server

🎯 **Goal:** the pipeline can be called through an API and runs in the background via Inngest.

💡 **Concept 1: endpoints.**

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | check the server is alive + which model |
| `POST /api/jobs` | upload files → save → send event to Inngest → return `event_id` |
| `GET /api/jobs/{event_id}` | status: `running` / `completed` / `failed` (+ result) |
| `GET /api/jobs/{event_id}/export` | download the result as Excel |
| `/api/inngest` | used by the Inngest dev server (automatic) |

💡 **Concept 2: `in_thread`.** The pipeline functions are "blocking" (waiting on the LLM). They run in another thread so the server can keep serving other requests (e.g. status checks).

💡 **Concept 3: upload security.**
- only certain extensions are accepted
- at most `MAX_UPLOAD_MB`
- `Path(filename).name` → a file name like `../../x.xlsx` can't "escape" the upload folder

💡 **Concept 4: CORS.** The frontend (`localhost:5173`) and backend (`localhost:8000`) are different "origins". The browser blocks cross-origin requests unless the server says they're allowed through `CORSMiddleware`.

💡 🔄 **Concept 5: job status from Inngest.** The Inngest dev server has 2 endpoints that look similar:

```
GET /v1/events/{event_id}/runs   → list of runs for 1 event   (only used to find the run_id)
GET /v1/runs/{run_id}            → detail of 1 run            (the CORRECT status + output)
```

In inngest-cli 1.46, the run list per event can already say `"Completed"` while the run is **still going** (`ended_at: null`, no `output` yet). If you only use the first endpoint, the frontend stops polling and shows an empty result. So `jobs.py` takes the status from the second endpoint.

🧩 Create `src/data_agent/jobs.py`:

```python
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
```

🧩 Create `src/data_agent/main.py`:

```python
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
```

🧩 Create `tests/test_api.py`:

```python
# test the FastAPI endpoints with TestClient (no real server needed)
import pytest
from fastapi.testclient import TestClient

from data_agent import main


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main.config, 'UPLOAD_DIR', tmp_path)
    sent = []

    async def fake_send(event):  # stands in for sending the event to Inngest
        sent.append(event)
        return ['event-123']

    monkeypatch.setattr(main.inngest_client, 'send', fake_send)
    c = TestClient(main.app)
    c.sent = sent
    return c


def test_health(client):
    assert client.get('/api/health').json()['ok'] is True


def test_upload_without_data_file_rejected(client):
    res = client.post('/api/jobs', files=[('files', ('guide.pdf', b'%PDF', 'application/pdf'))])
    assert res.status_code == 400 and 'data file' in res.json()['detail']


def test_upload_unknown_file_type_rejected(client):
    res = client.post('/api/jobs', files=[('files', ('virus.exe', b'x', 'application/octet-stream'))])
    assert res.status_code == 400


def test_valid_upload_sends_event(client, tmp_path):
    files = [
        ('files', ('guide.pdf', b'%PDF', 'application/pdf')),
        ('files', ('../../data.xlsx', b'xlsx', 'application/octet-stream')),  # "naughty" file name
    ]
    res = client.post('/api/jobs', files=files)
    assert res.status_code == 200 and res.json()['event_id'] == 'event-123'

    data = client.sent[0].data
    assert data['data_path'].startswith(str(tmp_path))  # stays inside the upload folder
    assert data['data_path'].endswith('data.xlsx')
```

🧩 🔄 Create `tests/test_jobs.py`. Inngest is faked with `httpx.MockTransport`, so no dev server is needed:

```python
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
```

🧩 Create `tests/test_inngest_function.py`. Inngest has a "mocked" client for testing the 5-step function without a dev server:

```python
# test the full Inngest function (5 steps) using Inngest's "mocked" client + a fake LLM
import inngest
from inngest.experimental import mocked

from data_agent import main, pipeline
from data_agent.custom_types import Instructions, Plan, Review


def test_process_job_runs_to_completion(pendulum_dir, pendulum_plan, monkeypatch, tmp_path):
    def fake_structured(prompt, schema, images=None, label=''):
        if schema is Instructions:
            return Instructions(items=['calculate g'], expected_tables=['Results', 'Summary'])
        if schema is Plan:
            return pendulum_plan
        return Review(items=[])

    monkeypatch.setattr(pipeline.llm, 'structured', fake_structured)
    client = mocked.Inngest(app_id='test', serializer=inngest.PydanticSerializer())
    event = inngest.Event(name='data/process', data={
        'job_id': 'test',
        'work_dir': str(tmp_path),
        'guide_paths': [str(pendulum_dir / 'guide.pdf')],
        'data_path': str(pendulum_dir / 'data.xlsx'),
    })

    res = mocked.trigger(main.process_job, event, client)

    assert res.status == mocked.Status.COMPLETED
    assert [t['id'] for t in res.output['tables']] == ['results', 'summary']
```

✅ **Check:**

```fish
uv run pytest -v          # 36 tests pass
```

---

## Step 15: Run the server + Inngest dev server

🎯 **Goal:** the backend really runs, and jobs can be sent through the API and monitored in the dashboard.

🧩 Open **2 terminals**, both in the `backend/` folder:

```fish
# terminal 1: FastAPI server
uv run uvicorn data_agent.main:app --reload --port 8000
```

```fish
# terminal 2: Inngest dev server (dashboard at http://localhost:8288)
npx --allow-scripts=inngest-cli inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery
```

> 🔄 **npm 12:** a package's install script only runs if its name is in `allow-scripts`. `inngest-cli` needs an install script to download its binary, so `--allow-scripts=inngest-cli` is required. The old `--ignore-scripts=false` flag is **no longer enough**.

✅ **Check:** in **terminal 3**, send a job with `curl`:

```fish
curl http://localhost:8000/api/health

curl -F files=@samples/pendulum/guide.pdf -F files=@samples/pendulum/data.xlsx http://localhost:8000/api/jobs
# → {"job_id":"...","event_id":"01J..."}

curl http://localhost:8000/api/jobs/<event_id>
# repeat until "status":"completed"
```

Open **http://localhost:8288** → **Runs** menu → click the run. There you can see the 5 steps, each step's input/output, how long it took, and the error if there is one. 🎉

Download the Excel file: open `http://localhost:8000/api/jobs/<event_id>/export` in the browser.

**Part 1 is done.** Commit first:

```fish
cd ..; git add backend; git commit -m "backend: cli, eval, FastAPI + Inngest"; cd backend
```

---
# F. Part 2: Frontend (React)

## Step F0: Create the Vite + React + TypeScript project

🎯 **Goal:** the frontend skeleton.

🧩 From the `DATA-PROCESSOR/` folder:

```fish
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
npm install tailwindcss @tailwindcss/vite @tanstack/react-query @tanstack/react-table react-dropzone
npm install -D @types/node
```

Delete the sample files that aren't used:

```fish
rm -f src/App.css
rm -rf src/assets
```

Change the tab title in `index.html`: `<title>frontend</title>` → `<title>Data Process Agent</title>`.

Add `.env` to `frontend/.gitignore`:

```fish
printf '\n# local settings\n.env\n' >> .gitignore
```

Create `.env` (the backend address) and its example:

```fish
printf 'VITE_API_URL=http://localhost:8000\n' > .env
cp .env .env.example
```

> Env variables in Vite **must** start with `VITE_` to be readable from browser code. Never put secrets here: everything `VITE_` is visible to users.

✅ **Check:** `npm run dev` → open http://localhost:5173 → the Vite sample page appears.

---

## Step F1: Tailwind + `@/` alias + shadcn/ui

🎯 **Goal:** styling is ready, and the shadcn components are installed.

💡 **Concept: the `@/` alias.** So imports don't become `../../../components/...`:

```ts
import { Button } from '@/components/ui/button'   // @ = the src/ folder
```

This alias must be registered in **two** places: `vite.config.ts` (for Vite) and `tsconfig` (for TypeScript).

🧩 Replace `vite.config.ts`:

```ts
import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    // "@/..." = the src/ folder, so imports don't need "../../../"
    alias: { '@': path.resolve(import.meta.dirname, './src') },
  },
})
```

🧩 Replace `tsconfig.json`:

```json
{
  "files": [],
  "references": [
    {
      "path": "./tsconfig.app.json"
    },
    {
      "path": "./tsconfig.node.json"
    }
  ],
  "compilerOptions": {
    "paths": {
      "@/*": [
        "./src/*"
      ]
    }
  }
}
```

🧩 Replace `tsconfig.app.json`:

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "es2023",
    "lib": [
      "ES2023",
      "DOM"
    ],
    "module": "esnext",
    "types": [
      "vite/client"
    ],
    "allowArbitraryExtensions": true,
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "paths": {
      "@/*": [
        "./src/*"
      ]
    }
  },
  "include": [
    "src"
  ]
}
```

🧩 Replace the contents of `src/index.css` with just one line (shadcn adds the rest later):

```css
@import "tailwindcss";
```

🧩 Install shadcn/ui:

```fish
npx shadcn@latest init -t vite -b radix -p nova

npx shadcn@latest add button card table badge alert
```

| Flag | Meaning |
|---|---|
| `-t vite` | the project is Vite |
| `-b radix` | components use Radix UI. **Required**, because `App.tsx` uses `<Button asChild>` (a Radix feature) |
| `-p nova` | look preset (Lucide icons, Geist font, **Neutral** base color). 🔄 shadcn 4 asks for a preset, not a base color |

`shadcn init` automatically:
- creates `components.json` + `src/lib/utils.ts` (the `cn()` function for merging Tailwind classes)
- adds theme colors to `src/index.css`
- installs `radix-ui`, `class-variance-authority`, `cn`, `lucide-react`, `tw-animate-css`, `@fontsource-variable/geist`

> 🔄 `cn` is shadcn's official package (repo `shadcn-ui/cn`), replacing `clsx` + `tailwind-merge` from older versions. The contents of `src/lib/utils.ts` become just `export { cn } from "cn"`.

`shadcn add` copies component code into `src/components/ui/`. The code is yours now, feel free to read & change it.

✅ **Check:** `ls src/components/ui` → you should see `alert.tsx badge.tsx button.tsx card.tsx table.tsx`.

---

## Step F2: API layer (`src/api/`)

🎯 **Goal:** everything about talking to the backend is collected in one folder.

💡 **Concept:** `types.ts` = the **twin of `custom_types.py`**. TypeScript will complain if you get a field name wrong. But this only works if the two files stay **the same**. Change one → change the other too.

🧩 Create `src/api/types.ts`:

```ts
// types.ts: the "twin" of custom_types.py in the backend
// if the data shape changes in the backend, change it here too

export type Cell = string | number | boolean | null

export interface ResultTable {
  id: string
  title: string
  columns: string[]
  rows: Cell[][]
  formulas: string[]
}

export interface CheckItem {
  instruction: string
  done: boolean
  note: string
}

export interface JobResult {
  instructions: { items: string[]; expected_tables: string[] }
  tables: ResultTable[]
  review: { items: CheckItem[] }
}

export interface JobStatus {
  status: 'running' | 'completed' | 'failed'
  result: JobResult | null
  error: string | null
}

export interface CreateJobResponse {
  job_id: string
  event_id: string
}
```

🧩 Create `src/api/client.ts`:

```ts
// client.ts: all calls to the backend are collected here
import type { CreateJobResponse, JobStatus } from './types'

// backend address comes from the frontend .env (VITE_API_URL), default localhost:8000
export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    // FastAPI sends errors as { detail: "..." }
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `Request failed (${res.status})`)
  }
  return res.json() as Promise<T>
}

export async function createJob(files: File[]): Promise<CreateJobResponse> {
  const form = new FormData()
  files.forEach((f) => form.append('files', f)) // field name "files" = the parameter in FastAPI
  const res = await fetch(`${API_URL}/api/jobs`, { method: 'POST', body: form })
  return handle<CreateJobResponse>(res)
}

export async function getJobStatus(eventId: string): Promise<JobStatus> {
  const res = await fetch(`${API_URL}/api/jobs/${eventId}`)
  return handle<JobStatus>(res)
}

export function exportUrl(eventId: string): string {
  return `${API_URL}/api/jobs/${eventId}/export`
}
```

🧩 Create `src/api/files.ts` (the file rules, same as in the backend, so the user is told earlier):

```ts
// files.ts: guess the file type from its extension (same as classify() in the backend)
export type FileKind = 'guide' | 'data'

const GUIDE_EXT = ['.pdf', '.png', '.jpg', '.jpeg', '.webp']
const DATA_EXT = ['.xlsx', '.csv']

export function fileKind(name: string): FileKind | null {
  const ext = name.slice(name.lastIndexOf('.')).toLowerCase()
  if (GUIDE_EXT.includes(ext)) return 'guide'
  if (DATA_EXT.includes(ext)) return 'data'
  return null
}

// return a message if the file combination is incomplete, null if it's fine
export function validateFiles(files: File[]): string | null {
  const guides = files.filter((f) => fileKind(f.name) === 'guide').length
  const datas = files.filter((f) => fileKind(f.name) === 'data').length
  if (guides === 0) return 'Add at least 1 guide file (PDF/image)'
  if (datas !== 1) return 'Need exactly 1 data file (.xlsx/.csv)'
  return null
}
```

---

## Step F3: `useJob` hook + `QueryClientProvider`

🎯 **Goal:** the "upload → watch status until finished" logic is separated from the UI.

💡 **Concept:**

```
useMutation  → for ACTIONS (uploading files, runs once)
useQuery     → for DATA    (job status); refetchInterval = ask again every 1.5 seconds
               stops automatically when the status is completed / failed
```

🧩 Create `src/hooks/useJob.ts`:

```ts
// useJob.ts: submit a job + watch its status until it finishes
import { useMutation, useQuery } from '@tanstack/react-query'
import { createJob, getJobStatus } from '@/api/client'

const POLL_MS = 1500 // check status every 1.5 seconds

export function useJob() {
  // useMutation = for actions that "change something" (uploading files)
  const upload = useMutation({ mutationFn: createJob })
  const eventId = upload.data?.event_id

  // useQuery = for "fetching data"; refetchInterval makes it keep asking again
  const status = useQuery({
    queryKey: ['job', eventId],
    queryFn: () => getJobStatus(eventId!),
    enabled: Boolean(eventId), // only runs after the upload succeeds
    refetchInterval: (query) => {
      const s = query.state.data?.status
      return s === 'completed' || s === 'failed' ? false : POLL_MS // stop once it's finished
    },
  })

  const isRunning =
    upload.isPending || (Boolean(eventId) && (!status.data || status.data.status === 'running'))

  return {
    start: upload.mutate,
    reset: upload.reset,
    eventId,
    isRunning,
    uploadError: upload.error,
    job: status.data,
    pollError: status.error,
  }
}
```

🧩 Replace `src/main.tsx`:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App.tsx'
import './index.css'

// QueryClient = the "brain" of TanStack Query: keeps the cache & manages refetching
const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
```

---

## Step F4: `FileDropzone.tsx`

🎯 **Goal:** the drag & drop area + list of chosen files, complete with `guide` / `data` labels.

🧩 Create `src/components/FileDropzone.tsx`:

```tsx
// FileDropzone.tsx: drag & drop area + list of the files already chosen
import { FileSpreadsheet, FileText, Upload, X } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { fileKind } from '@/api/files'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface Props {
  files: File[]
  onChange: (files: File[]) => void
  disabled?: boolean
}

export function FileDropzone({ files, onChange, disabled }: Props) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    disabled,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.webp'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'text/csv': ['.csv'],
    },
    // new files are added to the list (not replacing it)
    onDrop: (accepted) => onChange([...files, ...accepted]),
  })

  const remove = (index: number) => onChange(files.filter((_, i) => i !== index))

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={cn(
          'flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors',
          isDragActive ? 'border-primary bg-muted' : 'hover:bg-muted/50',
          disabled && 'cursor-not-allowed opacity-50',
        )}
      >
        <input {...getInputProps()} />
        <Upload className="size-8 text-muted-foreground" />
        <p className="font-medium">
          {isDragActive ? 'Drop files here…' : 'Drag & drop files, or click to choose'}
        </p>
        <p className="text-sm text-muted-foreground">
          Guide: PDF / image · Data: 1 .xlsx / .csv file
        </p>
      </div>

      {files.length > 0 && (
        <ul className="space-y-2">
          {files.map((file, i) => {
            const kind = fileKind(file.name)
            const Icon = kind === 'data' ? FileSpreadsheet : FileText
            return (
              <li key={`${file.name}-${i}`} className="flex items-center gap-3 rounded-md border px-3 py-2">
                <Icon className="size-4 shrink-0 text-muted-foreground" />
                <span className="flex-1 truncate text-sm">{file.name}</span>
                <Badge variant={kind === 'data' ? 'default' : 'secondary'}>{kind ?? '?'}</Badge>
                <Button variant="ghost" size="icon" onClick={() => remove(i)} disabled={disabled}
                        aria-label={`Remove ${file.name}`}>
                  <X />
                </Button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
```

---

## Step F5: `ResultTable.tsx`, the result table (TanStack Table v9)

🎯 **Goal:** show one sortable result table, plus the list of formulas below it.

💡 **Concept 1:** data from the backend is an **array per row** (`[1, 0.3, 1.102, 9.753]`), so the `i`-th column is read with `row[i]`.

💡 **Concept 2: TanStack Table v9.** Features are registered first through `tableFeatures(...)`. Here it's only sorting. `features` and `helper` are kept **outside the component** so they aren't recreated on every render.

> ⚠️ If you find a tutorial that uses `useReactTable` / `getCoreRowModel`, that's the (old) **v8** API. In v9 use `useTable` + `tableFeatures`.

🧩 Create `src/components/ResultTable.tsx`:

```tsx
// ResultTable.tsx: shows ONE result table, sortable by clicking a column header
import { useMemo } from 'react'
import {
  createColumnHelper,
  createSortedRowModel,
  rowSortingFeature,
  sortFn_alphanumeric,
  sortFn_basic,
  tableFeatures,
  useTable,
} from '@tanstack/react-table'
import { ArrowUpDown } from 'lucide-react'
import type { Cell, ResultTable as ResultTableData } from '@/api/types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

type Row = Cell[]

// table features in use: only sorting. Kept outside the component so it isn't recreated on every render
const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns: { alphanumeric: sortFn_alphanumeric, basic: sortFn_basic },
})
const helper = createColumnHelper<typeof features, Row>()

export function ResultTable({ table }: { table: ResultTableData }) {
  // data from the backend is an array per row, so the i-th column is read with row[i]
  const columns = useMemo(
    () =>
      helper.columns(
        table.columns.map((name, i) => helper.accessor((row) => row[i], { id: String(i), header: name })),
      ),
    [table.columns],
  )

  const instance = useTable({ features, columns, data: table.rows })

  return (
    <Card>
      <CardHeader>
        <CardTitle>{table.title}</CardTitle>
        <CardDescription>{table.rows.length} {table.rows.length === 1 ? 'row' : 'rows'}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Table>
          <TableHeader>
            {instance.getHeaderGroups().map((group) => (
              <TableRow key={group.id}>
                {group.headers.map((header) => (
                  <TableHead key={header.id}>
                    <button
                      className="inline-flex items-center gap-1 hover:text-foreground"
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <instance.FlexRender header={header} />
                      <ArrowUpDown className="size-3" />
                    </button>
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {instance.getRowModel().rows.map((row) => (
              <TableRow key={row.id}>
                {row.getAllCells().map((cell) => (
                  <TableCell key={cell.id} className="tabular-nums">
                    {String(cell.getValue() ?? '')}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>

        {/* formulas used: so the user can check the LLM didn't misread the guide */}
        <div className="rounded-md bg-muted p-3">
          <p className="mb-1 text-xs font-medium text-muted-foreground">Steps & formulas</p>
          <ul className="space-y-1 font-mono text-xs">
            {table.formulas.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
```

---

## Step F6: `ReviewList.tsx`

🎯 **Goal:** show the `review` step result: each instruction ✅ or ❌.

🧩 Create `src/components/ReviewList.tsx`:

```tsx
// ReviewList.tsx: result of the "review" step, whether each instruction was followed or not
import { CircleCheck, CircleX } from 'lucide-react'
import type { CheckItem } from '@/api/types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function ReviewList({ items }: { items: CheckItem[] }) {
  const done = items.filter((i) => i.done).length
  return (
    <Card>
      <CardHeader>
        <CardTitle>Instruction check</CardTitle>
        <CardDescription>
          {done}/{items.length} instructions followed
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {items.map((item, i) => (
            <li key={i} className="flex gap-3">
              {item.done ? (
                <CircleCheck className="size-5 shrink-0 text-green-600" />
              ) : (
                <CircleX className="size-5 shrink-0 text-destructive" />
              )}
              <div>
                <p className="text-sm">{item.instruction}</p>
                <p className="text-xs text-muted-foreground">{item.note}</p>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}
```

---

## Step F7: `App.tsx`, the main page

🎯 **Goal:** put everything together: upload → **Enter** → loading → tables + instruction check + Excel download.

💡 **Concept:** the Enter key is attached to `window` through `useEffect`, so it can be pressed anywhere (unless typing in an input).

🧩 Replace `src/App.tsx`:

```tsx
// App.tsx: main page: upload -> Enter -> wait -> result tables
import { useEffect, useState } from 'react'
import { Download, Loader2, RotateCcw } from 'lucide-react'
import { exportUrl } from '@/api/client'
import { validateFiles } from '@/api/files'
import { FileDropzone } from '@/components/FileDropzone'
import { ResultTable } from '@/components/ResultTable'
import { ReviewList } from '@/components/ReviewList'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useJob } from '@/hooks/useJob'

export default function App() {
  const [files, setFiles] = useState<File[]>([])
  const { start, reset, eventId, isRunning, uploadError, job, pollError } = useJob()

  const problem = validateFiles(files)
  const canSubmit = !problem && !isRunning
  const submit = () => canSubmit && start(files)

  // pressing Enter anywhere = process (unless typing in an input)
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const typing = e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement
      if (e.key === 'Enter' && !typing) submit()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  const startOver = () => {
    setFiles([])
    reset()
  }

  const error = uploadError?.message ?? pollError?.message ?? (job?.status === 'failed' ? job.error : null)
  const result = job?.status === 'completed' ? job.result : null

  return (
    <main className="mx-auto max-w-4xl space-y-6 px-4 py-10">
      <header>
        <h1 className="text-2xl font-bold">Data Process Agent</h1>
        <p className="text-muted-foreground">
          Add a guide + raw data, press <kbd className="rounded border px-1 text-xs">Enter</kbd>,
          and get tables in the format the guide asks for.
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>1 · Files</CardTitle>
          <CardDescription>{problem ?? 'Ready to process'}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FileDropzone files={files} onChange={setFiles} disabled={isRunning} />
          <div className="flex gap-2">
            <Button onClick={submit} disabled={!canSubmit}>
              {isRunning && <Loader2 className="animate-spin" />}
              {isRunning ? 'Processing…' : 'Process (Enter)'}
            </Button>
            {(eventId || files.length > 0) && !isRunning && (
              <Button variant="outline" onClick={startOver}>
                <RotateCcw /> Start over
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>Failed</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {result && eventId && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">2 · Results ({result.tables.length} {result.tables.length === 1 ? 'table' : 'tables'})</h2>
            <Button variant="outline" asChild>
              <a href={exportUrl(eventId)}>
                <Download /> Download Excel
              </a>
            </Button>
          </div>
          {result.tables.map((t) => (
            <ResultTable key={t.id} table={t} />
          ))}
          <ReviewList items={result.review.items} />
        </section>
      )}
    </main>
  )
}
```

✅ **Check:**

```fish
npm run build      # must say "✓ built", with no TypeScript errors
npm run lint
```

The `only-export-components` warnings from `badge.tsx` / `button.tsx` are normal (shadcn's built-in files), you can ignore them.

---

## Step F8: Run everything 🎉

Open **3 terminals**:

| Terminal | Folder | Command |
|---|---|---|
| 1 | `backend/` | `uv run uvicorn data_agent.main:app --reload --port 8000` |
| 2 | `backend/` | `npx --allow-scripts=inngest-cli inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery` |
| 3 | `frontend/` | `npm run dev` |

✅ **Check:**
1. Open http://localhost:5173
2. Drag `backend/samples/pendulum/guide.pdf` + `data.xlsx`
3. Press **Enter**
4. Wait → **2 tables** + formulas + instruction check appear
5. Click a column header → the table gets sorted
6. Click **Download Excel** → you get an `.xlsx` file with 2 sheets
7. Open http://localhost:8288 → see the run in the Inngest dashboard

Commit:

```fish
cd ..; git add frontend; git commit -m "frontend: upload, polling, result tables"
```

**The app is done.** 🚀

---

# G. Maintenance

## G1. Everyday commands

| What you want to do | Command (folder) |
|---|---|
| Run the app | 3 terminals in [F8](#step-f8-run-everything-) |
| Run all tests | `uv run pytest` (backend) |
| Model/prompt quality report | `uv run data-agent-eval` (backend) |
| Process files from the terminal | `uv run data-agent guide.pdf data.xlsx` (backend) |
| Check the frontend | `npm run build && npm run lint` (frontend) |
| Reinstall all packages | `uv sync` (backend) / `npm ci` (frontend) |

## G2. Golden rules

1. **Every time you change backend code** → `uv run pytest` must stay green
2. **Every time you change a prompt / switch model** → `uv run data-agent-eval` must still pass
3. **Every time you change `custom_types.py`** → change `frontend/src/api/types.ts` too
4. **Every time you add/change an op** → change `OPS_REFERENCE` in `prompts.py` too
5. **`uv.lock` and `package-lock.json` are always committed**, `.env` never

## G3. Switching models

Just edit `backend/.env`, then restart uvicorn:

```bash
LLM_MODEL=qwen3-vl:2b-instruct      # 🔄 the one in use now (CPU-only laptop)
# LLM_MODEL=qwen3-vl:4b-instruct    # smarter, ~2x slower
# LLM_MODEL=glm-5.3-flash:cloud     # Ollama cloud (needs `ollama signin` + credit first)
```

After switching, **always** run `uv run data-agent-eval` to compare the results.

> Cloud models: the guide & data are sent to Ollama's servers (mostly in the US). Ollama says prompts aren't logged & aren't used for training, but still: the data is no longer only on your laptop.

## G4. How to add a new op

Example: a `percent` op (each row's percentage of the column total).

| # | File | What to add |
|---|---|---|
| 1 | `custom_types.py` | `'percent'` to `OpName` (+ a new field in `Step` if needed) |
| 2 | `operations.py` | the function `op_percent(df, step)` |
| 3 | `operations.py` | register it in `OPERATIONS` |
| 4 | `operations.py` | a new case in `describe_step` |
| 5 | `prompts.py` | a new line in `OPS_REFERENCE` |
| 6 | `tests/test_operations.py` | a test for the new op |

```python
def op_percent(df: pd.DataFrame, step: Step) -> pd.DataFrame:
    # new column = value / column total * 100
    _need(step, 'new_column', 'columns')
    _check_columns(df, step.columns)
    col = step.columns[0]
    df = df.copy()
    df[step.new_column] = df[col] / df[col].sum() * 100
    return df
```

## G5. How to add a new sample

```
samples/
└─ sample_name/
   ├─ guide.pdf        (or .png/.jpg)
   ├─ data.xlsx        (or .csv)
   └─ expected.json    {"tables": [{"title": "...", "columns": [...], "rows": [[...]]}]}
```

`expected.json` is calculated **manually** (Excel / a calculator / your own script), don't use the app's output, or its mistakes get saved too. The more varied samples you have (filter, group, regression, guide photo), the more the model/prompt weaknesses show.

## G6. Updating dependencies

```fish
# backend
uv lock --upgrade          # bump all versions in uv.lock
uv sync
uv run pytest && uv run data-agent-eval

# frontend
npm outdated               # see what can be updated
npm update
npm run build
```

Update **one at a time** for major versions (e.g. pandas 3 → 4), then run the tests each time. If something breaks, `git checkout uv.lock` to go back.

## G7. Reading logs & monitoring tokens

Each LLM call writes one log line:

```
INFO data_agent.llm: [plan#1] model=qwen3-vl:8b input=2150 output=430 time=14.2s speed=30.3 tok/s
```

- `plan#2`, `plan#3` appearing = the first plan failed and was fixed. If this happens often, the prompt or model needs improving
- `input` close to `LLM_NUM_CTX` = the guide is too long, part of it may get cut off. Raise `LLM_NUM_CTX` or split the guide
- the full error of each step is visible in the Inngest dashboard (http://localhost:8288)

## G8. README.md for the repo

Create `DATA-PROCESSOR/README.md`:

````markdown
# Data Process Agent

Upload a guide (PDF/image) + raw data (Excel/CSV) → tables that follow the guide.
A local LLM (Ollama) makes the plan, pandas does the calculating.

## Run
1. `ollama pull qwen3-vl:8b`
2. backend: `cp .env.example .env && uv sync`
3. 3 terminals:
   - `cd backend && uv run uvicorn data_agent.main:app --reload --port 8000`
   - `cd backend && npx --allow-scripts=inngest-cli inngest-cli@latest dev -u http://127.0.0.1:8000/api/inngest --no-discovery`
   - `cd frontend && npm ci && npm run dev`
4. open http://localhost:5173

## Check quality
- `cd backend && uv run pytest`
- `cd backend && uv run data-agent-eval`

Full details: GUIDE.md
````

---

# 🆘 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: 'LLM_MODEL'` | `.env` not found | run commands from the `backend/` folder, check the contents of `.env` |
| `ConnectionError: Failed to connect to Ollama` | the Ollama server is down | `sudo systemctl start ollama` |
| `Server disconnected without sending a response` | 🔄 Ollama was killed by the kernel because RAM ran out (check: `journalctl -u ollama` → `oom-kill`) | use a smaller model, or lower `LLM_NUM_CTX` (e.g. 8192) |
| `model "qwen3-vl:8b" not found` | not downloaded yet | `ollama pull <model name>` |
| `ModuleNotFoundError` | packages not installed yet | `uv sync` |
| model is extremely slow | running on CPU / thinking mode | check `ollama ps`; set `LLM_THINK=false`; use a smaller `-instruct` version; or Ollama cloud |
| `out of memory` / CUDA error | context too large | `LLM_NUM_CTX=8192` in `.env` |
| the warning "output does not match schema" keeps appearing | the model struggles to follow the JSON | check Step 5; try another model; simplify the guide |
| `plan still failed after 3 attempts` | the LLM can't find the right column/formula | look at the error message in the log; check the column names in Excel; add examples to `OPS_REFERENCE` |
| result numbers differ from what's expected | the LLM misread a formula | look at "Steps & formulas" in the UI; guides whose formulas are plain text (not images) are safer |
| frontend: `Failed to fetch` | backend is down / CORS | check terminal 1; `FRONTEND_ORIGIN` in `backend/.env` must be `http://localhost:5173` |
| status stays `running` | the Inngest dev server is down / not connected | check terminal 2; open http://localhost:8288 → Apps → `data-process-agent` should be there |
| `Inngest CLI binary not found` | 🔄 npm 12 skips install scripts | use `npx --allow-scripts=inngest-cli ...`. If it still fails: delete the folder in `~/.npm/_npx/` that contains `node_modules/inngest-cli`, then run again |
| `shadcn init` keeps asking for a preset | 🔄 shadcn 4 | use `npx shadcn@latest init -t vite -b radix -p nova` |
| `Cannot find module '@/...'` | alias not configured | check `vite.config.ts` + `tsconfig.json` + `tsconfig.app.json` (Step F1) |
| `useReactTable is not exported` | using a TanStack Table v8 example | use the v9 API (`useTable`, `tableFeatures`), see F5 |

---

# H. Next steps

Do these **after** the app above runs stably and `data-agent-eval` passes.

## H1. Confirm the plan before calculating

Inngest can **pause** mid-process and wait for an event from the user (`ctx.step.wait_for_event`). The flow:

```
make_plan → [show the plan in the UI, user clicks "Approve"] → run_plan → review
```

Good for important experiment data: the user checks the formulas first before the result is used.

## H2. Template library (Qdrant)

Store guides that were processed before + their plans that were **proven correct**. When a new guide comes in, find a similar old guide, then give its plan to the LLM as an example.

```
new guide → embedding (qwen3-embedding:0.6b, dim 1024) → search Qdrant → the 2 most similar old plans
          → inserted into the make_plan prompt as examples → a more accurate new plan
```

What to add: `ollama pull qwen3-embedding:0.6b`, `uv add qdrant-client`, Qdrant via Docker, a `vector_db.py` file (you can copy `QdrantStorage` from RAG-PDF, change to `dim=1024`), and an `embed()` function in `llm.py`.

## H3. Job history

Right now job results only live in the Inngest dev server (gone if the dev server restarts). Next step: save the `JobResult` to a small database (SQLite) or a JSON file at `uploads/<job_id>/result.json`, plus a "history" page in the frontend.

## H4. Deploy

- Inngest: switch the dev server to Inngest Cloud (needs `INNGEST_EVENT_KEY` + `INNGEST_SIGNING_KEY`, and `is_production=True`)
- `jobs.py`: change how status is checked (the dev server's REST API differs from the cloud version)
- Frontend: `npm run build` → the `dist/` folder can be hosted anywhere; set `VITE_API_URL` to the backend address
- Model: a server with a GPU, or move to Ollama cloud through `.env`
