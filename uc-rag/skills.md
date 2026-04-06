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
    description: "Loads all policy documents from the specified directory and splits them into chunks of maximum 400 tokens per chunk. Limits chunks strictly by sentence boundaries, never splitting mid-sentence."
    input: "Path to policy documents directory (`data/policy-documents/`)"
    output: "List of chunk dictionaries with `{doc_name, chunk_index, text}`"
    error_handling: "Raises an error if directory/file is missing. Prevents chunk boundary failures by keeping sentences whole, even if slightly below max limit."

  - name: retrieve_and_answer
    description: "Takes a query strings, embeds it via sentence-transformers, retrieves top-3 chunks from ChromaDB, filters chunks scoring below 0.6, and calls LLM providing retrieved chunks as context."
    input: "Query string"
    output: "A dictionary with answer string and list of cited chunks (doc_name and chunk_index)"
    error_handling: "Addresses answer outside context by enforcing LLM to use only retrieved context. Filters chunks scoring below 0.6 to prevent wrong chunk retrieval. Returns refusal template if no chunks meet threshold."
