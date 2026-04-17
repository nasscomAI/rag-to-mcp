# skills.md — UC-MCP MCP Server

skills:
  - name: query_policy_documents
    description: Answers questions about CMC policy documents by querying the RAG server. Returns answer from retrieved context or refusal template if question is not covered.
    input: question (str) - a non-empty string containing the policy question
    output: Dictionary with keys: content (list of dicts with type:text and text), isError (bool)
    error_handling: If RAG server returns refusal, return it as content. If exception occurs, return isError: true with error message.

  - name: serve_mcp
    description: Handles JSON-RPC requests over HTTP. Implements tools/list and tools/call methods. Always returns HTTP 200 with JSON-RPC 2.0 response.
    input: HTTP POST request with JSON-RPC body containing method, params, id
    output: JSON-RPC 2.0 response dict with result or error
    error_handling: Unknown method returns error code -32601, malformed JSON returns -32700, missing question returns -32602
