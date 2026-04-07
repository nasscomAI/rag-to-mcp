skills:
  - name: chunk_documents
    description: "Loads all policy documents from the configured directory and splits each into chunks of maximum 400 tokens on sentence boundaries."
    input: "path to policy-documents directory"
    output: "list of chunk dicts with doc_name, chunk_index, text"
    error_handling: "If a file is unreadable, warn and skip. Fails if chunks exceed 400 tokens. Prevents chunk boundary failure by never splitting mid-sentence."

  - name: retrieve_and_answer
    description: "Embeds query, retrieves top-3 chunks from ChromaDB, filters < 0.6, and generates answer strictly from retrieved context."
    input: "query string"
    output: "answer string + list of cited chunks"
    error_handling: "Prevents wrong chunk retrieval by using metadata. Prevents context hallucination by returning the refusal template if no score > 0.6."
