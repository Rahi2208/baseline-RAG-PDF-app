import logging 
from fastapi import FastAPI #so that out code can be reach by URL 
import inngest #inngest is for visualization and run code in background more secured 
import inngest.fast_api #connect inngest to fastapi 
from inngest.experimental import ai #memanggil ai dalam step inngest 
from dotenv import load_dotenv #membaca .env, api key in .env so that it is stay mysterious and canot be seen by other even when pushed to github, caused .env is inside .gitignore
import uuid #to crate unique id 
import os
import asyncio #to run blocking code (openai, qdrant) in a thread
from typing import Any
from ai_apps.data_loader import load_and_chunk_pdf, create_embeddings
from ai_apps.vector_db import QdrantStorage
from ai_apps.settings import llm_config
from ai_apps.custom_types import RAGChunkAndSrc, RAGUpsertResult, RAGSearchResult

load_dotenv() #load .env 
app = FastAPI() 

#client -> inngest -> server

#initialize inngest client 
inngest_client = inngest.Inngest(
    app_id='rag app', 
    logger= logging.getLogger('uvicorn'), 
    is_production=False, 
    serializer=inngest.PydanticSerializer()
)

#retrieval 
@inngest_client.create_function(
    fn_id = 'RAG: query pdf', 
    trigger = inngest.TriggerEvent(event = 'rag/query_pdf') 
)
async def rag_query_ai_pdf(ctx: inngest.Context): 
    # step handlers must be async; blocking calls (openai, qdrant) go to a thread so they don't block the event loop
    async def _search(question: str, top_k: int) -> RAGSearchResult:
        query_vec = (await asyncio.to_thread(create_embeddings, [question]))[0]
        found = await asyncio.to_thread(lambda: QdrantStorage().search(query_vec, top_k))
        return RAGSearchResult(contexts=found['context'], sources=found['sources'])

    question = str(ctx.event.data.get('question', ''))
    top_k = int(str(ctx.event.data.get('top_k', 8)))
    found = await ctx.step.run('embed_and_search', _search, question, top_k, output_type=RAGSearchResult)

    #prompt for user 
    contexts_block = "\n\n".join(f'-{c}' for c in found.contexts) 
    user_content =(
        'use the folowwing context to answer the question.\n\n'
        f'Context:\n{contexts_block}\n\n'
        f'Question: {question}\n' 
        'Answer concisely using the context above' 
    )

    #chat model (groq / openai) comes from .env, see settings.py
    try:
        cfg = llm_config()
    except ValueError as e:
        raise inngest.NonRetriableError(str(e))  #retrying will not fix a missing key
    adapter = ai.openai.Adapter(auth_key=cfg['auth_key'], base_url=cfg['base_url'], model=cfg['model'])

    #call LLM model and give answer 
    res: Any = await ctx.step.ai.infer(
        'llm-answer', 
        adapter = adapter ,
        body= { 
            'max_tokens': 2048, #reasoning models (gpt-oss) spend part of this budget on thinking 
            'temperature': 0.1, 
            'messages': [
                {'role':'system', 'content': 'answer only using the provided context. '}, 
                {'role': 'user', 'content': user_content} 
            ]
        }
    )
    
    answer = (res["choices"][0]['message'].get('content') or '').strip() or '(the model returned an empty answer)'
    return {'answer': answer, 'sources': found.sources, 'num_context': len(found.contexts)} 

# load pdf, chunking, embed, store in db  
@inngest_client.create_function(
    fn_id='RAG: ingest pdf', 
    trigger = inngest.TriggerEvent(event='rag/ingest_pdf')
)
async def rag_ingest_pdf(ctx: inngest.Context): 
    async def _load(pdf_path: str, source_id: str) -> RAGChunkAndSrc:
        chunks, pages = await asyncio.to_thread(load_and_chunk_pdf, pdf_path)
        return RAGChunkAndSrc(chunks=chunks, pages=pages, source_id=source_id)

    async def _upsert(chunk_and_src: RAGChunkAndSrc) -> RAGUpsertResult:
        chunks = chunk_and_src.chunks
        source_id = chunk_and_src.source_id
        vecs = await asyncio.to_thread(create_embeddings, chunks)
        ids = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{source_id}:{i}")) for i in range(len(chunks))]
        pages = chunk_and_src.pages
        payloads = [{'source': source_id, 'page': pages[i] if i < len(pages) else None, 'text': chunks[i]} for i in range(len(chunks))]
        def _replace():
            store = QdrantStorage()
            store.delete_source(source_id) #drop old version of this pdf first
            store.upsert(ids, vecs, payloads)
        await asyncio.to_thread(_replace)
        return RAGUpsertResult(ingested=len(chunks))

    pdf_path = ctx.event.data.get('pdf_path')
    if not pdf_path:
        raise inngest.NonRetriableError('pdf_path is required in the event data')
    pdf_path = str(pdf_path)
    source_id = str(ctx.event.data.get('source_id') or pdf_path)

    chunk_and_src = await ctx.step.run('load_and_chunk_pdf', _load, pdf_path, source_id, output_type=RAGChunkAndSrc)
    ingested = await ctx.step.run('embed_and_upsert', _upsert, chunk_and_src, output_type=RAGUpsertResult)
    return ingested.model_dump()


"""
what inngest.Context return: 
class Context:
    event: Event #data event that trigger this function        
    run_id: str          
    attempt: int

ctx: inngest.Context, meaning that ctx shape is mimic class.Context

"""
# @ symbol is called decorator, decorator is always linked with the code directly below it 
#  
inngest.fast_api.serve(app, inngest_client, [rag_ingest_pdf, rag_query_ai_pdf]) 

#inngest.fast_api(app, client, [function])
