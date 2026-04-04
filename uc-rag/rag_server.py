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
import chromadb

# Add the uc-mcp directory to the path for llm_adapter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../uc-mcp"))

from google import genai
from google.genai import types
from llm_adapter import call_llm

# --- SKILL: chunk_documents ---
def chunk_documents(docs_dir: str, max_tokens: int = 150) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split by section headers and prepend header to each chunk (Anchoring).
    """
    import re
    chunks = []
    if not os.path.exists(docs_dir):
        raise FileNotFoundError(f"Directory not found: {docs_dir}")

    for filename in sorted(os.listdir(docs_dir)):
        if filename.endswith(".txt"):
            path = os.path.join(docs_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 1. Strip decorative CMC lines to improve signal-to-noise
            content = content.replace('═', '')
            
            # 2. Split by section headers (e.g., 5. LEAVE WITHOUT PAY (LWP))
            # Fixed regex to include parentheses and special characters in headers
            section_pattern = r'(\n\d+\.\s+[^\n]+\n)'
            temp_parts = re.split(section_pattern, content)
            
            current_header = "General Policy Structure"
            
            for part in temp_parts:
                if re.match(section_pattern, part):
                    current_header = part.strip()
                    continue
                
                # 3. Improved sentence splitting to avoid breaking decimals (5.1, 5.2)
                sentences = [s.strip() for s in re.split(r'(?<!\d)\.(?!\d)\s+', part) if s.strip()]
                
                current_chunk = []
                current_token_count = 0
                chunk_index_in_file = len([c for c in chunks if c["doc_name"] == filename])
                
                i = 0
                while i < len(sentences):
                    sentence = sentences[i]
                    anchored_sentence = f"Section: {current_header}. {sentence}"
                    tokens = len(anchored_sentence.split())
                    
                    if current_token_count + tokens > max_tokens and current_chunk:
                        chunks.append({
                            "doc_name": filename,
                            "section_title": current_header,
                            "chunk_index": chunk_index_in_file,
                            "text": " ".join(current_chunk)
                        })
                        chunk_index_in_file += 1
                        i = max(0, i - 1) # Overlap
                        current_chunk = []
                        current_token_count = 0
                    else:
                        if not current_chunk:
                            current_chunk.append(f"Section: {current_header}.")
                        current_chunk.append(sentence)
                        current_token_count += tokens
                        i += 1
                
                if current_chunk and len(current_chunk) > 1:
                    chunks.append({
                        "doc_name": filename,
                        "section_title": current_header,
                        "chunk_index": chunk_index_in_file,
                        "text": " ".join(current_chunk)
                    })
    return chunks


# --- SKILL: retrieve_and_answer ---
def retrieve_and_answer(
    query: str,
    collection,          # ChromaDB collection
    llm_call,            # callable: (prompt: str) -> str
    top_k: int = 3,
    threshold: float = 0.6,
) -> dict:
    """
    Embed query, retrieve top_k chunks from ChromaDB.
    Filter chunks below threshold.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found in environment. "
            "Please set it: export GEMINI_API_KEY='your-key-here'. "
            "Get a free key at: https://aistudio.google.com/app/apikey"
        )
    # Switch to v1beta to access the newer embedding models
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version='v1beta'))
    
    # Use the modern embedding model verified in your project
    res = client.models.embed_content(
        model='gemini-embedding-2-preview',
        contents=query,
        config=types.EmbedContentConfig(task_type='RETRIEVAL_QUERY')
    )
    query_embedding = res.embeddings[0].values
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]
    
    # For 'cosine' space, ChromaDB returns 1 - cosine_similarity
    passing_chunks = []
    for doc, meta, dist in zip(docs, metadatas, distances):
        score = 1.0 - dist
        if score >= threshold:
            passing_chunks.append({
                "doc_name": meta["doc_name"],
                "section_title": meta.get("section_title", "General"),
                "text": doc,
                "score": round(score, 3)
            })
    
    if not passing_chunks:
        # Defensive: use .get() for metadata keys to avoid crashes on mismatched indices
        sources = ", ".join([f"{meta.get('doc_name', 'unknown')}::chunk_{meta.get('chunk_index', 'idx')}" for meta in metadatas])
        refusal = (
            f"This question is not covered in the retrieved policy documents.\n"
            f"Retrieved chunks: [{sources}]. Please contact the relevant department for guidance."
        )
        return {"answer": refusal, "cited_chunks": [], "refused": True}
    
    # Grounding prompt
    context_text = "\n\n".join([f"Document: {c['doc_name']}, {c['section_title']}\n{c['text']}" for c in passing_chunks])
    prompt = (
        f"You are a policy assistant for City Municipal Corporation staff. "
        f"Answer the user query using ONLY the provided context below. "
        f"If the answer is not in the context, use the refusal template provided.\n\n"
        f"Context:\n{context_text}\n\n"
        f"User Query: {query}\n\n"
        f"Instructions:\n"
        f"1. Use ONLY the information above. Never use general knowledge.\n"
        f"2. Cite the Document Name and specific Section/Clause for every claim.\n"
        f"3. Do not mention internal chunk indices in your answer.\n\n"
        f"Answer:"
    )
    
    answer = llm_call(prompt)
    return {"answer": answer, "cited_chunks": passing_chunks, "refused": False}


