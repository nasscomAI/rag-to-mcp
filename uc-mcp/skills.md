skills:
  - name: query_policy_documents
    description: Calls the RAG server (stub_rag.py or rag_server.py) to answer questions about specific CMC policy documents.
    input: question (string)
    output: answer + cited sources within an MCP content format (content array + isError)
    error_handling: if RAG returns refused=True — return error content with isError true and the refusal message

  - name: serve_mcp
    description: Starts the HTTP server on a configurable port (default 8765), handles tools/list and tools/call requests, and returns JSON-RPC compliant responses.
    input: HTTP POST request with JSON-RPC body
    output: JSON-RPC 2.0 response, always HTTP 200 (for application operations and errors)
    error_handling: unknown method → JSON-RPC error -32601
