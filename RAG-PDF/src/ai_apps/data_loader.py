import os
from functools import lru_cache
from pathlib import Path
from llama_index.readers.file import PDFReader 
from llama_index.core.node_parser import SentenceSplitter 
import re
from ai_apps.settings import EMBED_BACKEND, EMBED_MODEL, chunk_sizes


_size, _overlap = chunk_sizes()
splitter = SentenceSplitter(chunk_size=_size, chunk_overlap=_overlap)

def _clean(text: str) -> str:
    #pdf text is full of tabs / nbsp between words; make them plain spaces so chunks embed cleaner
    return re.sub(r'[ \t\u00a0]+', ' ', text).strip()

def load_and_chunk_pdf(path:str):
    #returns (chunks, pages): pages[i] is the pdf page number that chunks[i] came from
    docs = PDFReader().load_data(file=path)
    chunks, pages = [], []
    for d in docs:
        text = _clean(getattr(d, 'text', '') or '')
        if not text:
            continue
        page = str((d.metadata or {}).get('page_label', '?'))
        for c in splitter.split_text(text):
            chunks.append(c)
            pages.append(page)
    return chunks, pages

@lru_cache(maxsize=1)
def _fastembed_model():
    from fastembed import TextEmbedding
    #fastembed's default cache is the system temp dir, which gets wiped; keep the model in ~/.cache instead
    cache = os.getenv('FASTEMBED_CACHE') or str(Path.home() / '.cache' / 'fastembed')
    return TextEmbedding(model_name=EMBED_MODEL, cache_dir=cache)


@lru_cache(maxsize=1)
def _openai_client():
    from openai import OpenAI
    return OpenAI()


def create_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if EMBED_BACKEND == 'fastembed':
        return [v.tolist() for v in _fastembed_model().embed(texts)]
    response = _openai_client().embeddings.create(input=texts, model=EMBED_MODEL)
    return [item.embedding for item in response.data]
