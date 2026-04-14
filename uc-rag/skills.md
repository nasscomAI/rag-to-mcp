# skills.md — UC-RAG RAG Server

skills:
  - name: chunk_documents
    description: "Loads all policy documents from the policy-documents directory, splits each into chunks of at most 400 tokens on sentence boundaries, and stores them in ChromaDB with metadata."
    input: "Path to the policy-documents directory (e.g. ../data/policy-documents/)."
    output: "List of chunk dicts, each with: {doc_name, chunk_index, text}. Also persists chunks to the ChromaDB index for later retrieval."
    error_handling: "If a file is missing or unreadable, log the filename and skip it; continue processing remaining files. If a document produces zero valid chunks, log a warning. Never allow a mid-sentence split — if a sentence boundary cannot be found within the 400-token window, extend to the next sentence boundary."

  - name: retrieve_and_answer
    description: "Embeds the user query using sentence-transformers, retrieves the top-3 chunks from ChromaDB by cosine similarity, filters out chunks below similarity 0.6, and calls the LLM with only the retrieved chunks as context to produce a grounded answer."
    input: "A query string from a City Municipal Corporation staff member."
    output: "A dict with two fields: answer (string grounded in retrieved chunks, with document name and chunk index citations) and cited_chunks (list of {doc_name, chunk_index, score} for every chunk used)."
    error_handling: "If no retrieved chunk scores above 0.6, return the refusal template immediately without calling the LLM: 'This question is not covered in the retrieved policy documents. Retrieved chunks: [list chunk sources]. Please contact the relevant department for guidance.' Never fall back to general knowledge."
