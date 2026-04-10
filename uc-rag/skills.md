# skills.md — UC-RAG RAG Server

skills:
  - name: chunk_documents
    description: "Loads all policy documents and splits them into chunks of maximum 400 tokens, maintaining strict sentence boundaries without splitting mid-sentence."
    input: "Path to the `data/policy-documents/` directory containing the .txt policy files."
    output: "A list of chunk dictionaries, where each contains `doc_name`, `chunk_index`, and `text`."
    error_handling: "If a file is missing or unreadable, the system should log the error and skip the problematic file, ensuring the index building continues for accessible documents. To prevent Chunk Boundary Failures, splitting logic strictly enforces complete sentences rather than arbitrary token counts."

  - name: retrieve_and_answer
    description: "Takes a user query, embeds it via sentence-transformers, retrieves the top 3 chunks by cosine similarity from ChromaDB, filters by threshold, and uses an LLM to generate an answer purely based on the retrieved context."
    input: "A user query string."
    output: "A generated answer string based on the context, combined with a list of cited chunks (doc_name and chunk_index)."
    error_handling: "To prevent Wrong Chunk Retrieval and Answer Outside Context, if no chunk scores above the similarity threshold of 0.6, the skill must bypass the LLM entirely and return the exact refusal template indicating the question is not covered. Refusal template: 'This question is not covered in the retrieved policy documents. Retrieved chunks: [list chunk sources]. Please contact the relevant department for guidance.'"
