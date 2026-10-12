## 1. Ingest PDF Files
# 2. Extract Text from PDF Files and split into small chunks
# 3. Send the chunks to the embedding model
# 4. Save the embeddings to a vector database
# 5. Perform similarity search on the vector database to find similar documents
# 6. retrieve the similar documents and present them to the user
## run pip install -r requirements.txt to install the required packages

import ollama
from langchain_community.document_loaders import UnstructuredPDFLoader
from langchain_ollama import OllamaEmbeddings #wrapper
from langchain_ollama import ChatOllama
from langchain_text_splitters import RecursiveCharacterTextSplitter #text splittimg
from langchain_community.vectorstores import Chroma #vector stores with chromadb
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_classic.retrievers.multi_query import MultiQueryRetriever
import os 

MODEL_NAME = 'llama3.2:1b'
DOC_PATH = './BOI.pdf'
EMBEDDING_MODEL = 'nomic-embed-text' 
VECTOR_STORE_NAME = 'baseline-rag'


#data ingestion 
def read_pdf(doc_path):
    if os.path.exists(doc_path): 
        loader = UnstructuredPDFLoader(file_path = doc_path) 
        data = loader.load() 
        print('PDF loaded succesfully')
        return data
    else:
        print('Upload a PDF file')
        return None 
    
#turn data into chunks 
def split_documents(documents): 
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=300) 
    chunks = text_splitter.split_documents(documents)
    print('document has been split into chunks') 
    return chunks 

#create vector database
def create_vector_db(chunks): 
    ollama.pull(EMBEDDING_MODEL) 

    vector_db = Chroma.from_documents(
        documents=chunks, 
        embedding = OllamaEmbeddings(model=EMBEDDING_MODEL), 
        collection_name = VECTOR_STORE_NAME 
    )
    print('vector database has been created')
    return vector_db 

#retrieve 
def create_retriever(vector_db, llm): 
    QUERY_PROMPT = PromptTemplate(
    input_variables=["question"],
    template="""You are an AI language model assistant. Your task is to generate five
    different versions of the given user question to retrieve relevant documents from
    a vector database. By generating multiple perspectives on the user question, your
    goal is to help the user overcome some of the limitations of the distance-based
    similarity search. Provide these alternative questions separated by newlines.
    Original question: {question}""",
)
    retriever = MultiQueryRetriever.from_llm(
        vector_db.as_retriever(), llm, prompt=QUERY_PROMPT
    )
    print('retriever created') 
    return retriever

def create_chain(retriever, llm): 
    template = """ 
Answer the question only based on the following 
{context}
 
Question: {question}
"""

    prompt = ChatPromptTemplate.from_template(template) 
    chain = ( 
        {'context': retriever, "question": RunnablePassthrough()} 
        | prompt 
        | llm 
        | StrOutputParser() 
    )
    print('chain has been created') 
    return chain 

def main(): 
    data = read_pdf(DOC_PATH) 
    if data is None: 
        return 

    chunks = split_documents(data) 

    vector_db = create_vector_db(chunks) 

    llm = ChatOllama(model=MODEL_NAME) 

    retriever = create_retriever(vector_db, llm)

    chain = create_chain(retriever, llm)

    question = ""
    res = chain.invoke(input=question)
    print("response: ") 
    print(res) 

if __name__ == "__main__":
    main()

