# skills.md — UC-RAG RAG Server

skills:
  - name: chunk_documents
    description: Loads all policy documents from data/policy-documents/, splits each into chunks of maximum 400 tokens on sentence boundaries, returns list of chunks with metadata.
    input: Path to policy-documents directory (str)
    output: List of dictionaries with keys: doc_name (str), chunk_index (int), text (str), token_count (int)
    error_handling: If file not found, skip and continue. If file is empty, return empty list. Log skipped files.

  - name: retrieve_and_answer
    description: Takes a query string, embeds it using sentence-transformers, retrieves top-3 chunks from ChromaDB by cosine similarity, filters out chunks below 0.6 threshold, calls LLM with retrieved chunks as context only, returns answer with cited chunks.
    input: Query string (str)
    output: Dictionary with keys: answer (str), cited_chunks (list), sources (list of doc names)
    error_handling: If no chunk scores above 0.6, return refusal template: "This question is not covered in the retrieved policy documents. Retrieved chunks: [list]. Please contact the relevant department for guidance."
