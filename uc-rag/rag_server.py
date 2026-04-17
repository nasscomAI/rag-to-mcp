"""
UC-RAG — RAG Server
rag_server.py — Starter file

Build this using your AI coding tool:
1. Share the contents of agents.md, skills.md, and uc-rag/README.md
2. Ask the AI to implement this file following the enforcement rules
   in agents.md and the skill definitions in skills.md
3. Run with: python3 rag_server.py --build-index
4. Then:      python3 rag_server.py --query "your question here"

Stack:
  pip3 install sentence-transformers chromadb
  LLM: set your API key in llm_adapter.py (../uc-mcp/llm_adapter.py)
       or set environment variable GEMINI_API_KEY
"""

import argparse
import os
import sys
import re
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# --- CONFIG ---
DOCS_DIR = os.path.join(os.path.dirname(__file__), "../data/policy-documents")
DB_PATH = os.path.join(os.path.dirname(__file__), "./chroma_db")
COLLECTION = "policy_docs"
MODEL_NAME = "all-MiniLM-L6-v2"
MAX_TOKENS = 400
TOP_K = 3
THRESHOLD = 0.3

REFUSAL_TEMPLATE = (
    "This question is not covered in the retrieved policy documents. "
    "Retrieved chunks: {sources}. "
    "Please contact the relevant department for guidance."
)

# --- EMBEDDER (loaded once) ---
_embedder = None

def get_embedder():
    global _embedder
    if _embedder is None:
        print("[rag_server] Loading embedder...")
        _embedder = SentenceTransformer(MODEL_NAME)
    return _embedder

# --- CHROMA CLIENT ---
_client = None
_collection = None

def get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=DB_PATH)
        try:
            _collection = _client.get_collection(COLLECTION)
        except Exception:
            _collection = None
    return _collection


