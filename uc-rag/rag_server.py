"""
UC-RAG — RAG Server
rag_server.py — Full Implementation

Stack:
  pip3 install sentence-transformers chromadb
  LLM: set GEMINI_API_KEY environment variable
"""

import argparse
import os
import re
import sys

# ── SKILL: chunk_documents ────────────────────────────────────────────────────
def chunk_documents(docs_dir: str, max_tokens: int = 150) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split each into chunks of max_tokens, respecting paragraph/sentence boundaries.
    Return list of: {doc_name, chunk_index, text}

    Enforcement:
    - Never split mid-sentence
    - Never exceed max_tokens per chunk
    - Use paragraph/section boundary awareness for policy document format
    """
    if not os.path.exists(docs_dir):
        raise RuntimeError(f"Policy documents directory not found: {docs_dir}")

    def count_tokens(text: str) -> int:
        return len(text.split())

    def split_into_units(text: str) -> list[str]:
        """
        Split policy document text into fine-grained units:
        1. First split on blank lines and section dividers (═══)
        2. Then split each block further on numbered sub-clauses (e.g. 5.1, 5.2)
        This preserves semantic meaning without cutting mid-sentence.
        """
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # Split on blank lines or section dividers
        blocks = re.split(r'\n\s*\n|═+', text)
        result = []
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            # Further split on numbered sub-clauses (e.g. "5.1 ", "5.2 ")
            sub_blocks = re.split(r'(?m)(?=^\s*\d+\.\d+\s)', block)
            for sb in sub_blocks:
                sb = " ".join(sb.split())  # normalise whitespace
                if sb:
                    result.append(sb)
        return result

    chunks = []
    txt_files = [f for f in os.listdir(docs_dir) if f.endswith(".txt")]

    if not txt_files:
        print(f"[chunk_documents] WARNING: No .txt files found in {docs_dir}")

    for filename in sorted(txt_files):
        filepath = os.path.join(docs_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
        except (OSError, IOError) as e:
            print(f"[chunk_documents] WARNING: Could not read {filename}: {e}")
            continue

        units = split_into_units(text)
        current_chunk_parts = []
        current_tokens = 0
        chunk_index = 0

        for unit in units:
            unit_tokens = count_tokens(unit)

            # If a single unit exceeds max_tokens, split by sentences
            if unit_tokens > max_tokens:
                if current_chunk_parts:
                    chunks.append({
                        "doc_name": filename,
                        "chunk_index": chunk_index,
                        "text": " ".join(current_chunk_parts)
                    })
                    chunk_index += 1
                    current_chunk_parts = []
                    current_tokens = 0

                sentences = re.split(r'(?<=[.!?])\s+', unit.strip())
                sent_buffer = []
                sent_tokens = 0
                for sentence in sentences:
                    st = count_tokens(sentence)
                    if sent_tokens + st > max_tokens and sent_buffer:
                        chunks.append({
                            "doc_name": filename,
                            "chunk_index": chunk_index,
                            "text": " ".join(sent_buffer)
                        })
                        chunk_index += 1
                        sent_buffer = []
                        sent_tokens = 0
                    sent_buffer.append(sentence)
                    sent_tokens += st
                if sent_buffer:
                    chunks.append({
                        "doc_name": filename,
                        "chunk_index": chunk_index,
                        "text": " ".join(sent_buffer)
                    })
                    chunk_index += 1
                continue

            if current_tokens + unit_tokens > max_tokens and current_chunk_parts:
                chunks.append({
                    "doc_name": filename,
                    "chunk_index": chunk_index,
                    "text": " ".join(current_chunk_parts)
                })
                chunk_index += 1
                current_chunk_parts = []
                current_tokens = 0

            current_chunk_parts.append(unit)
            current_tokens += unit_tokens

        # Flush remaining
        if current_chunk_parts:
            chunks.append({
                "doc_name": filename,
                "chunk_index": chunk_index,
                "text": " ".join(current_chunk_parts)
            })

    print(f"[chunk_documents] Produced {len(chunks)} chunks from {len(txt_files)} documents.")
    return chunks


# ── SKILL: retrieve_and_answer ────────────────────────────────────────────────
def retrieve_and_answer(
    query: str,
    collection,          # ChromaDB collection
    embedder,            # SentenceTransformer model
    llm_call,            # callable: (prompt: str) -> str
    top_k: int = 3,
    threshold: float = 0.3,
) -> dict:
    """
    Embed query, retrieve top_k chunks from ChromaDB.
    Filter chunks below threshold.
    If no chunks pass threshold, return refusal template.
    Otherwise call llm with retrieved chunks as context only.
    Return: {answer, cited_chunks, refused}

    Enforcement:
    - Answer must use only retrieved chunks
    - No cross-document blending
    - Citation required
    - Refusal if no chunk above 0.6
    """
    query_embedding = embedder.encode([query], normalize_embeddings=True)[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    raw_docs = results["documents"][0]
    raw_metas = results["metadatas"][0]
    raw_distances = results["distances"][0]

    # ChromaDB returns L2 distances — convert to cosine-like similarity
    # For normalized embeddings, distance ≈ 2*(1 - cosine_sim)
    # So cosine_sim ≈ 1 - distance/2
    cited_chunks = []
    passing_chunks = []

    for doc_text, meta, dist in zip(raw_docs, raw_metas, raw_distances):
        score = 1.0 - dist / 2.0
        chunk_info = {
            "doc_name": meta.get("doc_name", "unknown"),
            "chunk_index": meta.get("chunk_index", 0),
            "score": round(score, 4)
        }
        cited_chunks.append(chunk_info)
        if score >= threshold:
            passing_chunks.append((doc_text, chunk_info))

    # Refusal template if nothing passes threshold
    if not passing_chunks:
        chunk_sources = [f"{c['doc_name']} chunk {c['chunk_index']}" for c in cited_chunks]
        refusal = (
            "This question is not covered in the retrieved policy documents. "
            f"Retrieved chunks: {chunk_sources}. "
            "Please contact the relevant department for guidance."
        )
        return {
            "answer": refusal,
            "cited_chunks": cited_chunks,
            "refused": True
        }

    # Build prompt — grounded only on retrieved chunks
    context_blocks = []
    for chunk_text, info in passing_chunks:
        context_blocks.append(
            f"[Source: {info['doc_name']}, Chunk {info['chunk_index']}]\n{chunk_text}"
        )
    context = "\n\n".join(context_blocks)

    prompt = (
        f"You are a policy assistant. Answer the question using ONLY the retrieved "
        f"policy document chunks below. Do not add any information not present in "
        f"these chunks. If the answer requires information from multiple documents, "
        f"cite each document separately — do not blend them.\n\n"
        f"Retrieved chunks:\n{context}\n\n"
        f"Question: {query}\n\n"
        f"Answer (cite source document name and chunk index for every claim):"
    )

    answer = llm_call(prompt)

    return {
        "answer": answer,
        "cited_chunks": [info for _, info in passing_chunks],
        "refused": False
    }


# ── INDEX BUILDER ─────────────────────────────────────────────────────────────
def build_index(docs_dir: str, db_path: str = "./chroma_db"):
    """
    Chunk all documents and store embeddings in ChromaDB.
    Called once before querying.
    """
    import chromadb
    from sentence_transformers import SentenceTransformer

    print(f"[build_index] Loading documents from: {docs_dir}")
    chunks = chunk_documents(docs_dir)

    print("[build_index] Loading sentence-transformers model...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    print("[build_index] Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=db_path)

    # Delete existing collection to rebuild fresh
    try:
        client.delete_collection("policy_docs")
    except Exception:
        pass

    collection = client.create_collection(
        name="policy_docs",
        metadata={"hnsw:space": "l2"}
    )

    print(f"[build_index] Embedding and indexing {len(chunks)} chunks...")
    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=True, normalize_embeddings=True).tolist()

    ids = [f"{c['doc_name']}__chunk_{c['chunk_index']}" for c in chunks]
    metadatas = [{"doc_name": c["doc_name"], "chunk_index": c["chunk_index"]} for c in chunks]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )
    print(f"[build_index] Index built at: {db_path}")


# ── NAIVE MODE ────────────────────────────────────────────────────────────────
def naive_query(query: str, docs_dir: str, llm_call):
    """
    Load all documents into context without retrieval.
    Run this BEFORE building your RAG pipeline to observe the failure modes.
    """
    if not os.path.exists(docs_dir):
        raise RuntimeError(f"Documents directory not found: {docs_dir}")

    all_text = []
    for filename in sorted(os.listdir(docs_dir)):
        if filename.endswith(".txt"):
            with open(os.path.join(docs_dir, filename), "r", encoding="utf-8") as f:
                all_text.append(f"=== {filename} ===\n{f.read()}")

    context = "\n\n".join(all_text)
    prompt = (
        f"You are a policy assistant. Answer this question using the policy documents below.\n\n"
        f"{context}\n\n"
        f"Question: {query}\nAnswer:"
    )
    return llm_call(prompt)


# ── PUBLIC query() FUNCTION (called by mcp_server) ───────────────────────────
def query(question: str, llm_call=None) -> dict:
    """
    Public interface called by mcp_server.py.
    Loads ChromaDB, embeds query, retrieves and answers.
    """
    import chromadb
    from sentence_transformers import SentenceTransformer

    if llm_call is None:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../uc-mcp"))
        from llm_adapter import call_llm
        llm_call = call_llm

    db_path = os.path.join(os.path.dirname(__file__), "./chroma_db")
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_collection("policy_docs")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")

    return retrieve_and_answer(question, collection, embedder, llm_call)


# ── MAIN ──────────────────────────────────────────────────────────────────────
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
            import chromadb
            from sentence_transformers import SentenceTransformer

            client = chromadb.PersistentClient(path=args.db_path)
            try:
                collection = client.get_collection("policy_docs")
            except Exception:
                print("[ERROR] Index not found. Run --build-index first.")
                sys.exit(1)

            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            result = retrieve_and_answer(args.query, collection, embedder, call_llm)

            print(f"\nAnswer:\n{result['answer']}")
            print(f"\nCited chunks:")
            for c in result["cited_chunks"]:
                print(f"  - {c['doc_name']} chunk {c['chunk_index']} (score: {c['score']})")
            if result["refused"]:
                print("\n[REFUSED — no chunk above threshold]")


if __name__ == "__main__":
    main()
