skills:
  - name: chunk_documents
    description: >
      Loads HR, IT, and Finance policy documents and splits them into searchable chunks 
      while maintaining semantic integrity.
    input: data/policy-documents/ directory
    output: A list of dictionaries containing doc_name, chunk_index, and text content.
    error_handling: >
      To fix chunk boundary failures, splitting must occur only at sentence boundaries. 
      Maximum chunk size is strictly 400 tokens to ensure context remains readable and complete.
  - name: retrieve_and_answer
    description: >
      Retrieves the most relevant policy snippets using cosine similarity and generates 
      an answer grounded strictly in the retrieved data.
    input: staff query string
    output: answer string accompanied by a list of cited chunks (doc_name and chunk_index).
    error_handling: >
      If no retrieved chunk exceeds a 0.6 similarity threshold, the system returns the 
      standardized refusal template. Answers are strictly grounded to prevent context 
      breaches and must never blend policies from different documents.
