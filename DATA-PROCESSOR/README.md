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
