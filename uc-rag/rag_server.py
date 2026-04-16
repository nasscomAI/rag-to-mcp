"""
UC-RAG — RAG Server
rag_server.py

Role    (agents.md): Retrieval-augmented policy assistant for CMC staff.
Intent  (agents.md): Answer grounded only in retrieved chunks + cite sources;
                     refuse with template when no chunk scores above 0.6.
Skills  (skills.md): chunk_documents, retrieve_and_answer

Run:
    python rag_server.py --build-index
    python rag_server.py --query "Who approves leave without pay?"
    python rag_server.py --naive --query "Can I use my personal phone for work files?"

Stack:
    pip install sentence-transformers chromadb
    Set GEMINI_API_KEY for LLM answers (optional — index/retrieval works without it).
"""

import argparse
import os
import re
import sys

# ---------------------------------------------------------------------------
# Token counting helper (whitespace approximation — no external dependency)
# ---------------------------------------------------------------------------

def _count_tokens(text: str) -> int:
    """Approximate token count by whitespace-split word count."""
    return len(text.split())


# ---------------------------------------------------------------------------
# SKILL: chunk_documents  (skills.md)
# ---------------------------------------------------------------------------

def chunk_documents(docs_dir: str, max_tokens: int = 400) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split each into sentence-boundary chunks of at most max_tokens.
    Return list of: {doc_name, chunk_index, text}

    Enforcement (agents.md):
    - Never split mid-sentence (chunk boundary failure mode #1)
    - Never exceed max_tokens per chunk
    """
    # Split text into sentences using punctuation boundaries
    _sentence_end = re.compile(r'(?<=[.!?])\s+')

    chunks = []
    try:
        files = sorted(f for f in os.listdir(docs_dir) if f.endswith(".txt"))
    except FileNotFoundError:
        print(f"[ERROR] Policy documents directory not found: {docs_dir}", file=sys.stderr)
        return chunks

    for doc_name in files:
        filepath = os.path.join(docs_dir, doc_name)
        try:
            with open(filepath, encoding="utf-8") as fh:
                text = fh.read()
        except Exception as exc:
            print(f"[SKIP] {doc_name} unreadable — {exc}", file=sys.stderr)
            continue

        sentences = _sentence_end.split(text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunk_index = 0
        current_sentences: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = _count_tokens(sentence)

            # Single sentence exceeds max_tokens — emit it alone
            if sentence_tokens > max_tokens:
                if current_sentences:
                    chunks.append({
                        "doc_name": doc_name,
                        "chunk_index": chunk_index,
                        "text": " ".join(current_sentences),
                    })
                    chunk_index += 1
                    current_sentences = []
                    current_tokens = 0
                chunks.append({
                    "doc_name": doc_name,
                    "chunk_index": chunk_index,
                    "text": sentence,
                })
                chunk_index += 1
                continue

            # Adding this sentence would exceed the limit — flush first
            if current_tokens + sentence_tokens > max_tokens and current_sentences:
                chunks.append({
                    "doc_name": doc_name,
                    "chunk_index": chunk_index,
                    "text": " ".join(current_sentences),
                })
                chunk_index += 1
                current_sentences = []
                current_tokens = 0

            current_sentences.append(sentence)
            current_tokens += sentence_tokens

        # Flush remaining sentences
        if current_sentences:
            chunks.append({
                "doc_name": doc_name,
                "chunk_index": chunk_index,
                "text": " ".join(current_sentences),
            })

        if not any(c["doc_name"] == doc_name for c in chunks):
            print(f"[WARN] {doc_name} produced zero chunks.", file=sys.stderr)

    return chunks


# ---------------------------------------------------------------------------
# SKILL: retrieve_and_answer  (skills.md)
# ---------------------------------------------------------------------------

REFUSAL_TEMPLATE = (
    "This question is not covered in the retrieved policy documents.\n"
    "Retrieved chunks: {chunk_sources}.\n"
    "Please contact the relevant department for guidance."
)

def retrieve_and_answer(
    query: str,
    collection,
    embedder,
    llm_call,
    top_k: int = 3,
    threshold: float = 0.3,
) -> dict:
    """
    Embed query → retrieve top_k chunks → filter below threshold →
    call LLM with retrieved chunks only → return answer + cited_chunks.

    Enforcement (agents.md):
    - Refusal template when no chunk scores above 0.6 (no LLM call)
    - Answer grounded in retrieved chunks only, never general knowledge
    - Every answer cites doc_name and chunk_index
    - Cross-document queries retrieved separately (ChromaDB handles per-chunk)
    """
    query_embedding = embedder.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # ChromaDB cosine distance = 1 - cosine_similarity → similarity = 1 - distance
    passing = []
    for doc_text, meta, dist in zip(documents, metadatas, distances):
        similarity = 1.0 - dist
        if similarity >= threshold:
            passing.append({
                "text": doc_text,
                "doc_name": meta["doc_name"],
                "chunk_index": meta["chunk_index"],
                "score": round(similarity, 4),
            })

    # All retrieved chunks are listed for the refusal template even if below threshold
    all_sources = ", ".join(
        f"{meta['doc_name']} chunk {meta['chunk_index']}"
        for meta in metadatas
    )

    if not passing:
        return {
            "answer": REFUSAL_TEMPLATE.format(chunk_sources=all_sources),
            "cited_chunks": [],
        }

    # Build context block from passing chunks only — never add outside knowledge
    context_parts = []
    cited_chunks = []
    for chunk in passing:
        context_parts.append(
            f"[Source: {chunk['doc_name']}, chunk {chunk['chunk_index']}]\n{chunk['text']}"
        )
        cited_chunks.append({
            "doc_name": chunk["doc_name"],
            "chunk_index": chunk["chunk_index"],
            "score": chunk["score"],
        })

    context_block = "\n\n".join(context_parts)

    prompt = (
        "You are a policy assistant for City Municipal Corporation staff.\n"
        "Answer the question using ONLY the policy excerpts provided below.\n"
        "For every fact you state, cite the source document name and chunk index "
        "in parentheses, e.g. (policy_hr_leave.txt, chunk 2).\n"
        "If the excerpts do not contain enough information to answer, say so explicitly "
        "and do NOT add information from general knowledge.\n\n"
        f"Policy excerpts:\n{context_block}\n\n"
        f"Question: {query}\n\n"
        "Answer (cite sources inline):"
    )

    answer = llm_call(prompt)

    return {
        "answer": answer,
        "cited_chunks": cited_chunks,
    }


# ---------------------------------------------------------------------------
# INDEX BUILDER
# ---------------------------------------------------------------------------

def build_index(docs_dir: str, db_path: str = "./chroma_db"):
    """Chunk all documents and store embeddings in ChromaDB."""
    try:
        from sentence_transformers import SentenceTransformer
        import chromadb
    except ImportError:
        print("[ERROR] Missing dependencies. Run: pip install sentence-transformers chromadb",
              file=sys.stderr)
        sys.exit(1)

    print("Loading sentence-transformers model (all-MiniLM-L6-v2)...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    print(f"Chunking documents from {docs_dir} ...")
    chunks = chunk_documents(docs_dir)
    if not chunks:
        print("[ERROR] No chunks produced. Check the docs directory.", file=sys.stderr)
        sys.exit(1)
    print(f"  {len(chunks)} chunks created across {len({c['doc_name'] for c in chunks})} documents.")

    print(f"Building ChromaDB index at {db_path} ...")
    client = chromadb.PersistentClient(path=db_path)
    # Reset collection so re-running --build-index is idempotent
    client.delete_collection("policy_docs") if "policy_docs" in [
        c.name for c in client.list_collections()
    ] else None
    collection = client.get_or_create_collection(
        name="policy_docs",
        metadata={"hnsw:space": "cosine"},
    )

    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()
    ids = [f"{c['doc_name']}__chunk_{c['chunk_index']}" for c in chunks]
    metadatas = [{"doc_name": c["doc_name"], "chunk_index": c["chunk_index"]} for c in chunks]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    print(f"Index built. {len(chunks)} chunks stored.")


# ---------------------------------------------------------------------------
# NAIVE MODE — demonstrates failure modes before RAG is applied
# ---------------------------------------------------------------------------

def naive_query(query: str, docs_dir: str, llm_call):
    """
    Load all documents into context with no retrieval.
    Demonstrates failure modes: context blending, hallucination, no citation.
    """
    all_text_parts = []
    try:
        for fname in sorted(os.listdir(docs_dir)):
            if fname.endswith(".txt"):
                fpath = os.path.join(docs_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as fh:
                        all_text_parts.append(f"--- {fname} ---\n{fh.read()}")
                except Exception as exc:
                    print(f"[SKIP] {fname}: {exc}", file=sys.stderr)
    except FileNotFoundError:
        return f"[ERROR] Docs directory not found: {docs_dir}"

    combined = "\n\n".join(all_text_parts)
    prompt = (
        f"You are a helpful assistant. Answer this question using the documents below.\n\n"
        f"{combined}\n\n"
        f"Question: {query}\nAnswer:"
    )
    return llm_call(prompt)


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

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
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../uc-mcp"))
        from llm_adapter import call_llm

        if args.naive:
            result = naive_query(args.query, args.docs_dir, call_llm)
            print(f"\nNaive answer:\n{result}")
        else:
            try:
                from sentence_transformers import SentenceTransformer
                import chromadb
            except ImportError:
                print("[ERROR] Run: pip install sentence-transformers chromadb", file=sys.stderr)
                sys.exit(1)

            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            client = chromadb.PersistentClient(path=args.db_path)
            try:
                collection = client.get_collection("policy_docs")
            except Exception:
                print("[ERROR] Index not found. Run --build-index first.", file=sys.stderr)
                sys.exit(1)

            result = retrieve_and_answer(args.query, collection, embedder, call_llm)

            print(f"\nAnswer:\n{result['answer']}")
            if result["cited_chunks"]:
                print("\nCited chunks:")
                for c in result["cited_chunks"]:
                    print(f"  {c['doc_name']}  chunk {c['chunk_index']}  (similarity {c['score']})")
            else:
                print("\n[No chunks passed the similarity threshold — refusal returned]")


# ---------------------------------------------------------------------------
# Public query() interface — called by mcp_server.py
# ---------------------------------------------------------------------------

_embedder = None
_collection = None

def query(question: str, llm_call=None, db_path: str = None) -> dict:
    """
    Public interface for UC-MCP to call.
    Loads embedder and ChromaDB collection on first call (cached).
    Returns {answer, cited_chunks, refused}
    """
    global _embedder, _collection

    from sentence_transformers import SentenceTransformer
    import chromadb

    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), "./chroma_db")

    if _embedder is None:
        print("[rag_server] Loading embedder (first call only)...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")

    if _collection is None:
        client = chromadb.PersistentClient(path=db_path)
        _collection = client.get_collection("policy_docs")

    if llm_call is None:
        def llm_call(prompt):
            return "[LLM not configured] Retrieved chunks only.\n" + prompt[:300]

    result = retrieve_and_answer(question, _collection, _embedder, llm_call)
    refused = not result["cited_chunks"]
    return {
        "answer": result["answer"],
        "cited_chunks": result["cited_chunks"],
        "refused": refused,
    }


if __name__ == "__main__":
    main()

