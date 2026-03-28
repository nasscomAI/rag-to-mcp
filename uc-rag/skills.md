# skills.md — UC-RAG RAG Server

skills:
  - name: chunk_documents
    description: >
      Loads all policy documents from data/policy-documents/, splits each
      into chunks of maximum 400 tokens using sentence-boundary-aware
      splitting, and returns structured chunk objects with metadata.
    input: >
      Path to the policy-documents directory
      (data/policy-documents/).
    output: >
      List of chunk dicts, each containing:
        doc_name    — filename of the source document (e.g., policy_hr_leave.txt)
        chunk_index — integer index of the chunk within that document
        text        — the chunk text content
    error_handling: >
      If a file is missing, unreadable, or empty, log a warning with the
      filename and skip it. Continue processing remaining files. If no
      files are found, raise an error indicating the policy-documents
      directory is empty or missing.

  - name: retrieve_and_answer
    description: >
      Takes a natural-language query, embeds it using sentence-transformers,
      retrieves the top-3 most similar chunks from ChromaDB, filters by
      similarity threshold, and generates a grounded answer using only
      the retrieved context.
    input: >
      A query string (e.g., "Who approves leave without pay?").
    output: >
      A dict containing:
        answer — the generated answer text grounded in retrieved chunks
        cited_chunks — list of chunk references (doc_name, chunk_index, similarity_score)
    error_handling: >
      If no chunk scores above the 0.6 similarity threshold, return the
      refusal template: "This question is not covered in the retrieved
      policy documents. Retrieved chunks: [list chunk sources]. Please
      contact the relevant department for guidance." Do not fall back to
      general knowledge under any circumstance.
