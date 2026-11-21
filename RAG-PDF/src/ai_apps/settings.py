#all model / provider choices live here, driven by .env (see .env.example)
import os
import re
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()

#embeddings: how text becomes numbers for the vector search
#  fastembed = runs on this laptop (free, no key) | openai = OpenAI api (needs OPENAI_API_KEY)
EMBED_BACKEND = os.getenv('EMBED_BACKEND', 'fastembed').strip().lower()
if EMBED_BACKEND not in ('fastembed', 'openai'):
    raise ValueError(f"EMBED_BACKEND must be 'fastembed' or 'openai', got {EMBED_BACKEND!r}")

_DEFAULT_EMBED_MODEL = {
    'fastembed': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',  #384 dim, ~0.22 GB, id + en
    'openai': 'text-embedding-3-large',
}
EMBED_MODEL = os.getenv('EMBED_MODEL') or _DEFAULT_EMBED_MODEL[EMBED_BACKEND]

_OPENAI_DIMS = {'text-embedding-3-large': 3072, 'text-embedding-3-small': 1536, 'text-embedding-ada-002': 1536}


@lru_cache(maxsize=1)
def embed_dim() -> int:
    if os.getenv('EMBED_DIM'):
        return int(os.environ['EMBED_DIM'])
    if EMBED_BACKEND == 'openai':
        if EMBED_MODEL in _OPENAI_DIMS:
            return _OPENAI_DIMS[EMBED_MODEL]
        raise ValueError(f'unknown openai embedding model {EMBED_MODEL!r}: set EMBED_DIM in .env')
    from fastembed import TextEmbedding
    for m in TextEmbedding.list_supported_models():
        if m['model'] == EMBED_MODEL:
            return int(m['dim'])
    raise ValueError(f'{EMBED_MODEL!r} is not a model fastembed supports (see TextEmbedding.list_supported_models())')


#chunk size (in tokens). an embedding model only "reads" its first N tokens of each chunk and ignores the rest,
#so chunks must fit inside that window or most of the text is never searchable.
#the two multilingual sentence-transformers models read only 128 tokens; bge reads 512; openai reads 8191.
_WINDOW_128 = {
    'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
    'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
}


def chunk_sizes() -> tuple[int, int]:
    #(chunk_size, chunk_overlap). tokens here are counted by llama-index (tiktoken), ~15-20% fewer than the
    #embedding model's own tokens, hence the margin below 128
    if EMBED_BACKEND == 'openai':
        default = (1000, 200)
    elif EMBED_MODEL in _WINDOW_128:
        default = (80, 15)
    else:
        default = (350, 70)
    return int(os.getenv('CHUNK_SIZE') or default[0]), int(os.getenv('CHUNK_OVERLAP') or default[1])


def collection_name() -> str:
    #one qdrant collection per embedding model: vectors from different models must never be mixed.
    #switching EMBED_MODEL therefore starts an empty collection (re-upload your pdfs) and keeps the old one intact.
    if (EMBED_BACKEND, EMBED_MODEL) == ('openai', 'text-embedding-3-large'):
        return 'docs'  #the name used before this setting existed, so old data keeps working
    return 'docs_' + re.sub(r'[^a-z0-9]+', '_', f'{EMBED_BACKEND}_{EMBED_MODEL}'.lower()).strip('_')


#chat model: writes the final answer from the retrieved chunks. all providers here speak the OpenAI api format
_PROVIDERS = {
    'groq': {'base_url': 'https://api.groq.com/openai/v1', 'key_env': 'GROQ_API_KEY', 'model': 'openai/gpt-oss-20b'},
    'openai': {'base_url': None, 'key_env': 'OPENAI_API_KEY', 'model': 'gpt-4o-mini'},
}


def llm_config() -> dict:
    #read at call time (not import time) so a missing key shows up as a clear error on the failed run
    provider = os.getenv('LLM_PROVIDER', 'groq').strip().lower()
    if provider not in _PROVIDERS:
        raise ValueError(f"LLM_PROVIDER must be one of {sorted(_PROVIDERS)}, got {provider!r}")
    p = _PROVIDERS[provider]
    key = os.getenv(p['key_env'])
    if not key:
        raise ValueError(f"{p['key_env']} is not set in .env (needed because LLM_PROVIDER={provider})")
    return {
        'auth_key': key,
        'model': os.getenv('LLM_MODEL') or p['model'],
        'base_url': os.getenv('LLM_BASE_URL') or p['base_url'] or os.getenv('OPENAI_BASE_URL') or None,
    }
