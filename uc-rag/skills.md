# Skills

## `chunk_documents`
- Loads all policy documents from `data/policy-documents/`
- Splits each document into chunks of maximum 400 tokens
- Splits on sentence boundaries — never mid-sentence
- Returns: list of chunks with metadata: `{doc_name, chunk_index, text}`

## `retrieve_and_answer`
- Takes a query string
- Embeds the query using sentence-transformers
- Retrieves top-3 chunks from ChromaDB by cosine similarity
- Filters out chunks scoring below 0.6
- Calls the LLM with retrieved chunks as context only
- Returns: answer + list of cited chunks
- Error handling: if no chunk scores above 0.6 — return refusal template
