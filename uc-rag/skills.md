skills:
  - name: chunk_documents
    description: >
      Loads all .txt policy documents from the data/policy-documents/ directory.
      Splits each document into chunks of a maximum of 400 tokens, using sentence
      boundary awareness — never splitting mid-sentence. Returns a list of chunk
      dicts with metadata for indexing into ChromaDB.
    input: "Path to the policy-documents directory (string)"
    output: "List of dicts: [{doc_name: str, chunk_index: int, text: str}]"
    error_handling: >
      If a file is missing or unreadable, log a warning and skip that file.
      Raise a RuntimeError if the directory itself does not exist.
      Never silently produce an empty chunk list without a warning.

  - name: retrieve_and_answer
    description: >
      Takes a natural language query string, embeds it using sentence-transformers,
      retrieves the top-3 most similar chunks from the ChromaDB collection using
      cosine similarity, filters out any chunk scoring below 0.6, and calls the
      LLM with only the retrieved chunks as context. Returns the answer along with
      a list of cited chunks (doc_name, chunk_index, score).
    input: "query (string) — the policy question from staff"
    output: >
      Dict: {
        answer: str,
        cited_chunks: [{doc_name: str, chunk_index: int, score: float}],
        refused: bool
      }
    error_handling: >
      If no chunk scores above 0.6 — set refused: true and return the refusal
      template: 'This question is not covered in the retrieved policy documents.
      Retrieved chunks: [list chunk sources]. Please contact the relevant
      department for guidance.' Never call the LLM when refused is true.
      If ChromaDB query fails — raise a RuntimeError with the original exception.
