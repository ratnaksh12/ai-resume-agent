# services/vector_store.py

import os
from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# persistent directory for Chroma
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "..", "chroma_store")

# simple, fast local embedding model
_embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _collection_name(resume_id: int, version_id: int) -> str:
    return f"resume_{resume_id}_v{version_id}"


def index_resume(resume_id: int, version_id: int, raw_text: str) -> None:
    """
    Chunk the resume text and store embeddings in Chroma.
    Called right after we create a new resume version.
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=80)
    docs = splitter.create_documents([raw_text])

    Chroma.from_documents(
        docs,
        _embeddings,
        collection_name=_collection_name(resume_id, version_id),
        persist_directory=CHROMA_DIR,
    ).persist()


def query_resume(resume_id: int, version_id: int, query: str, k: int = 5) -> List[str]:
    """
    Retrieve the top-k most relevant chunks from this resume version.
    """
    vs = Chroma(
        collection_name=_collection_name(resume_id, version_id),
        embedding_function=_embeddings,
        persist_directory=CHROMA_DIR,
    )
    results = vs.similarity_search(query, k=k)
    return [d.page_content for d in results]
