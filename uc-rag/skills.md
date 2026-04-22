# skills.md — UC-RAG RAG Server
# INSTRUCTIONS:
# 1. Open your AI tool
# 2. Paste the full contents of uc-rag/README.md
# 3. Use this prompt:
#    "Read this UC README. Generate a skills.md YAML defining the two
#     skills: chunk_documents and retrieve_and_answer. Each skill needs:
#     name, description, input, output, error_handling.
#     error_handling must address the failure modes in the README.
#     Output only valid YAML."
# 4. Paste the output below, replacing this placeholder
# 5. Verify error_handling addresses all three failure modes

skills:
  - name: chunk_documents
    description: "Loads policy documents and splits them into sentence-aware chunks."
    input: "Directory path containing .txt policy documents."
    output: "A list of dictionaries where each dictionary contains doc_name, chunk_index, and the chunk text."
    error_handling: "If the directory or files are inaccessible, the system logs the error and returns an empty list, preventing the indexer from crashing."

  - name: retrieve_and_answer
    description: "Embeds a query, retrieves the most relevant chunks from ChromaDB, and generates an answer grounded strictly in those chunks."
    input: "A natural language query string."
    output: "An answer string accompanied by a list of cited chunk metadata (document name, index, and similarity score)."
    error_handling: "If no chunks meet the similarity threshold (0.6), the system returns the standard refusal template instead of generating a fallback answer."
