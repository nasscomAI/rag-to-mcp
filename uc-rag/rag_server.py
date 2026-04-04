"""
UC-RAG — RAG Server
rag_server.py — Retrieval-Augmented Generation server for CMC policy documents.

Stack: sentence-transformers · ChromaDB · LLM via llm_adapter.py

Run:
  python3 rag_server.py --build-index
  python3 rag_server.py --query "Who approves leave without pay?"
  python3 rag_server.py --naive --query "Can I use my personal phone for work files?"
"""

import argparse
import os
import re
import sys

import chromadb
from sentence_transformers import SentenceTransformer

# ── CONFIG ───────────────────────────────────────────────────────────────────
DOCS_DIR   = os.path.join(os.path.dirname(__file__), "../data/policy-documents")
DB_PATH    = os.path.join(os.path.dirname(__file__), "./chroma_db")
COLLECTION = "policy_docs"
MODEL_NAME = "all-MiniLM-L6-v2"
MAX_TOKENS = 400
TOP_K      = 3
THRESHOLD  = 0.25  # calibrated for all-MiniLM-L6-v2 L2 distances on these docs

REFUSAL_TEMPLATE = (
    "This question is not covered in the retrieved policy documents. "
    "Retrieved chunks: {sources}. "
    "Please contact the relevant department for guidance."
)

# ── SINGLETON LOADERS ────────────────────────────────────────────────────────
_embedder = None
def get_embedder():
    global _embedder
    if _embedder is None:
        print("[rag_server] Loading embedder (first run only)...")
        _embedder = SentenceTransformer(MODEL_NAME)
    return _embedder

_client = None
_collection = None
def get_collection(db_path: str = DB_PATH):
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=db_path)
        try:
            _collection = _client.get_collection(COLLECTION)
        except Exception:
            _collection = None
    return _collection


# ── SKILL: chunk_documents ───────────────────────────────────────────────────
def _split_sentences(text: str) -> list[str]:
    """Split text on sentence boundaries (period/exclamation/question followed by whitespace)."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def chunk_documents(docs_dir: str = DOCS_DIR, max_tokens: int = MAX_TOKENS) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split each into chunks of max_tokens, respecting sentence boundaries.
    Return list of: {doc_name, chunk_index, text, id}
    """
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(f"Policy documents directory not found: {docs_dir}")

    results = []
    files = sorted(f for f in os.listdir(docs_dir) if f.endswith(".txt"))

    if not files:
        raise FileNotFoundError(f"No .txt files found in {docs_dir}")

    for fname in files:
        path = os.path.join(docs_dir, fname)
        try:
            text = open(path, encoding="utf-8").read()
        except Exception as e:
            print(f"[rag_server] WARNING: skipping {fname}: {e}")
            continue

        if not text.strip():
            print(f"[rag_server] WARNING: skipping {fname}: empty file")
            continue

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

        for i, chunk in enumerate(chunks):
            results.append({
                "doc_name":    fname,
                "chunk_index": i,
                "text":        chunk,
                "id":          f"{fname}::chunk_{i}",
            })

    return results


