import os
import argparse
import chromadb
from sentence_transformers import SentenceTransformer
import google.generativeai as genai

# Setup
DB_PATH = "./chroma_db"
COLLECTION_NAME = "policies"
MODEL_NAME = "all-MiniLM-L6-v2"

class RAGServer:
    def __init__(self):
        self.encoder = SentenceTransformer(MODEL_NAME)
        self.chroma_client = chromadb.PersistentClient(path=DB_PATH)
        self.collection = self.chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        
        # Initialize Gemini if key is available
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None

    def chunk_text(self, text, max_tokens=400):
        """Simple sentence-aware chunking."""
        sentences = text.split('. ')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for sentence in sentences:
            sentence_len = len(sentence.split()) # Naive token count
            if current_length + sentence_len > max_tokens:
                chunks.append(". ".join(current_chunk) + ".")
                current_chunk = [sentence]
                current_length = sentence_len
            else:
                current_chunk.append(sentence)
                current_length += sentence_len
        
        if current_chunk:
            chunks.append(". ".join(current_chunk) + ".")
        return chunks

    def build_index(self, data_dir):
        """Load, chunk, and index documents."""
        print(f"Building index from {data_dir}...")
        for filename in os.listdir(data_dir):
            if filename.endswith(".txt"):
                path = os.path.join(data_dir, filename)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                chunks = self.chunk_text(content)
                for i, chunk_text in enumerate(chunks):
                    chunk_id = f"{filename}_{i}"
                    embedding = self.encoder.encode(chunk_text).tolist()
                    self.collection.add(
                        ids=[chunk_id],
                        embeddings=[embedding],
                        metadatas=[{"doc_name": filename, "chunk_index": i}],
                        documents=[chunk_text]
                    )
        print("Index ready.")

    def query(self, user_query, threshold=0.6, naive=False):
        """Retrieve and answer."""
        if naive:
            print("Running NAIVE prompt (no RAG)...")
            return self.call_llm(user_query, context="")

        # 1. Retrieve
        query_embedding = self.encoder.encode(user_query).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=3
        )

        # 2. Filter & Format Context
        relevant_chunks = []
        citations = []
        for i in range(len(results['ids'][0])):
            distance = results['distances'][0][i]
            # ChromaDB distances are L2; lower is better. 
            # We approximate cosine similarity here (for all-MiniLM-L6-v2, it's roughly 1 - dist/2)
            similarity = 1 - (distance / 2) 
            
            if similarity >= threshold:
                chunk_text = results['documents'][0][i]
                metadata = results['metadatas'][0][i]
                ref = f"{metadata['doc_name']}[{metadata['chunk_index']}]"
                relevant_chunks.append(f"Source: {ref}\n{chunk_text}")
                citations.append(ref)

        if not relevant_chunks:
            return f"This question is not covered in the retrieved policy documents. Retrieved chunks: None. Please contact the relevant department for guidance."

        context = "\n\n---\n\n".join(relevant_chunks)
        answer = self.call_llm(user_query, context)
        return f"{answer}\n\nCitations: {', '.join(citations)}"

    def call_llm(self, query, context):
        """Mock or call Gemini."""
        prompt = f"""
        You are a policy assistant. Use ONLY the following context to answer the user's question.
        If the answer is not in the context, say you don't know.
        
        CONTEXT:
        {context}
        
        QUESTION:
        {query}
        """
        
        if self.model:
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                return f"Error calling Gemini: {e}"
        else:
            # Fallback mock response for the workshop if no API key
            return f"[MOCK ANSWER] Based on the context provided, here is the answer to '{query}'. (Set GEMINI_API_KEY to see real AI output)"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-RAG Server")
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--query", type=str)
    parser.add_argument("--naive", action="store_true")
    args = parser.parse_args()

    server = RAGServer()
    if args.build_index:
        server.build_index("../data/policy-documents")
    elif args.query:
        print(server.query(args.query, naive=args.naive))
