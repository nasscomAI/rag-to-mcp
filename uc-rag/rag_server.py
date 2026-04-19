import argparse
import os
import sys
import re
import chromadb
from sentence_transformers import SentenceTransformer

# Add parent directory to sys.path to import llm_adapter
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uc-mcp")))
from llm_adapter import call_llm

# Fix UnicodeEncodeError for Windows console
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback for older python or non-ANSI environments
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# --- CONFIG ---
DB_PATH = os.path.join(os.path.dirname(__file__), "./chroma_db")
COLLECTION_NAME = "policy_docs"

_collection = None
_embedder = None

def get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=DB_PATH)
        try:
            _collection = client.get_collection(name=COLLECTION_NAME)
        except Exception:
            _collection = None
    return _collection

def get_embedder():
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedder

# --- SKILL: chunk_documents ---
def chunk_documents(docs_dir: str, max_tokens: int = 400) -> list[dict]:
    """
    Load all .txt files from docs_dir.
    Split each into chunks of max_tokens, respecting sentence and newline boundaries.
    """
    chunks = []
    if not os.path.exists(docs_dir):
        print(f"Error: Directory {docs_dir} not found.")
        return chunks

    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(docs_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Split on punctuation followed by space OR on newlines
            # This handles headers and bullet points without periods
            lines = re.split(r'(?<=[.!?])\s+|\n+', content)
            
            current_chunk = []
            current_token_count = 0
            chunk_index = 0
            
            # Target smaller chunks (~250 tokens) for higher density
            target_tokens = min(250, max_tokens)
            
            for line in lines:
                line = line.strip()
                if not line: continue
                
                # Rough token estimation
                line_tokens = len(line.split()) * 1.3
                
                if current_token_count + line_tokens > target_tokens and current_chunk:
                    chunks.append({
                        "doc_name": filename,
                        "chunk_index": chunk_index,
                        "text": " ".join(current_chunk).strip()
                    })
                    current_chunk = [line]
                    current_token_count = line_tokens
                    chunk_index += 1
                else:
                    current_chunk.append(line)
                    current_token_count += line_tokens
            
            if current_chunk:
                chunks.append({
                    "doc_name": filename,
                    "chunk_index": chunk_index,
                    "text": " ".join(current_chunk).strip()
                })
                
    return chunks


# --- SKILL: retrieve_and_answer ---
def retrieve_and_answer(
    query: str,
    collection,
    embedder,
    llm_call,
    top_k: int = 3,
    threshold: float = 0.3,
) -> dict:
    """
    Embed query, retrieve chunks, filter by threshold, and generate grounded answer.
    """
    query_embedding = embedder.encode([query])[0].tolist()
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    valid_chunks = []
    for i in range(len(results['ids'][0])):
        # Chromadb cosine distance = 1 - cosine_similarity
        similarity = 1 - results['distances'][0][i]
        if similarity >= threshold:
            valid_chunks.append({
                "text": results['documents'][0][i],
                "doc_name": results['metadatas'][0][i]['doc_name'],
                "chunk_index": results['metadatas'][0][i]['chunk_index'],
                "score": similarity
            })
            
    if not valid_chunks:
        refusal = (
            "This question is not covered in the retrieved policy documents. "
            "Retrieved chunks: [None above threshold]. Please contact the relevant "
            "department for guidance."
        )
        return {"answer": refusal, "cited_chunks": []}
    
    # Grounded Prompt
    context_text = "\n\n".join([
        f"--- Source: {c['doc_name']} (Chunk {c['chunk_index']}) ---\n{c['text']}" 
        for c in valid_chunks
    ])
    
    prompt = f"""You are a Retrieval-Augmented Generation (RAG) assistant for the City Municipal Corporation.

GROUNDING RULES:
1. ANSWER ONLY using the provided "Retrieved Context" below. 
2. CITATION: Every claim must be followed by a citation in brackets, e.g., [{valid_chunks[0]['doc_name']}, Chunk {valid_chunks[0]['chunk_index']}].
3. REFUSAL: If the answer is not contained within the context, you must state that it is not covered.
4. NO EXTERNAL KNOWLEDGE: Use only the provided documents.

Retrieved Context:
{context_text}

User Query: {query}

Answer:"""

    answer = llm_call(prompt)
    return {"answer": answer, "cited_chunks": valid_chunks}


# --- INDEX BUILDER ---
def build_index(docs_dir: str, db_path: str = "./chroma_db"):
    """
    Chunk all documents and store embeddings in ChromaDB.
    """
    print(f"Loading documents from {docs_dir}...")
    chunks = chunk_documents(docs_dir)
    print(f"Created {len(chunks)} chunks.")
    
    client = chromadb.PersistentClient(path=db_path)
    
    # Clear existing collection to prevent duplicates
    try:
        client.delete_collection(name="policy_docs")
        print("Cleared existing collection.")
    except Exception:
        pass
        
    # Use cosine similarity for the threshold logic
    collection = client.create_collection(
        name="policy_docs", 
        metadata={"hnsw:space": "cosine"}
    )
    
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    
    print("Embedding and indexing chunks...")
    for i, chunk in enumerate(chunks):
        embedding = embedder.encode([chunk['text']])[0].tolist()
        collection.add(
            ids=[f"chunk_{i}"],
            embeddings=[embedding],
            metadatas=[{
                "doc_name": chunk['doc_name'],
                "chunk_index": chunk['chunk_index']
            }],
            documents=[chunk['text']]
        )
    print("Indexing complete.")


# --- NAIVE MODE ---
def naive_query(query: str, docs_dir: str, llm_call):
    """
    Load all documents into context WITHOUT retrieval or rules.
    """
    all_text = ""
    for filename in os.listdir(docs_dir):
        if filename.endswith(".txt"):
            with open(os.path.join(docs_dir, filename), "r", encoding="utf-8") as f:
                all_text += f"\n\n--- {filename} ---\n" + f.read()
                
    prompt = f"""Answer this query using the documents below.
    
Documents:
{all_text}

Query: {query}
"""
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
        print("Done.")

    if args.query:
        if args.naive:
            result = naive_query(args.query, args.docs_dir, call_llm)
            print(f"\nNaive answer:\n{result}")
        else:
            # Full RAG query
            client = chromadb.PersistentClient(path=args.db_path)
            collection = client.get_collection(name="policy_docs")
            embedder = SentenceTransformer('all-MiniLM-L6-v2')
            
            result = retrieve_and_answer(
                args.query, 
                collection, 
                embedder, 
                call_llm
            )
            
            print(f"\nRAG Answer:\n{result['answer']}")
            if result['cited_chunks']:
                print("\nCited Chunks:")
                for c in result['cited_chunks']:
                    print(f"- {c['doc_name']} (Chunk {c['chunk_index']}), Similarity: {c['score']:.4f}")


# --- PUBLIC QUERY INTERFACE ---
def query(question: str, llm_call=None) -> dict:
    """
    Public interface for UC-MCP to call.
    """
    collection = get_collection()
    if collection is None:
        return {
            "answer": "Error: RAG index not found. Run 'python rag_server.py --build-index' first.",
            "cited_chunks": [],
            "refused": True
        }
    
    embedder = get_embedder()
    result = retrieve_and_answer(
        question, 
        collection, 
        embedder, 
        llm_call or call_llm
    )
    
    # Ensure refused key is present (retrieve_and_answer uses answer logic)
    # If retrieve_and_answer returns an answer starting with "This question is not covered", 
    # we should set refused=True.
    if "not covered in the retrieved policy documents" in result["answer"]:
        result["refused"] = True
    else:
        result["refused"] = False
        
    return result


if __name__ == "__main__":
    main()