# ── INDEX BUILDER ────────────────────────────────────────────────────────────
def build_index(docs_dir: str = DOCS_DIR, db_path: str = DB_PATH):
    """Chunk all documents and store embeddings in ChromaDB."""
    global _client, _collection

    embedder = get_embedder()
    chunks = chunk_documents(docs_dir)

    _client = chromadb.PersistentClient(path=db_path)
    try:
        _client.delete_collection(COLLECTION)
    except Exception:
        pass
    _collection = _client.create_collection(COLLECTION)

    print(f"[rag_server] Indexing {len(chunks)} chunks from "
          f"{len(set(c['doc_name'] for c in chunks))} documents...")

    ids       = [c["id"]   for c in chunks]
    texts     = [c["text"] for c in chunks]
    metadatas = [{"doc_name": c["doc_name"], "chunk_index": c["chunk_index"]}
                 for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()

    _collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
    print(f"[rag_server] Index built at {db_path}")


# ── SKILL: retrieve_and_answer ───────────────────────────────────────────────
def retrieve_and_answer(
    query_text: str,
    llm_call=None,
    top_k: int = TOP_K,
    threshold: float = THRESHOLD,
    db_path: str = DB_PATH,
) -> dict:
    """
    Embed query, retrieve top_k chunks from ChromaDB, filter by threshold.
    If no chunks pass threshold, return refusal.
    Otherwise call LLM with retrieved chunks as context only.
    Return: {answer, cited_chunks, refused}
    """
    collection = get_collection(db_path)
    if collection is None:
        raise RuntimeError("Index not built. Run: python3 rag_server.py --build-index")

    embedder = get_embedder()
    query_embedding = embedder.encode([query_text]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs      = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # ChromaDB returns L2 distances. Convert to approximate cosine similarity.
    # Filter: keep chunks where similarity >= threshold
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

    # Refusal if nothing passes threshold
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

    # Build grounded prompt — retrieved context only
    context_blocks = "\n\n".join(
        f"[Source: {m['doc_name']}, chunk {m['chunk_index']}]\n{doc}"
        for doc, m, _ in passing
    )
    prompt = (
        f"Answer the following question using ONLY the provided context. "
        f"Do not use any information outside the context. "
        f"If the answer is not in the context, say so explicitly.\n\n"
        f"Context:\n{context_blocks}\n\n"
        f"Question: {query_text}\n\n"
        f"Answer (cite source document and chunk for each claim):"
    )

    if llm_call is None:
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


# ── PUBLIC QUERY INTERFACE (called by UC-MCP) ───────────────────────────────
def query(question: str, llm_call=None) -> dict:
    """Public interface for UC-MCP to call."""
    return retrieve_and_answer(question, llm_call=llm_call)


# ── NAIVE MODE ───────────────────────────────────────────────────────────────
def naive_query(query_text: str, docs_dir: str, llm_call):
    """
    Load all documents into context without retrieval.
    Demonstrates failure modes: cross-doc blending, hallucination, no citations.
    """
    all_text = ""
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(docs_dir, fname)
        all_text += f"\n\n--- {fname} ---\n\n" + open(path, encoding="utf-8").read()

    prompt = (
        f"Answer the following question based on the documents below.\n\n"
        f"{all_text}\n\n"
        f"Question: {query_text}\n\n"
        f"Answer:"
    )
    return llm_call(prompt)


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UC-RAG RAG Server")
    parser.add_argument("--build-index", action="store_true",
                        help="Build ChromaDB index from policy documents")
    parser.add_argument("--query", type=str,
                        help="Query the RAG server")
    parser.add_argument("--naive", action="store_true",
                        help="Run naive (no retrieval) mode to see failures")
    parser.add_argument("--docs-dir", type=str, default=DOCS_DIR,
                        help="Path to policy documents directory")
    parser.add_argument("--db-path", type=str, default=DB_PATH,
                        help="Path to ChromaDB storage directory")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    args = parser.parse_args()

    if not args.build_index and not args.query:
        parser.print_help()
        sys.exit(1)

    if args.build_index:
        print("Building index...")
        build_index(args.docs_dir, args.db_path)
        print("Index built. Run with --query to test.")

    if args.query:
        if args.naive:
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../uc-mcp"))
            from llm_adapter import call_llm
            result = naive_query(args.query, args.docs_dir, call_llm)
            print(f"\nNaive answer:\n{result}")
        else:
            # Try to load LLM adapter
            llm_call = None
            try:
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../uc-mcp"))
                from llm_adapter import call_llm
                llm_call = call_llm
            except Exception:
                print("[rag_server] No LLM adapter found — returning retrieved chunks only.")

            import json
            result = retrieve_and_answer(args.query, llm_call=llm_call, db_path=args.db_path)

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
