# skills.md — UC-MCP MCP Server

skills:
  - name: query_policy_documents
    description: >
      MCP tool that answers questions about CMC policy documents by
      delegating to the RAG server. Scoped to three documents only:
      HR Leave Policy, IT Acceptable Use Policy, and Finance
      Reimbursement Policy.
    input: >
      A question string (non-empty) provided via the MCP tools/call
      request in params.arguments.question.
    output: >
      MCP-compliant result object:
        content — array with one text entry containing the answer and cited sources
        isError — false on success, true on refusal or error
    error_handling: >
      If the RAG server returns a refusal (refused=True or no chunks above
      threshold), return isError: true with a content entry containing the
      refusal message. If the RAG server raises an exception, return
      isError: true with a content entry describing the internal error.
      Never return an empty content array.

  - name: serve_mcp
    description: >
      Starts a plain HTTP server on a configurable port (default 8765)
      that handles MCP JSON-RPC 2.0 requests. Implements two methods:
      tools/list (returns available tools and their schemas) and
      tools/call (executes a tool by name with provided arguments).
    input: >
      HTTP POST requests with a JSON-RPC 2.0 body containing method,
      params, and id fields.
    output: >
      JSON-RPC 2.0 response with HTTP 200 status for all application-level
      responses. Includes jsonrpc, id, and either result or error fields.
    error_handling: >
      Unknown method returns JSON-RPC error code -32601 (Method not found).
      Malformed or unparseable JSON returns error code -32700 (Parse error).
      Missing required params returns error code -32602 (Invalid params).
      All error responses are returned with HTTP 200 — only transport-level
      failures use HTTP 4xx/5xx.
