skills:
  - name: query_policy_documents
    description: "Calls the underlying RAG server with a user question and returns the retrieved answer and cited sources."
    input: "Takes: `question` (string)"
    output: "Returns: answer + cited sources"
    error_handling: "If RAG returns refused=True — return error content with `isError: true` and the refusal message."

  - name: serve_mcp
    description: "Starts a plain HTTP server that implements the MCP JSON-RPC protocol to expose tools to AI agents."
    input: "Starts the HTTP server on a configurable port (default 8765) and Handles `tools/list` and `tools/call` requests"
    output: "Returns JSON-RPC compliant responses"
    error_handling: "unknown method → JSON-RPC error -32601"
