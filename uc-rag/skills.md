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
    description: >
      Processes raw text files into manageable segments for vector indexing, 
      ensuring semantic integrity by respecting sentence boundaries.
    input: "Local path to the `data/policy-documents/` directory containing .txt files."
    output: "A list of dictionaries, each containing: {doc_name, chunk_index, text}."
    error_handling: >
      If a file is missing, unreadable, or contains non-text characters, the process 
      logs a 'File Access Error' and skips the document to prevent index corruption. 
      Ensures no chunk exceeds the 400-token hard limit.

  - name: retrieve_and_answer
    description: >
      Executes the full RAG pipeline: embedding the user query, searching the ChromaDB 
      vector store, and generating a grounded response via the LLM.
    input: "User query string (e.g., 'Who approves leave without pay?')."
    output: "A grounded answer string plus a list of cited chunks (source and index)."
    error_handling: >
      If no chunks return a cosine similarity score >= 0.6, the skill triggers the 
      Refusal Template: 'This question is not covered in the retrieved policy documents. 
      Retrieved chunks: [list]. Please contact the relevant department for guidance.'