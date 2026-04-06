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
from sentence_transformers import SentenceTransformer

# --- SKILL: chunk_documents ---
def chunk_documents(docs_dir: str, max_tokens: int = 400) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split each into chunks of max_tokens, respecting sentence boundaries.
    Return list of: {doc_name, chunk_index, text}

    Failure mode to prevent:
    - Never split mid-sentence (chunk boundary failure)
    - Never exceed max_tokens per chunk
    """
    results = []
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(docs_dir, fname)
        text = open(path, encoding="utf-8").read()
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Chunk sentences
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
                "doc_name": fname,
                "chunk_index": i,
                "text": chunk,
                "id": f"{fname}::chunk_{i}" # adding id for ChromaDB
            })
    return results


# --- SKILL: retrieve_and_answer ---
def retrieve_and_answer(
    query: str,
    collection,          # ChromaDB collection
    embedder,            # SentenceTransformer model
    llm_call,            # callable: (prompt: str) -> str
    top_k: int = 3,
    threshold: float = 0.6,
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
    query_embedding = embedder.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    distance_threshold = (1.0 - threshold) * 2.0
    passing = [
        (doc, meta, dist)
        for doc, meta, dist in zip(docs, metadatas, distances)
        if dist <= distance_threshold
    ]

    cited_chunks = [
        {
            "doc_name": m["doc_name"],
            "chunk_index": m["chunk_index"],
            "score": round(1.0 - d / 2.0, 3)
        }
        for _, m, d in passing
    ]

    if not passing:
        sources_str = ", ".join(f"{m['doc_name']}::chunk_{m['chunk_index']}" for _, m, _ in zip(docs, metadatas, distances)) or "none"
        refusal = f"This question is not covered in the retrieved policy documents.\nRetrieved chunks: {sources_str}. Please contact the relevant department for guidance."
        return {"answer": refusal, "cited_chunks": cited_chunks, "refused": True}

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

    answer = llm_call(prompt) if llm_call else "No LLM configured."

    return {
        "answer": answer,
        "cited_chunks": cited_chunks,
        "refused": False
    }


# --- INDEX BUILDER ---
def build_index(docs_dir: str, db_path: str = "./chroma_db"):
    """
    Chunk all documents and store embeddings in ChromaDB.
    Called once before querying.
    """
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    chunks = chunk_documents(docs_dir)

    client = chromadb.PersistentClient(path=db_path)
    try:
        client.delete_collection("policy_docs")
    except Exception:
        pass
    collection = client.create_collection("policy_docs")

    print(f"Indexing {len(chunks)} chunks...")
    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [{"doc_name": c["doc_name"], "chunk_index": c["chunk_index"]} for c in chunks]
    embeddings = embedder.encode(texts, show_progress_bar=True).tolist()

    collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)


# --- NAIVE MODE (run this first to see failure modes) ---
def naive_query(query: str, docs_dir: str, llm_call):
    """
    Load all documents into context without retrieval.
    Run this BEFORE building your RAG pipeline to observe the failure modes.
    """
    texts = []
    for fname in sorted(os.listdir(docs_dir)):
        if fname.endswith(".txt"):
            path = os.path.join(docs_dir, fname)
            texts.append(open(path, encoding="utf-8").read())
            
    context = "\n\n".join(texts)
    prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
    return llm_call(prompt)


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
        if args.naive:
            # Import LLM adapter from uc-mcp
            sys.path.insert(0, "../uc-mcp")
            from llm_adapter import call_llm
            result = naive_query(args.query, args.docs_dir, call_llm)
            print(f"\nNaive answer:\n{result}")
        else:
            # Full RAG query
            sys.path.insert(0, "../uc-mcp")
            from llm_adapter import call_llm
            
            client = chromadb.PersistentClient(path=args.db_path)
            try:
                collection = client.get_collection("policy_docs")
            except Exception:
                print("Index not built. Run with --build-index first.")
                sys.exit(1)
                
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            result = retrieve_and_answer(args.query, collection, embedder, call_llm)
            print(f"\nAnswer:\n{result['answer']}")
            if result.get("cited_chunks"):
                print("\nSources:")
                for c in result["cited_chunks"]:
                    print(f"  [{c['doc_name']}, chunk {c['chunk_index']}] score={c['score']}")


if __name__ == "__main__":
    main()