# --- SKILL: chunk_documents ---
def chunk_documents(docs_dir: str, max_tokens: int = MAX_TOKENS) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split each into chunks of max_tokens, respecting sentence boundaries.
    Return list of: {doc_name, chunk_index, text}

    Failure mode to prevent:
    - Never split mid-sentence (chunk boundary failure)
    - Never exceed max_tokens per chunk
    """
    results = []
    
    # Split on sentence boundaries
    def split_sentences(text: str) -> list:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]
    
    # Chunk text by accumulating sentences
    def chunk_text(text: str) -> list:
        sentences = split_sentences(text)
        chunks, current, count = [], [], 0
        for sentence in sentences:
            words = len(sentence.split())
            if count + words > max_tokens and current:
                chunks.append(" ".join(current))
                current, count = [sentence], words
            else:
                current.append(sentence)
                count += words
        if current:
            chunks.append(" ".join(current))
        return chunks
    
    # Load all .txt files
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(docs_dir, fname)
        try:
            text = open(path, encoding="utf-8").read()
        except Exception as e:
            print(f"[rag_server] Warning: Could not read {fname}: {e}")
            continue
        
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            results.append({
                "doc_name": fname,
                "chunk_index": i,
                "text": chunk,
                "id": f"{fname}::chunk_{i}",
            })
    
    return results


# --- SKILL: retrieve_and_answer ---
def retrieve_and_answer(
    query: str,
    collection,
    embedder,
    llm_call=None,
    top_k: int = TOP_K,
    threshold: float = THRESHOLD,
) -> dict:
    """
    Embed query, retrieve top_k chunks from ChromaDB.
    Filter chunks below threshold.
    If no chunks pass threshold, return refusal template.
    Otherwise call llm with retrieved chunks as context only.
    Return: {answer, cited_chunks: [{doc_name, chunk_index, score}]}

    Failure modes to prevent:
    - Answer outside retrieved context
    - Cross-document blending
    - No citation
    """
    # Embed query
    query_embedding = embedder.encode([query]).tolist()
    
    # Retrieve from ChromaDB
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    
    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    
    # Filter by threshold (convert L2 distance to similarity)
    distance_threshold = (1.0 - threshold) * 2.0
    passing = [
        (doc, meta, dist)
        for doc, meta, dist in zip(docs, metadatas, distances)
        if dist <= distance_threshold
    ]
    
    # Build cited chunks
    cited_chunks = [
        {
            "doc_name": m["doc_name"],
            "chunk_index": m["chunk_index"],
            "score": round(1.0 - d / 2.0, 3),
            "text": doc[:200] + "..." if len(doc) > 200 else doc,
        }
        for doc, m, d in passing
    ]
    
    # If no chunks pass threshold, return refusal
    if not passing:
        sources = ", ".join(
            f"{m['doc_name']}::chunk_{m['chunk_index']}"
            for _, m, _ in zip(docs, metadatas, distances)
        ) or "none"
        return {
            "answer": REFUSAL_TEMPLATE.format(sources=sources),
            "cited_chunks": [],
            "refused": True,
        }
    
    # Build prompt with retrieved context only
    context_blocks = "\n\n".join(
        f"[Source: {m['doc_name']}, chunk {m['chunk_index']}]\n{doc}"
        for doc, m, _ in passing
    )
    prompt = (
        f"Answer the following question using ONLY the provided context. "
        f"Do not use any information outside the context. "
        f"If the answer is not in the context, say so explicitly.\n\n"
        f"Context:\n{context_blocks}\n\n"
        f"Question: {query}\n\n"
        f"Answer (cite source document and chunk for each claim):"
    )
    
    if llm_call is None:
        # Return retrieved chunks if no LLM configured
        answer = (
            "Retrieved context (no LLM configured):\n\n" +
            "\n\n---\n\n".join(
                f"[{m['doc_name']}, chunk {m['chunk_index']}]:\n{doc}"
                for doc, m, _ in passing
            )
        )
    else:
        answer = llm_call(prompt)
    
    return {
        "answer": answer,
        "cited_chunks": cited_chunks,
        "refused": False,
    }


# --- INDEX BUILDER ---
def build_index(docs_dir: str = DOCS_DIR, db_path: str = DB_PATH):
    """
    Chunk all documents and store embeddings in ChromaDB.
    Called once before querying.
    """
    global _client, _collection
    
    embedder = get_embedder()
    chunks = chunk_documents(docs_dir)
    
    _client = chromadb.PersistentClient(path=db_path)
    try:
        _client.delete_collection(COLLECTION)
    except Exception:
        pass
    _collection = _client.create_collection(COLLECTION)
    
    print(f"[rag_server] Indexing {len(chunks)} chunks...")
    
    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [{"doc_name": c["doc_name"], "chunk_index": c["chunk_index"]} for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()
    
    _collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
    print(f"[rag_server] Index built at {db_path}")


# --- CLI ---
def main():
    parser = argparse.ArgumentParser(description="UC-RAG RAG Server")
    parser.add_argument("--build-index", action="store_true", help="Build the ChromaDB index")
    parser.add_argument("--query", type=str, help="Query the RAG server")
    args = parser.parse_args()
    
    if args.build_index:
        build_index()
        print("Index built successfully!")
        return
    
    if args.query:
        collection = get_collection()
        if collection is None:
            print("Error: Index not built. Run with --build-index first.")
            return
        
        embedder = get_embedder()
        result = retrieve_and_answer(args.query, collection, embedder)
        print(f"\nAnswer: {result['answer']}")
        if result.get('cited_chunks'):
            print(f"\nCited chunks:")
            for chunk in result['cited_chunks']:
                print(f"  - {chunk['doc_name']}::chunk_{chunk['chunk_index']} (score: {chunk['score']})")
        return
    
    parser.print_help()


if __name__ == "__main__":
    main()


# --- NAIVE MODE (run this first to see failure modes) ---
def naive_query(query: str, docs_dir: str, llm_call):
    """
    Load all documents into context without retrieval.
    Run this BEFORE building your RAG pipeline to observe the failure modes.
    """
    raise NotImplementedError(
        "Implement naive_query using your AI tool.\n"
        "Hint: load all .txt files, concatenate, pass to LLM with query. "
        "No chunking, no retrieval, no enforcement."
    )


# --- MAIN ---
def main():
    parser = argparse.ArgumentParser(description="UC-RAG RAG Server")
    parser.add_argument("--build-index", action="store_true",
                        help="Build ChromaDB index from policy documents")
    parser.add_argument("--query", type=str,
                        help="Query the RAG server")
    parser.add_argument("--naive", action="store_true",
                        help="Run naive (no retrieval) mode to see failures")
    parser.add_argument("--docs-dir", type=str,
                        default="../data/policy-documents",
                        help="Path to policy documents directory")
    parser.add_argument("--db-path", type=str,
                        default="./chroma_db",
                        help="Path to ChromaDB storage directory")
    args = parser.parse_args()

    if not args.build_index and not args.query:
        parser.print_help()
        sys.exit(1)

    if args.build_index:
        print("Building index...")
        build_index(args.docs_dir, args.db_path)
        print("Index built. Run with --query to test.")

    if args.query:
        collection = get_collection()
        if collection is None:
            print("Error: Index not built. Run with --build-index first.")
            return
        
        embedder = get_embedder()
        result = retrieve_and_answer(args.query, collection, embedder)
        print(f"\nAnswer: {result['answer']}")
        if result.get('cited_chunks'):
            print(f"\nCited chunks:")
            for chunk in result['cited_chunks']:
                print(f"  - {chunk['doc_name']}::chunk_{chunk['chunk_index']} (score: {chunk['score']})")


if __name__ == "__main__":
    main()
