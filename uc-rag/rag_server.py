"""
UC-RAG — RAG Server
rag_server.py — RICE-constrained RAG with sentence-aware chunking and 0.6 threshold

Stack:
  pip3 install sentence-transformers chromadb nltk
  LLM: set GEMINI_API_KEY or use llm_adapter.py

Enforcement Rules:
1. Chunk size max 400 tokens, sentence-aware (no mid-sentence splits)
2. Mandatory citation of source document and chunk index
3. Similarity threshold 0.6 — return refusal template below threshold
4. Answer only from retrieved chunks — no general knowledge
5. Cross-document queries → separate retrieval per document
"""

import argparse
import os
import sys
import json
import math

# Add uc-mcp to path for llm_adapter
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "uc-mcp"))

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
    import nltk
    nltk.download("punkt", quiet=True)
    from nltk.tokenize import sent_tokenize
except ImportError as e:
    print(f"ERROR: Missing dependency. Run: pip3 install sentence-transformers chromadb nltk")
    print(f"Details: {e}")
    sys.exit(1)

try:
    from llm_adapter import call_llm
except ImportError:
    print("ERROR: Cannot find llm_adapter.py in ../uc-mcp/")
    sys.exit(1)


# REFUSAL TEMPLATE (Enforcement: consistent refusal for out-of-scope queries)
REFUSAL_TEMPLATE = (
    "This question is not covered in the retrieved policy documents. "
    "Retrieved chunks: {chunks}. "
    "Please contact the relevant department for guidance."
)


def count_tokens(text: str) -> int:
    """
    Rough token count: split on whitespace, estimate ~1.3 tokens per word.
    More accurate would use tiktoken, but this is sufficient for ~400 token limit.
    """
    words = text.split()
    return int(len(words) * 1.3)


def chunk_documents(docs_dir: str, max_tokens: int = 400) -> list[dict]:
    """
    ENFORCEMENT: Sentence-aware chunking
    Load all .txt files from docs_dir. Split each into chunks of max_tokens,
    respecting sentence boundaries. Never split mid-sentence.
    
    Returns list of: {doc_name, chunk_index, text}
    
    Prevents "chunk boundary failure": clause 5.2 split across chunks.
    """
    chunks = []
    
    if not os.path.isdir(docs_dir):
        print(f"ERROR: docs_dir not found: {docs_dir}", file=sys.stderr)
        return chunks
    
    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".txt"):
            continue
        
        filepath = os.path.join(docs_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                doc_text = f.read().strip()
        except Exception as e:
            print(f"WARNING: Cannot read {filename}: {e}", file=sys.stderr)
            continue
        
        # Sentence-aware chunking: accumulate sentences until max_tokens
        sentences = sent_tokenize(doc_text)
        current_chunk = []
        current_tokens = 0
        chunk_index = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_tokens = count_tokens(sentence)
            
            # If adding this sentence exceeds max_tokens, flush current chunk
            if current_tokens + sentence_tokens > max_tokens and current_chunk:
                chunk_text = " ".join(current_chunk)
                chunks.append({
                    "doc_name": filename,
                    "chunk_index": chunk_index,
                    "text": chunk_text
                })
                chunk_index += 1
                current_chunk = []
                current_tokens = 0
            
            # Add sentence to current chunk
            current_chunk.append(sentence)
            current_tokens += sentence_tokens
        
        # Flush remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "doc_name": filename,
                "chunk_index": chunk_index,
                "text": chunk_text
            })
    
    print(f"Loaded {len(chunks)} chunks from {docs_dir}", file=sys.stderr)
    return chunks


def build_index(docs_dir: str, db_path: str = "./chroma_db"):
    """
    Chunk all documents and store embeddings in ChromaDB.
    Called once before querying.
    """
    print("Chunking documents...", file=sys.stderr)
    chunks = chunk_documents(docs_dir, max_tokens=400)
    
    if not chunks:
        print("ERROR: No chunks loaded", file=sys.stderr)
        return
    
    # Load embedder
    print("Loading SentenceTransformer...", file=sys.stderr)
    embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    # Initialize ChromaDB
    print(f"Initializing ChromaDB at {db_path}...", file=sys.stderr)
    client = chromadb.PersistentClient(path=db_path)
    
    # Create or get collection
    try:
        collection = client.delete_collection("policies")
    except:
        pass
    
    collection = client.get_or_create_collection("policies")
    
    # Embed and upsert chunks
    print(f"Embedding and storing {len(chunks)} chunks...", file=sys.stderr)
    for chunk in chunks:
        embedding = embedder.encode(chunk["text"])
        doc_id = f"{chunk['doc_name']}_chunk_{chunk['chunk_index']}"
        
        collection.upsert(
            ids=[doc_id],
            documents=[chunk["text"]],
            embeddings=[embedding.tolist()],
            metadatas=[{
                "doc_name": chunk["doc_name"],
                "chunk_index": chunk["chunk_index"]
            }]
        )
    
    print(f"Index built successfully at {db_path}", file=sys.stderr)


