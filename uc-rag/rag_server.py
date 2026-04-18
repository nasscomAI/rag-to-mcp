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
    chunks = []
    
    if not os.path.exists(docs_dir):
        print(f"Error: {docs_dir} not found.")
        return chunks
        
    for filename in os.listdir(docs_dir):
        if not filename.endswith('.txt'): continue
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()

        # Split on sentence boundaries (e.g. . ! ?)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        current_chunk = []
        current_length = 0
        chunk_idx = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence: continue
            
            # Simple word-based heuristic for token length
            sentence_tokens = len(sentence.split())
            
            if current_length + sentence_tokens > max_tokens and current_chunk:
                chunks.append({
                    "doc_name": filename,
                    "chunk_index": chunk_idx,
                    "text": " ".join(current_chunk)
                })
                chunk_idx += 1
                current_chunk = [sentence]
                current_length = sentence_tokens
            else:
                current_chunk.append(sentence)
                current_length += sentence_tokens
                
        if current_chunk:
            chunks.append({
                "doc_name": filename,
                "chunk_index": chunk_idx,
                "text": " ".join(current_chunk)
            })
            
    return chunks

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
    query_emb = embedder.encode([query]).tolist()
    
    results = collection.query(
        query_embeddings=query_emb,
        n_results=top_k
    )
    
    if not results['distances'] or not results['distances'][0]:
        return {
            "answer": "This question is not covered in the retrieved policy documents.\nRetrieved chunks: []. Please contact the relevant department for guidance.", 
            "cited_chunks": []
        }
        
    distances = results['distances'][0]
    metadatas = results['metadatas'][0]
    documents = results['documents'][0]
    
    valid_chunks = []
    
    for doc, meta, dist in zip(documents, metadatas, distances):
        # We calculate similarity from distance depending on how chromadb returned it.
        # Collection relies on cosine, so distance is cosine distance
        sim_score = 1.0 - dist
        
        if sim_score >= threshold:
            valid_chunks.append({
                "text": doc,
                "doc_name": meta["doc_name"],
                "chunk_index": meta["chunk_index"],
            })
            
    if not valid_chunks:
        # Refusal template format
        sources = ", ".join([f"{meta['doc_name']} (chunk {meta['chunk_index']})" for meta in metadatas])
        return {
            "answer": f"This question is not covered in the retrieved policy documents.\nRetrieved chunks: [{sources}]. Please contact the relevant department for guidance.",
            "cited_chunks": []
        }
        
    # Apply cross-document rule: Group chunks by document and pick the most relevant document
    # "Never merge retrieved chunks from different documents into one answer."
    top_doc = valid_chunks[0]["doc_name"]
    filtered_chunks = [c for c in valid_chunks if c["doc_name"] == top_doc]
    
    prompt = f"""You are a retrieval-augmented policy assistant. 
Using ONLY the following context chunks from {top_doc}, answer the query. Do not use general knowledge.

Context:"""
    for c in filtered_chunks:
         prompt += f"\n[Chunk {c['chunk_index']}]: {c['text']}"
         
    prompt += f"\n\nQuery: {query}\n\nAnswer:"
    
    answer = llm_call(prompt)
    
    cited = [{"doc_name": c["doc_name"], "chunk_index": c["chunk_index"]} for c in filtered_chunks]
    return {
        "answer": answer,
        "cited_chunks": cited
    }


# --- INDEX BUILDER ---
def build_index(docs_dir: str, db_path: str = "./chroma_db"):
    """
    Chunk all documents and store embeddings in ChromaDB.
    Called once before querying.
    """
    import chromadb
    from sentence_transformers import SentenceTransformer
    
    print("Loading documents and chunking...")
    chunks = chunk_documents(docs_dir)
    print(f"Generated {len(chunks)} chunks.")
    
    if not chunks:
        print("No documents found to index.")
        return
        
    print("Loading SentenceTransformer model...")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=db_path)
    
    # recreate for clean build
    try:
        client.delete_collection("policy_collection")
    except Exception:
        pass
        
    collection = client.create_collection(
        name="policy_collection",
        metadata={"hnsw:space": "cosine"}
    )
    
    ids = [f"{c['doc_name']}_{c['chunk_index']}" for c in chunks]
    documents = [c['text'] for c in chunks]
    metadatas = [{"doc_name": c['doc_name'], "chunk_index": c['chunk_index']} for c in chunks]
    
    print("Computing embeddings...")
    embeddings = embedder.encode(documents).tolist()
    
    print("Upserting to ChromaDB...")
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )
    print("Index build complete!")


# --- NAIVE MODE (run this first to see failure modes) ---
def naive_query(query: str, docs_dir: str, llm_call):
    """
    Load all documents into context without retrieval.
    Run this BEFORE building your RAG pipeline to observe the failure modes.
    """
    text_blocks = []
    if os.path.exists(docs_dir):
        for filename in os.listdir(docs_dir):
            if filename.endswith('.txt'):
                filepath = os.path.join(docs_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    text_blocks.append(f"--- {filename} ---\n{f.read()}")
                    
    context = "\n".join(text_blocks)
    prompt = f"Using the following context, please answer the query.\n\nContext:\n{context}\n\nQuery: {query}"
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
            try:
                from llm_adapter import call_llm
            except ImportError:
                print("Could not import llm_adapter. Make sure ../uc-mcp/llm_adapter.py exists")
                sys.exit(1)
            result = naive_query(args.query, args.docs_dir, call_llm)
            print(f"\nNaive answer:\n{result}")
        else:
            # Full RAG query
            import chromadb
            from sentence_transformers import SentenceTransformer
            sys.path.insert(0, "../uc-mcp")
            try:
                from llm_adapter import call_llm
            except ImportError:
                print("Could not import llm_adapter. Make sure ../uc-mcp/llm_adapter.py exists")
                sys.exit(1)
                
            embedder = SentenceTransformer('all-MiniLM-L6-v2')
            client = chromadb.PersistentClient(path=args.db_path)
            try:
                collection = client.get_collection("policy_collection")
            except ValueError:
                print("Collection not found. Did you run --build-index first?")
                sys.exit(1)
                
            res = retrieve_and_answer(args.query, collection, embedder, call_llm)
            print("\n====================")
            print("Answer:")
            print(res["answer"])
            print("====================")
            if res["cited_chunks"]:
                print("Sources:")
                for c in res["cited_chunks"]:
                    print(f"- {c['doc_name']} (Chunk {c['chunk_index']})")


if __name__ == "__main__":
    main()
