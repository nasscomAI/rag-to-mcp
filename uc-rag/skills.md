skills:
  - name: chunk_documents
    description: Loads policy files, splits them into semantic chunks of max 400 tokens without breaking sentences, and attaches metadata.
    input: Absolute path to the directory containing text policy documents.
    output: A list of dictionaries, each containing 'doc_name', 'chunk_index', and 'text'.
    error_handling: Logs skipped files if unreadable or missing; ensures no chunk is empty.

  - name: retrieve_and_answer
    description: Embeds a user query, retrieves relevant chunks from ChromaDB, filters by threshold, and generates a grounded response.
    input: A user's policy-related question as a string.
    output: A dictionary containing the 'answer' string and a list of 'cited_chunks'.
    error_handling: If maximum similarity score is below 0.6, returns the predefined refusal template.
