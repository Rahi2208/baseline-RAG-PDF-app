RAG-PDF 

In this repo, there are 3 programs that i have built applying Retrieval Augmented Generation(RAG) to tuning the base llm model. 

1. Initial Learning phase
   this is my study project on RAG based on video by . . . . .
   **Tools:** Python, Ollama (`llama3.2:1b` for answers, `nomic-embed-text` for embeddings), LangChain, ChromaDB, Unstructured (PDF loader)

2. RAG-PDF
   my second project, with the help of tools such as:
- Backend: Python (managed with uv), FastAPI, Inngest (background steps and run dashboard)
- Interface: Streamlit
- PDF reading and chunking: LlamaIndex
- Embeddings: fastembed (runs locally, no API key)
- Vector database: Qdrant (Docker)
- Answer model: `gpt-oss-20b` through the Groq API (OpenAI-compatible),

i created program to enables llm analyzed and answer question based on pdf given.
this project is inspired by . . . .

3. DATA-PROCESSOR
   in this project, i created a program that can turn data into specific table based on clue pdf given.
   **Tools:**
- Backend: Python (managed with uv), FastAPI, Inngest
- LLM: Ollama (local model)
- Data and PDF processing: pandas, openpyxl, PyMuPDF
- Frontend: React, Vite, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query and Table
