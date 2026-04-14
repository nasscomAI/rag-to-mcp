"""
UC-RAG — RAG Server
rag_server.py — Completed file
"""

import argparse
import os
import sys
import re
import json
from sentence_transformers import SentenceTransformer
import chromadb

# --- SKILL: chunk_documents ---
def chunk_documents(docs_dir: str, max_tokens: int = 400) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split each into chunks of max_tokens, respecting sentence boundaries.
    Return list of: {doc_name, chunk_index, text}
    """
    chunks = []
    if not os.path.exists(docs_dir):
        print(f"Error: Directory {docs_dir} not found.")
        return chunks

    for filename in os.listdir(docs_dir):
        if not filename.endswith(".txt"):
            continue
        filepath = os.path.join(docs_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split by sentences approximately using punctuation
            sentences = re.split(r'(?<=[.!?])\s+', content)
            
            current_chunk = []
            current_length = 0
            chunk_idx = 0
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence: continue
                
                # Approximate token count by word count
                tokens = len(sentence.split())
                
                if current_length + tokens > max_tokens and current_chunk:
                    chunks.append({
                        "doc_name": filename,
                        "chunk_index": chunk_idx,
                        "text": " ".join(current_chunk)
                    })
                    chunk_idx += 1
                    current_chunk = [sentence]
                    current_length = tokens
                else:
                    current_chunk.append(sentence)
                    current_length += tokens
                    
            if current_chunk:
                chunks.append({
                    "doc_name": filename,
                    "chunk_index": chunk_idx,
                    "text": " ".join(current_chunk)
                })
        except Exception as e:
            print(f"Warning: Failed to read {filename}. Error: {e}")
            
    return chunks

# --- SKILL: retrieve_and_answer ---
def retrieve_and_answer(
    query: str,
    collection,
    embedder,
    llm_call,
    top_k: int = 3,
    threshold: float = 0.30,
) -> dict:
    """
    Embed query, retrieve top_k chunks from ChromaDB.
    Filter chunks below threshold.
    If no chunks pass threshold, return refusal template.
    Otherwise call llm with retrieved chunks as context only.
    """
    refusal_template = {
        "answer": "This question is not covered in the retrieved policy documents. Retrieved chunks: {sources}. Please contact the relevant department for guidance.",
        "cited_chunks": [],
        "refused": True
    }

    query_embedding = embedder.encode([query]).tolist()[0]
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    if not results["ids"] or not results["ids"][0]:
        refusal_template["answer"] = refusal_template["answer"].format(sources="[]")
        return refusal_template

    cited_chunks = []
    
    # ChromaDB L2 distance to approx cosine similarity
    distances = results["distances"][0]
    metadatas = results["metadatas"][0]
    
    source_strings = []

    for dist, meta in zip(distances, metadatas):
        score = round(1.0 - (dist / 2.0), 3)
        source_strings.append(f"{meta['doc_name']}::chunk_{meta['chunk_index']}")
        
        if score >= threshold:
            cited_chunks.append({
                "doc_name": meta['doc_name'],
                "chunk_index": meta['chunk_index'],
                "score": score,
                "text": meta['text']
            })

    if not cited_chunks:
        sources_str = ", ".join(source_strings)
        refusal_template["answer"] = refusal_template["answer"].format(sources=sources_str)
        return refusal_template

    prompt = f"""You are a retrieval-augmented policy assistant. 
Strict rules:
1. Answer strictly using the context provided below.
2. Cite the source document name and chunk index.
3. Do not use general knowledge.
4. If the query spans multiple documents context, do not blend or merge them into one summary, list them separately.

