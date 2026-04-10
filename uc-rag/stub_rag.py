"""
UC-RAG — stub_rag.py
Fully working RAG implementation against the policy documents.

USE THIS IF:
- Your rag_server.py is not yet working
- You want to proceed to UC-MCP without finishing UC-RAG
- You want to compare your implementation against a reference

UC-MCP imports from this file by default.
To use your own rag_server.py in UC-MCP, update uc-mcp/mcp_server.py:
  change: from stub_rag import query as rag_query
  to:     from rag_server import query as rag_query   (once your server works)

Requirements:
  pip3 install sentence-transformers chromadb
"""

import os
import sys
import json
import argparse
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

# ── CONFIG ──────────────────────────────────────────────────────────────────
DOCS_DIR    = os.path.join(os.path.dirname(__file__), "../data/policy-documents")
DB_PATH     = os.path.join(os.path.dirname(__file__), "./stub_chroma_db")
COLLECTION  = "policy_docs"
MODEL_NAME  = "all-MiniLM-L6-v2"
MAX_TOKENS  = 400
TOP_K       = 3
THRESHOLD   = 0.35

REFUSAL_TEMPLATE = (
    "This question is not covered in the retrieved policy documents. "
    "Retrieved chunks: {sources}. "
    "Please contact the relevant department for guidance."
)

# ── EMBEDDER (loaded once) ───────────────────────────────────────────────────
_embedder = None
def get_embedder():
    global _embedder
    if _embedder is None:
        print("[stub_rag] Loading embedder (first run only)...")
        _embedder = SentenceTransformer(MODEL_NAME)
    return _embedder

# ── CHROMA CLIENT ────────────────────────────────────────────────────────────
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

# ── CHUNK DOCUMENTS ──────────────────────────────────────────────────────────
def _split_sentences(text: str) -> list[str]:
    """Split on sentence boundaries."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]

def _chunk_text(text: str, max_tokens: int = MAX_TOKENS) -> list[str]:
    """
    Accumulate sentences until max_tokens is reached.
    Respects sentence boundaries — never splits mid-sentence.
    """
    sentences = _split_sentences(text)
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

def chunk_documents(docs_dir: str = DOCS_DIR) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Return list of {doc_name, chunk_index, text}.
    """
    results = []
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(docs_dir, fname)
        text = open(path, encoding="utf-8").read()
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            results.append({
                "doc_name":    fname,
                "chunk_index": i,
                "text":        chunk,
                "id":          f"{fname}::chunk_{i}",
            })
    return results

# ── BUILD INDEX ──────────────────────────────────────────────────────────────
def build_index(docs_dir: str = DOCS_DIR, db_path: str = DB_PATH):
    """Embed all chunks and store in ChromaDB."""
    global _client, _collection
    embedder = get_embedder()
    chunks = chunk_documents(docs_dir)

    _client = chromadb.PersistentClient(path=db_path)
    try:
        _client.delete_collection(COLLECTION)
    except Exception:
        pass
    _collection = _client.create_collection(COLLECTION)

    print(f"[stub_rag] Indexing {len(chunks)} chunks from {len(set(c['doc_name'] for c in chunks))} documents...")
    ids        = [c["id"]       for c in chunks]
    texts      = [c["text"]     for c in chunks]
    metadatas  = [{"doc_name": c["doc_name"], "chunk_index": c["chunk_index"]} for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()

    _collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
    print(f"[stub_rag] Index built at {db_path}")

# ── RETRIEVE AND ANSWER ───────────────────────────────────────────────────────
def retrieve_and_answer(
    query: str,
    llm_call=None,
    top_k: int = TOP_K,
    threshold: float = THRESHOLD,
) -> dict:
    """
    Embed query, retrieve top_k chunks, filter by threshold.
    If no chunks pass — return refusal.
    Otherwise call LLM with retrieved context only.
    Returns {answer, cited_chunks}
    """
    collection = get_collection()
    if collection is None:
        raise RuntimeError(
            "Index not built. Run: python3 stub_rag.py --build-index"
        )

    embedder = get_embedder()
    query_embedding = embedder.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    
    # DEBUG: Print retrieval scores
    print(f"[DEBUG] Raw distances: {distances}")
    print(f"[DEBUG] Cosine similarities: {[round(1.0 - d/2.0, 3) for d in distances]}")

    # ChromaDB returns L2 distances — convert to cosine similarity approx
    # Lower distance = more similar. Filter: distance < (1 - threshold) * 2
    distance_threshold = (1.0 - threshold) * 2.0
    passing = [
        (doc, meta, dist)
        for doc, meta, dist in zip(docs, metadatas, distances)
        if dist <= distance_threshold
    ]

    cited_chunks = [
        {
            "doc_name":    m["doc_name"],
            "chunk_index": m["chunk_index"],
            "score":       round(1.0 - d / 2.0, 3),
            "text":        doc[:200] + "..." if len(doc) > 200 else doc,
        }
        for doc, m, d in passing
    ]

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

    # Build prompt — retrieved context only
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
        # Return retrieved chunks as answer if no LLM configured
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
        "answer":       answer,
        "cited_chunks": cited_chunks,
        "refused":      False,
    }

# ── PUBLIC QUERY INTERFACE (called by UC-MCP) ────────────────────────────────
def query(question: str, llm_call=None) -> dict:
    """
    Public interface for UC-MCP to call.
    Returns {answer, cited_chunks, refused}
    """
    return retrieve_and_answer(question, llm_call=llm_call)

# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UC-RAG Stub — Working Reference Implementation")
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--query",       type=str)
    parser.add_argument("--docs-dir",    type=str, default=DOCS_DIR)
    parser.add_argument("--json",        action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.build_index:
        build_index(args.docs_dir)

    if args.query:
        # Try to load LLM adapter from uc-mcp
        llm_call = None
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../uc-mcp"))
            from llm_adapter import call_llm
            llm_call = call_llm
        except Exception:
            print("[stub_rag] No LLM adapter found — returning retrieved chunks only.")

        result = query(args.query, llm_call=llm_call)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\nAnswer:\n{result['answer']}")
            if result["cited_chunks"]:
                print(f"\nSources:")
                for c in result["cited_chunks"]:
                    print(f"  [{c['doc_name']}, chunk {c['chunk_index']}] score={c['score']}")
            if result.get("refused"):
                print("\n[REFUSED — no chunks above threshold]")

if __name__ == "__main__":
    main()