# --- INDEX BUILDER ---
def build_index(docs_dir: str, db_path: str = "./chroma_db"):
    """
    Chunk all documents and store embeddings in ChromaDB.
    """
    import chromadb
    from sentence_transformers import SentenceTransformer
    
    print(f"Loading documents from {docs_dir}...")
    chunks = chunk_documents(docs_dir)
    print(f"Split into {len(chunks)} chunks.")
    
    print("Initializing embedder...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    print(f"Connecting to ChromaDB at {db_path}...")
    client = chromadb.PersistentClient(path=db_path)
    
    # Reset collection if exists
    try:
        client.delete_collection("policy_docs")
    except:
        pass
    # Use 'cosine' space for better similarity matching
    collection = client.create_collection("policy_docs", metadata={"hnsw:space": "cosine"})
    
    print("Embedding and indexing chunks with Gemini...")
    texts = [c["text"] for c in chunks]
    metadatas = [
        {
            "doc_name": c["doc_name"], 
            "section_title": c["section_title"],
            "chunk_index": c["chunk_index"]
        } 
        for c in chunks
    ]
    ids = [f"{c['doc_name']}_{c['chunk_index']}" for c in chunks]
    
    # Generate document embeddings using Gemini (RETRIEVAL_DOCUMENT)
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[rag_server] ERROR: GEMINI_API_KEY not found in environment.")
        print("[rag_server] Get a free key at: https://aistudio.google.com/app/apikey")
        print("[rag_server] Set it with: export GEMINI_API_KEY='your-key-here'")
        return
    # Switch to v1beta to access the newer embedding models
    genai_client = genai.Client(api_key=api_key, http_options=types.HttpOptions(api_version='v1beta'))
    
    # We can embed in batches if needed, but for policy docs a single call is usually fine or small batches
    res = genai_client.models.embed_content(
        model='gemini-embedding-2-preview',
        contents=texts,
        config=types.EmbedContentConfig(task_type='RETRIEVAL_DOCUMENT')
    )
    embeddings = [e.values for e in res.embeddings]
    
    collection.add(
        ids=ids,
        embeddings=embeddings,
        metadatas=metadatas,
        documents=texts
    )
    print("Index build complete.")


# --- SKILL: query ---
def query(question: str, llm_call=None) -> dict:
    """
    Public interface for UC-MCP to call.
    Automatically initializes the ChromaDB client and collection.
    """
    import chromadb
    db_path = os.path.join(os.path.dirname(__file__), "./chroma_db")
    if not os.path.exists(db_path):
         return {
            "answer": f"Error: Index not found at {db_path}. Build it first with: python3 rag_server.py --build-index",
            "cited_chunks": [],
            "refused": True
        }
    
    client = chromadb.PersistentClient(path=db_path)
    try:
        collection = client.get_collection("policy_docs")
    except:
        return {
            "answer": "Error: Collection 'policy_docs' not found. Build the index first.",
            "cited_chunks": [],
            "refused": True
        }
    
    return retrieve_and_answer(question, collection, llm_call)


# --- NAIVE MODE (run this first to see failure modes) ---
def naive_query(query: str, docs_dir: str, llm_call):
    """
    Load all documents into context without retrieval.
    """
    context = ""
    for filename in sorted(os.listdir(docs_dir)):
        if filename.endswith(".txt"):
            path = os.path.join(docs_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                context += f"\n--- {filename} ---\n"
                context += f.read()
    
    prompt = (
        f"Answer the user query using the following policy documents.\n\n"
        f"Documents:\n{context}\n\n"
        f"User Query: {query}\n\n"
        f"Answer:"
    )
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
        build_index(args.docs_dir, args.db_path)
        print("Success: Index built with Gemini Embeddings. Run with --query to test.")

    if args.query:
        if args.naive:
            result = naive_query(args.query, args.docs_dir, call_llm)
            print(f"\nNaive answer:\n{result}")
        else:
            # Full RAG query
            import chromadb
            
            if not os.path.exists(args.db_path):
                print(f"Error: Index not found at {args.db_path}. Build it first with --build-index.")
                sys.exit(1)
                
            client = chromadb.PersistentClient(path=args.db_path)
            try:
                collection = client.get_collection("policy_docs")
            except:
                print("Error: Collection 'policy_docs' not found. Build the index first.")
                sys.exit(1)
                
            result = retrieve_and_answer(args.query, collection, call_llm)
            
            print(f"\n{result['answer']}")
            if result['cited_chunks']:
                # Deduplicate sources/sections for the footer
                seen_sources = set()
                print("\nSources:")
                for chunk in result['cited_chunks']:
                    source_line = f"- {chunk['section_title']} ({chunk['doc_name']})"
                    if source_line not in seen_sources:
                        print(source_line)
                        seen_sources.add(source_line)


if __name__ == "__main__":
    main()