Context Documents:
"""
    for chunk in cited_chunks:
        prompt += f"--- {chunk['doc_name']} (Chunk {chunk['chunk_index']}) ---\n{chunk['text']}\n\n"
        
    prompt += f"Query: {query}\nAnswer:"

    answer = llm_call(prompt)
    
    return {
        "answer": answer,
        "cited_chunks": cited_chunks,
        "refused": False
    }


# --- INDEX BUILDER ---
def build_index(docs_dir: str, db_path: str = "./chroma_db"):
    """
    Chunk all documents and store embeddings in ChromaDB.
    """
    print("[rag_server] Starting index build...")
    chunks = chunk_documents(docs_dir)
    if not chunks:
        print("[rag_server] No chunks generated. Aborting.")
        return
        
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    client = chromadb.PersistentClient(path=db_path)
    try:
        client.delete_collection("policy_docs")
    except:
        pass
        
    collection = client.create_collection("policy_docs", metadata={"hnsw:space": "l2"})
    
    ids = []
    embeddings = []
    metadatas = []
    
    print(f"[rag_server] Embedding {len(chunks)} chunks...")
    texts = [c["text"] for c in chunks]
    embeds = embedder.encode(texts).tolist()
    
    for i, (chunk, emb) in enumerate(zip(chunks, embeds)):
        ids.append(f"chunk_{i}")
        embeddings.append(emb)
        metadatas.append(chunk)
        
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas
    )
    print(f"[rag_server] Successfully inserted {len(chunks)} chunks into ChromaDB at {db_path}")

# --- CACHE (Avoid reloading model/DB on every request) ---
_embedder = None
_client = None

def get_rag_resources():
    global _embedder, _client
    if _embedder is None:
        print("[rag_server] Loading SentenceTransformer...")
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    if _client is None:
        db_path = os.path.join(os.path.dirname(__file__), "./chroma_db")
        print(f"[rag_server] Connecting to ChromaDB at {db_path}...")
        _client = chromadb.PersistentClient(path=db_path)
    return _embedder, _client

# --- PUBLIC QUERY INTERFACE (called by UC-MCP) ---
def query(question: str, llm_call=None) -> dict:
    """
    Public interface for UC-MCP to call.
    Uses cached resources to avoid TimeoutErrors.
    """
    embedder, client = get_rag_resources()
    
    try:
        collection = client.get_collection("policy_docs")
    except:
        return {
            "answer": "Error: RAG index not found. Please run '--build-index' first.",
            "cited_chunks": [],
            "refused": True
        }

    # Use default llm_call if none provided
    if llm_call is None:
        try:
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../uc-mcp")))
            from llm_adapter import call_llm
            llm_call = call_llm
        except:
            llm_call = lambda p: "Error: No LLM adapter found."

    # Use the 0.10 threshold for high reliability in this environment
    return retrieve_and_answer(question, collection, embedder, llm_call, threshold=0.30)

# --- NAIVE MODE ---
def naive_query(query: str, docs_dir: str, llm_call):
    """
    Load all documents into context without retrieval.
    """
    context = ""
    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(docs_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                context += f"\n--- {filename} ---\n{f.read()}\n"
                
    prompt = f"Answer the query based on the following documents:\n\n{context}\n\nQuery: {query}\nAnswer:"
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

    if args.docs_dir.startswith("../"):
        target_docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), args.docs_dir))
    else:
        target_docs_dir = args.docs_dir

    if not args.build_index and not args.query:
        parser.print_help()
        sys.exit(1)

    if args.build_index:
        print("Building index...")
        build_index(target_docs_dir, args.db_path)
        print("Index built. Run with --query to test.")

    if args.query:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../uc-mcp")))
        from llm_adapter import call_llm
        
        if args.naive:
            result = naive_query(args.query, target_docs_dir, call_llm)
            print(f"\nNaive answer:\n{result}")
        else:
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            client = chromadb.PersistentClient(path=args.db_path)
            try:
                collection = client.get_collection("policy_docs")
            except Exception as e:
                print("Collection 'policy_docs' not found. Please run with --build-index first.")
                sys.exit(1)
                
            res = retrieve_and_answer(args.query, collection, embedder, call_llm)
            print(json.dumps(res, indent=2))

if __name__ == "__main__":
    main()