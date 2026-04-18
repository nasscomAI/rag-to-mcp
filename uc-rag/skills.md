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
    description: "Loads policy documents and splits them into sentence-aware chunks of maximum 400 tokens."
    input: "data/policy-documents/"
    output: "List of chunks with metadata {doc_name, chunk_index, text}"
    error_handling: "To prevent chunk boundary failure, chunks must not exceed 400 tokens and must split only on sentence boundaries never mid-sentence. Handle missing or unreadable files gracefully."

  - name: retrieve_and_answer
    description: "Embeds query, retrieves top-3 chunks from ChromaDB, and calls LLM with retrieved chunks as context."
    input: "query string"
    output: "answer string + list of cited chunks"
    error_handling: "Must use metadata filtering to prevent wrong chunk retrieval across documents. To prevent answering outside retrieved context, strictly ground answer to retrieved context. If no chunk scores above 0.6, return the refusal template."
