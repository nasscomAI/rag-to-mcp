skills:
  - name: query_policy_documents
    description: >
      Accepts a natural language question string, calls the RAG server
      (rag_server.py or stub_rag.py) with that question, and formats the
      result as an MCP-compliant content response. If the RAG server returns
      refused: true (no chunk above similarity threshold), the skill returns
      isError: true with the refusal message in the content array. If the RAG
      server raises an exception, the skill returns isError: true with the
      error details.
    input: "question (string) — the policy question to answer"
    output: >
      Dict in MCP content format:
      {
        "content": [{"type": "text", "text": "<answer or refusal>"}],
        "isError": bool
      }
    error_handling: >
      - If RAG returns refused: true → isError: true, content contains refusal message.
      - If RAG raises an exception → isError: true, content contains error details.
      - Never return an empty content array. Always include a message.

  - name: serve_mcp
    description: >
      Starts a plain HTTP server on a configurable port (default 8765) that
      implements the JSON-RPC 2.0 protocol. Handles POST requests to / with a
      JSON body. Dispatches on the 'method' field: 'tools/list' returns the
      tool definition, 'tools/call' invokes query_policy_documents, and any
      unknown method returns a JSON-RPC error -32601 (Method not found).
      All JSON-RPC responses (including errors) are returned with HTTP 200.
    input: "port (int, default 8765)"
    output: "Runs indefinitely, serving JSON-RPC 2.0 responses over HTTP"
    error_handling: >
      - Unknown method → JSON-RPC error object with code -32601.
      - Malformed JSON body → JSON-RPC error object with code -32700.
      - Missing 'question' in tools/call arguments → JSON-RPC error with code -32602.
      - All errors returned as HTTP 200 with JSON-RPC error body (not HTTP 4xx).
