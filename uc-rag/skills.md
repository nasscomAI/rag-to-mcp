# skills.md — UC-RAG RAG Server

skills:
  - name: chunk_documents
    description: "Load all policy documents from data/policy-documents/, split each into chunks of maximum 400 tokens respecting sentence boundaries, return list of chunks with metadata."
    input: |
      {
        "docs_dir": "string (path to data/policy-documents/)",
        "max_tokens": "integer (default 400)"
      }
    output: |
      [
        {
          "doc_name": "string (policy_hr_leave.txt)",
          "chunk_index": "integer (0, 1, 2, ...)",
          "text": "string (chunk text, max 400 tokens)"
        }
      ]
    error_handling: "If file missing or unreadable, log error and skip that document. Processing continues for remaining documents. Never fail entirely; return all successfully chunked documents."

  - name: retrieve_and_answer
    description: "Embed query using SentenceTransformer, retrieve top-3 chunks from ChromaDB by cosine similarity, filter out chunks below 0.6 threshold, call LLM with retrieved chunks as context only, return answer + cited sources."
    input: |
      {
        "query": "string (user question)",
        "collection": "ChromaDB collection",
        "embedder": "SentenceTransformer model",
        "llm_call": "callable for LLM invocation",
        "top_k": "integer (default 3)",
        "threshold": "float (default 0.6)"
      }
    output: |
      {
        "answer": "string (grounded answer or refusal template)",
        "cited_chunks": [
          {
            "doc_name": "string",
            "chunk_index": "integer",
            "score": "float (0.0-1.0 similarity)"
          }
        ],
        "is_refusal": "boolean (true if refusal template returned)"
      }
    error_handling: "If no chunk scores above 0.6 threshold, return refusal template with list of retrieved chunk sources and is_refusal=true. Do NOT make an LLM call for out-of-scope queries. If ChromaDB connection fails, raise exception immediately."