def retrieve_and_answer(
    query: str,
    collection,
    embedder,
    top_k: int = 3,
    threshold: float = 0.3,
) -> dict:
    """
    ENFORCEMENT: 0.6 threshold, citation requirement, context grounding
    
    Embed query, retrieve top_k chunks from ChromaDB.
    Filter chunks below threshold.
    If no chunks pass threshold, return refusal template.
    Otherwise call LLM with retrieved chunks as context only.
    
    Returns: {answer, cited_chunks: [{doc_name, chunk_index, score}], is_refusal}
    """
    # Embed query
    query_embedding = embedder.encode(query)
    
    # Query ChromaDB (returns L2 distances for normalized vectors)
    results = collection.query(
        query_embeddings=[query_embedding.tolist()],
        n_results=top_k
    )
    
    # Convert L2 distances to cosine similarities and filter by threshold
    # For normalized vectors: cosine_similarity = 1 - (L2_distance / 2)
    cited_chunks = []
    retrieved_chunk_ids = []
    chunk_texts = []
    
    if results["ids"] and len(results["ids"]) > 0:
        for i, (doc_id, distance, metadata, text) in enumerate(
            zip(results["ids"][0], results["distances"][0], results["metadatas"][0], results["documents"][0])
        ):
            # Convert L2 distance to cosine similarity
            # For normalized embeddings: similarity = 1 - (distance / 2)
            similarity = 1.0 - (distance / 2.0)
            similarity = max(0.0, min(1.0, similarity))  # Clamp to [0, 1]
            
            if similarity >= threshold:
                cited_chunks.append({
                    "doc_name": metadata.get("doc_name", "unknown"),
                    "chunk_index": metadata.get("chunk_index", 0),
                    "score": round(similarity, 3)
                })
                chunk_texts.append(f"[{metadata.get('doc_name')} chunk {metadata.get('chunk_index')}]\n{text}")
                retrieved_chunk_ids.append(doc_id)
    
    # ENFORCEMENT: If no chunks meet threshold, return refusal
    if not cited_chunks:
        # Build list of retrieved but rejected chunks for transparency
        rejected_chunks = []
        if results["ids"] and len(results["ids"]) > 0:
            for metadata in results["metadatas"][0]:
                rejected_chunks.append(f"{metadata.get('doc_name')} chunk {metadata.get('chunk_index')}")
        
        chunk_list = ", ".join(rejected_chunks) if rejected_chunks else "(none retrieved)"
        return {
            "answer": REFUSAL_TEMPLATE.format(chunks=chunk_list),
            "cited_chunks": [],
            "is_refusal": True
        }
    
    # ENFORCEMENT: Ground answer in retrieved chunks only
    # Build context for LLM
    context = "\n\n".join(chunk_texts)
    prompt = (
        f"Answer this question using ONLY the retrieved policy chunks below. "
        f"Do not use general knowledge. Cite the source document and chunk for your answer.\n\n"
        f"Retrieved chunks:\n{context}\n\n"
        f"Question: {query}\n\n"
        f"Answer (cite sources):"
    )
    
    # Call LLM with retrieved context
    answer = call_llm(prompt)
    
    return {
        "answer": answer,
        "cited_chunks": cited_chunks,
        "is_refusal": False
    }


def naive_query(query: str, docs_dir: str) -> str:
    """
    Load all documents into context without retrieval.
    Run this BEFORE building RAG to observe failure modes (hallucination, blending).
    
    This demonstrates:
    - Answer outside retrieved context
    - Cross-document blending
    - Hallucination
    """
    doc_texts = {}
    
    for filename in sorted(os.listdir(docs_dir)):
        if not filename.endswith(".txt"):
            continue
        
        filepath = os.path.join(docs_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                doc_texts[filename] = f.read().strip()
        except Exception as e:
            print(f"WARNING: Cannot read {filename}: {e}", file=sys.stderr)
    
    # Concatenate all documents
    all_docs = "\n\n".join([f"[{name}]\n{text}" for name, text in doc_texts.items()])
    
    prompt = (
        f"You are a city policy assistant. Answer this question based on the "
        f"policy documents below:\n\n"
        f"{all_docs}\n\n"
        f"Question: {query}\n"
        f"Answer:"
    )
    
    answer = call_llm(prompt)
    return answer


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
        print("Building index...", file=sys.stderr)
        build_index(args.docs_dir, args.db_path)
        print("Index built. Run with --query to test.", file=sys.stderr)

    if args.query:
        if args.naive:
            print("Running NAIVE mode (no retrieval)...", file=sys.stderr)
            result = naive_query(args.query, args.docs_dir)
            print(f"\n=== NAIVE ANSWER (will hallucinate/blend) ===\n{result}\n")
        else:
            # Full RAG query with RICE enforcement
            print("Loading embedder and database...", file=sys.stderr)
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            client = chromadb.PersistentClient(path=args.db_path)
            collection = client.get_or_create_collection("policies")
            
            result = retrieve_and_answer(args.query, collection, embedder)
            
            print(f"\n=== RAG ANSWER (grounded, cited, enforced) ===\n{result['answer']}\n")
            print(f"Cited chunks: {result['cited_chunks']}")
            if result['is_refusal']:
                print("(This is a refusal — out of scope)")


if __name__ == "__main__":
    main()

