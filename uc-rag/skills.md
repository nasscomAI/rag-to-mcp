skills:
  - name: chunk_documents
    description: "Loads all policy documents from data/policy-documents/, splits them into chunks, and returns the chunks with metadata."
    input: "None"
    output: "List of chunks with metadata: {doc_name, chunk_index, text}"
    error_handling: "Must strictly split on sentence boundaries and never exceed 400 tokens to prevent chunk boundary failures (e.g. splitting clauses)."

  - name: retrieve_and_answer
    description: "Takes a query string, embeds it using sentence-transformers, retrieves relevant chunks from ChromaDB, and generates an answer using the LLM restricted to the retrieved context."
    input: "Query string"
    output: "Answer string + list of cited chunks"
    error_handling: "Must filter out chunks scoring below 0.6 to prevent wrong chunk retrieval. If no chunk scores above 0.6, it must explicitly output the refusal template: 'This question is not covered in the retrieved policy documents. Retrieved chunks: [list chunk sources]. Please contact the relevant department for guidance.' to prevent answering outside the retrieved context."
