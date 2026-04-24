import argparse
import os
import sys
import json
import re

# Add path for llm_adapter
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uc-mcp')))
try:
    from llm_adapter import call_llm
except ImportError:
    print("Warning: llm_adapter not found. Please ensure it's at ../uc-mcp/llm_adapter.py")
    def call_llm(prompt):
        return "LLM call failed: llm_adapter not found."

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
except ImportError:
    print("Warning: sentence_transformers or chromadb not installed.")

# --- Helper ---
def token_count(text: str) -> int:
    return len(text.split())

# --- SKILL: chunk_documents ---
def chunk_documents(docs_dir: str, max_tokens: int = 400) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split each into chunks of max_tokens, respecting sentence boundaries.
    Return list of: {doc_name, chunk_index, text}
    """
    chunks = []
    
    if not os.path.exists(docs_dir):
        print(f"Error: {docs_dir} not found.")
        return chunks
        
    for filename in os.listdir(docs_dir):
        if not filename.endswith('.txt'):
            continue
            
        filepath = os.path.join(docs_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        current_chunk_text = ""
        chunk_idx = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence: continue
            
            if token_count(current_chunk_text) + token_count(sentence) <= max_tokens:
                current_chunk_text += (sentence + " ")
            else:
                if current_chunk_text:
                    chunks.append({
                        "doc_name": filename,
                        "chunk_index": chunk_idx,
                        "text": current_chunk_text.strip()
                    })
                    chunk_idx += 1
                current_chunk_text = sentence + " "
                
        if current_chunk_text.strip():
            chunks.append({
                "doc_name": filename,
                "chunk_index": chunk_idx,
                "text": current_chunk_text.strip()
            })
            
    return chunks

# --- SKILL: retrieve_and_answer ---
def retrieve_and_answer(
    query: str,
    collection,
    embedder,
    llm_call,
    top_k: int = 3,
    threshold: float = 0.6,
) -> dict:
    """
    Embed query, retrieve top_k chunks from ChromaDB.
    Filter chunks below threshold.
    If no chunks pass threshold, return refusal template.
    Otherwise call llm with retrieved chunks as context only.
    Return: {answer, cited_chunks: [{doc_name, chunk_index, score}]}
    """
    query_emb = embedder.encode(query).tolist()
    
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k
    )
    
    cited_chunks = []
    context_texts = []
    
    # Chroma default space we used is cosine: distance = 1 - similarity
    max_distance = 1.0 - threshold
    
    if results['distances'] and results['distances'][0]:
        for i, dist in enumerate(results['distances'][0]):
            if dist <= max_distance:
                meta = results['metadatas'][0][i]
                text = results['documents'][0][i]
                cited_chunks.append({
                    "doc_name": meta['doc_name'],
                    "chunk_index": meta['chunk_index'],
                    "score": 1.0 - dist
                })
                context_texts.append(f"[{meta['doc_name']} Chunk {meta['chunk_index']}]: {text}")
                
    if not cited_chunks:
        refusal = "This question is not covered in the retrieved policy documents. Retrieved chunks: None. Please contact the relevant department for guidance."
        return {"answer": refusal, "cited_chunks": []}
        
    context_str = "\n\n".join(context_texts)
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    agents_path = os.path.join(base_dir, 'agents.md')
    if os.path.exists(agents_path):
        with open(agents_path, 'r', encoding='utf-8') as f:
            agents_text = f.read()
    else:
        agents_text = "Enforce RICE rules."
        
    prompt = f"""You are the AI Assistant.

=== AGENTS DEFINITION ===
{agents_text}

=== RETRIEVED CONTEXT ===
{context_str}

=== USER QUERY ===
{query}

=== INSTRUCTIONS ===
Answer the user query strictly using the retrieved context above. 
Do not use any external knowledge. 
You must cite the source document name and chunk index.
"""
    
    answer = llm_call(prompt)
    
    return {
        "answer": answer,
        "cited_chunks": cited_chunks
    }

# --- INDEX BUILDER ---
def build_index(docs_dir: str, db_path: str = "./chroma_db"):
    chunks = chunk_documents(docs_dir)
    print(f"Generated {len(chunks)} chunks.")
    
    if not chunks:
        print("No chunks to index.")
        return
        
    print("Loading SentenceTransformer model...")
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    print("Initializing ChromaDB...")
    client = chromadb.PersistentClient(path=db_path)
    
    collection = client.get_or_create_collection(
        name="policy_docs", 
        metadata={"hnsw:space": "cosine"}
    )
    
    if collection.count() > 0:
        collection.delete(ids=collection.get()['ids'])
        
    ids = []
    texts = []
    metadatas = []
    
    for i, c in enumerate(chunks):
        ids.append(f"chunk_{i}")
        texts.append(c['text'])
        metadatas.append({
            "doc_name": c['doc_name'],
            "chunk_index": c['chunk_index']
        })
        
    print(f"Embedding and upserting {len(texts)} chunks...")
    embeddings = embedder.encode(texts).tolist()
    
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas
    )
    print("Successfully built the index.")

# --- NAIVE MODE ---
def naive_query(query: str, docs_dir: str, llm_call):
    if not os.path.exists(docs_dir):
        return f"Error: {docs_dir} not found."
        
    all_text = ""
    for filename in os.listdir(docs_dir):
        if filename.endswith('.txt'):
            with open(os.path.join(docs_dir, filename), 'r', encoding='utf-8') as f:
                all_text += f"\n--- {filename} ---\n{f.read()}"
                
    prompt = f"""You are a helpful assistant.
Context:
{all_text}

Query: {query}
Answer the query based on the context.
"""
    return llm_call(prompt)

# --- MAIN ---
def main():
    parser = argparse.ArgumentParser(description="UC-RAG RAG Server")
    parser.add_argument("--build-index", action="store_true", help="Build ChromaDB index")
    parser.add_argument("--query", type=str, help="Query the RAG server")
    parser.add_argument("--naive", action="store_true", help="Run naive mode")
    parser.add_argument("--docs-dir", type=str, default="../data/policy-documents")
    parser.add_argument("--db-path", type=str, default="./chroma_db")
    args = parser.parse_args()

    if not args.build_index and not args.query:
        parser.print_help()
        sys.exit(1)

    if args.build_index:
        print("Building index...")
        build_index(args.docs_dir, args.db_path)
        print("Index built. Run with --query to test.")

    if args.query:
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'uc-mcp')))
        from llm_adapter import call_llm
        
        if args.naive:
            result = naive_query(args.query, args.docs_dir, call_llm)
            print(f"\nNaive answer:\n{result}")
        else:
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            client = chromadb.PersistentClient(path=args.db_path)
            collection = client.get_collection(name="policy_docs")
            
            result = retrieve_and_answer(
                query=args.query,
                collection=collection,
                embedder=embedder,
                llm_call=call_llm
            )
            
            print(f"\nAnswer:\n{result['answer']}\n")
            if result['cited_chunks']:
                print("Cited chunks:")
                for c in result['cited_chunks']:
                    print(f"- {c['doc_name']} (Chunk {c['chunk_index']}) [Score: {c['score']:.2f}]")

if __name__ == "__main__":
    main()
