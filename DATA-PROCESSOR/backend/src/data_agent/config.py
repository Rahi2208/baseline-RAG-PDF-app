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
