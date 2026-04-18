# skills.md — UC-MCP MCP Server

skills:
  - name: query_policy_documents
    description: "Call the RAG server with the user's question. Return MCP-formatted response: content array with text field plus isError boolean. Handle RAG refusals and exceptions by returning isError: true with clear error message."
    input: |
      {
        "question": "string (user's policy question, non-empty)"
      }
    output: |
      {
        "content": [
          {
            "type": "text",
            "text": "string (answer or refusal message)"
          }
        ],
        "isError": "boolean (true if refusal or exception)"
      }
    error_handling: "If RAG returns refused=true (below 0.6 threshold), set isError=true and include the refusal message in text field. If RAG server raises exception, set isError=true with error description. Never return empty content array."

  - name: serve_mcp
    description: "Start an HTTP server on configurable port implementing JSON-RPC 2.0 over POST. Handle tools/list (return query_policy_documents definition) and tools/call (invoke query_policy_documents with question). Return JSON-RPC compliant responses always with HTTP 200 for application errors."
    input: |
      {
        "method": "string (tools/list or tools/call)",
        "params": "object (for tools/call: {name: string, arguments: {question: string}})",
        "id": "integer (JSON-RPC request ID)"
      }
    output: |
      HTTP 200 JSON-RPC 2.0 response:
      {
        "jsonrpc": "2.0",
        "id": "integer (same as request)",
        "result": "object or null" | "error": "object (if error)"
      }
    error_handling: "Unknown method → JSON-RPC error -32601 Method not found. Malformed request → error -32700 Parse error. Invalid params → error -32602 Invalid params. All errors returned with HTTP 200, never HTTP 5xx."
