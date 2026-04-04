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

# --- CONFIGURATION (from agents.md / README) ---
MAX_TOKENS = 400
THRESHOLD = 0.6
TOP_K = 3
COLLECTION_NAME = "policy_docs"
MODEL_NAME = "all-MiniLM-L6-v2"

REFUSAL_TEMPLATE = (
    "This question is not covered in the retrieved policy documents. "
    "Retrieved chunks: {sources}. Please contact the relevant "
    "department for guidance."
)

# --- SKILL: chunk_documents ---
def chunk_documents(docs_dir: str, max_tokens: int = 400) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split each into chunks of max_tokens, respecting sentence boundaries.
    Return list of: {doc_name, chunk_index, text}

    Enforcement Rules:
    - Never split mid-sentence (Failure Mode 1)
    - Never exceed max_tokens (approx 400) per chunk
    - Use UTF-8 encoding to prevent Windows 'charmap' errors
    """
    results = []
    
    if not os.path.exists(docs_dir):
        print(f"Error: Directory '{docs_dir}' not found.")
        return []

    # Sort files to ensure deterministic indexing
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".txt"):
            continue
        
        path = os.path.join(docs_dir, fname)
        
        try:
            # FIX: Explicitly set encoding to utf-8 to handle special symbols
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except UnicodeDecodeError:
            print(f"Warning: Could not decode {fname} with UTF-8. Skipping.")
            continue

        # Split on sentence boundaries (., !, ?) followed by whitespace
        # This prevents splitting mid-sentence
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        chunks = []
        current_chunk_sentences = []
        current_token_count = 0

        for sentence in sentences:
            # Simple token estimation: 1 word approx 1.3 tokens, 
            # but word-count is a safe baseline for this requirement.
            sentence_word_count = len(sentence.split())
            
            # If adding this sentence hits the limit, save the current chunk
            if current_token_count + sentence_word_count > max_tokens and current_chunk_sentences:
                chunks.append(" ".join(current_chunk_sentences))
                current_chunk_sentences = [sentence]
                current_token_count = sentence_word_count
            else:
                current_chunk_sentences.append(sentence)
                current_token_count += sentence_word_count
        
        # Add the final remaining chunk for this document
        if current_chunk_sentences:
            chunks.append(" ".join(current_chunk_sentences))

        # Format into the dictionary structure required by skills.md
        for i, chunk_text in enumerate(chunks):
            results.append({
                "doc_name": fname,
                "chunk_index": i,
                "text": chunk_text.strip(),
                "id": f"{fname}::chunk_{i}" # Useful for ChromaDB unique IDs
            })
            
    return results


# --- SKILL: retrieve_and_answer ---
def retrieve_and_answer(
    query: str,
    collection,
    embedder,
    llm_call,
    top_k: int = TOP_K,
    threshold: float = THRESHOLD,
) -> dict:
    """
    Retrieves chunks and enforces grounding rules (Failure Mode 3).
    """
    query_embedding = embedder.encode([query]).tolist()
    
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    # Convert L2 distance to Cosine Similarity approx: 1 - (distance/2)
    passing_chunks = []
    for doc, meta, dist in zip(docs, metadatas, distances):
        score = 1.0 - (dist / 2.0)
        if score >= threshold:
            passing_chunks.append((doc, meta, score))

    if not passing_chunks:
        sources = [f"{m['doc_name']} (Index {m['chunk_index']})" for m in metadatas]
        return {
            "answer": REFUSAL_TEMPLATE.format(sources=", ".join(sources)),
            "cited_chunks": []
        }

    # Enforcement: Answer must use ONLY retrieved information
    context_text = "\n\n".join(
        f"SOURCE: {m['doc_name']}, CHUNK: {m['chunk_index']}\nCONTENT: {doc}"
        for doc, m, score in passing_chunks
    )

    prompt = (
        f"You are a policy assistant. Answer the question using ONLY the context below.\n"
        f"Rules:\n1. Cite the doc_name and chunk_index for every claim.\n"
        f"2. If the context doesn't contain the answer, use the refusal template.\n\n"
        f"Context:\n{context_text}\n\n"
        f"Question: {query}\n\n"
        f"Answer:"
    )

    answer = llm_call(prompt)
    
    return {
        "answer": answer,
        "cited_chunks": [
            {"doc_name": m["doc_name"], "chunk_index": m["chunk_index"], "score": round(s, 3)}
            for doc, m, s in passing_chunks
        ]
    }


# --- INDEX BUILDER ---
def build_index(docs_dir: str, db_path: str):
    client = chromadb.PersistentClient(path=db_path)
    
    # Reset collection if exists
    try: client.delete_collection(COLLECTION_NAME)
    except: pass
    
    collection = client.create_collection(COLLECTION_NAME)
    embedder = SentenceTransformer(MODEL_NAME)
    
    chunks = chunk_documents(docs_dir)
    
    if not chunks:
        print("No documents found to index.")
        return

    collection.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        metadatas=[{"doc_name": c["doc_name"], "chunk_index": c["chunk_index"]} for c in chunks],
        embeddings=embedder.encode([c["text"] for c in chunks]).tolist()
    )


# --- NAIVE MODE ---
def naive_query(query: str, docs_dir: str, llm_call):
    all_text = ""
    for fname in os.listdir(docs_dir):
        if fname.endswith(".txt"):
            # ADD encoding="utf-8" HERE
            with open(os.path.join(docs_dir, fname), "r", encoding="utf-8") as f:
                all_text += f"\nFile: {fname}\n{f.read()}\n"
    
    prompt = f"Answer this query based on these policies:\n{all_text}\n\nQuery: {query}"
    return llm_call(prompt)


# --- MAIN ---
def main():
    parser = argparse.ArgumentParser(description="UC-RAG RAG Server")
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--query", type=str)
    parser.add_argument("--naive", action="store_true")
    parser.add_argument("--docs-dir", type=str, default="../data/policy-documents")
    parser.add_argument("--db-path", type=str, default="./chroma_db")
    args = parser.parse_args()

    # Load LLM adapter
    sys.path.insert(0, "../uc-mcp")
    try:
        from llm_adapter import call_llm
    except ImportError:
        def call_llm(p): return "Error: llm_adapter.py not found."

    if args.build_index:
        build_index(args.docs_dir, args.db_path)
        print("Index built successfully.")

    if args.query:
        if args.naive:
            print(f"\n--- NAIVE ANSWER ---\n{naive_query(args.query, args.docs_dir, call_llm)}")
        else:
            client = chromadb.PersistentClient(path=args.db_path)
            collection = client.get_collection(COLLECTION_NAME)
            embedder = SentenceTransformer(MODEL_NAME)
            
            result = retrieve_and_answer(args.query, collection, embedder, call_llm)
            print(f"\n--- RAG ANSWER ---\n{result['answer']}")
            if result['cited_chunks']:
                print("\nCitations:")
                for c in result['cited_chunks']:
                    print(f"- {c['doc_name']} (Chunk {c['chunk_index']}) [Confidence: {c['score']}]")

if __name__ == "__main__":
    main()