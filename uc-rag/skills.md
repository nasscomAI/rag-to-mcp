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
    description: "Loads policy documents from the filesystem and splits them into sentence-aware chunks of maximum 400 tokens."
    input: "Path to the data/policy-documents/ directory."
    output: "List of dictionaries: {doc_name, chunk_index, text}."
    error_handling: "Must prevent chunk boundary failure by ensuring cuts only occur at sentence boundaries. If files are missing, raise FileNotFoundError."

  - name: retrieve_and_answer
    description: "Retrieves the top-3 chunks using cosine similarity and generates an answer strictly grounded in the retrieved text."
    input: "User query string."
    output: "Answer string + list of cited chunks {doc_name, chunk_index}."
    error_handling: "If no chunk scores above similarity threshold 0.6, return the refusal template. Prevents context breach by grounding LLM to retrieved chunks only. Addresses wrong retrieval by ensuring metadata filtering."
