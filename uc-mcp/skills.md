# skills.md — UC-MCP MCP Server

skills:
  - name: query_policy_documents
    description: "Receives a natural language question about CMC policy documents, calls the RAG server to retrieve and answer from indexed chunks, and returns the answer in MCP content format with cited sources."
    input: "question (string) — a staff member's policy question, e.g. 'Who approves leave without pay?'"
    output: "MCP response dict: {content: [{type: 'text', text: '<answer with citations>'}], isError: false}. On refusal: {content: [{type: 'text', text: '<refusal message>'}], isError: true}."
    error_handling: "If the RAG server returns a refusal (no chunk above threshold), return the refusal message with isError: true. If the RAG server raises an exception, catch it, return a descriptive error message in content with isError: true. Never return an empty content array."

  - name: serve_mcp
    description: "Starts a plain HTTP server that listens for JSON-RPC 2.0 POST requests, dispatches tools/list and tools/call methods, and returns compliant responses. Uses Python stdlib only (http.server)."
    input: "HTTP POST request with a JSON-RPC 2.0 body on a configurable port (default 8765)."
    output: "HTTP 200 response with a JSON-RPC 2.0 body for all requests — including errors. tools/list returns the tool catalogue. tools/call returns the tool result or a JSON-RPC error object."
    error_handling: "Unknown JSON-RPC method → return JSON-RPC error code -32601 (Method not found). Malformed or unparseable JSON body → return error code -32700 (Parse error). All responses use HTTP 200; never return HTTP 4xx/5xx for application-level errors."
