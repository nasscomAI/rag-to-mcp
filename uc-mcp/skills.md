skills:
  - name: query_policy_documents
    description: Executes a search and generation loop against CMC policy documents for a given question.
    input: A 'question' string.
    output: A dictionary with 'answer' and 'cited_chunks'.
    error_handling: Detects RAG refusals and returns a formatted MCP error content with isError: true.

  - name: serve_mcp
    description: Implements a plain HTTP POST handler that routes JSON-RPC methods tools/list and tools/call.
    input: Port number (default 8765).
    output: A running HTTP server responsive to JSON-RPC requests.
    error_handling: Validates method names and JSON structure, returning standard JSON-RPC error objects for invalid requests.
