- name: query_policy_documents
  description: >
    Retrieve and answer questions strictly based on CMC policy documents (HR Leave, IT Acceptable Use, 
    and Finance Reimbursement).
  input:
    question: "string (e.g., 'Who approves leave without pay?')"
  output:
    text: "Grounded answer with citations (doc name and chunk index)"
  error_handling:
    - "If the RAG server returns 'refused=True', the skill must return 'isError: true' with the standard refusal message."
    - "If the query is empty or null, provide a protocol-compliant error response."

- name: serve_mcp
  description: >
    Launch a plain HTTP server that exposes municipal tools via the Model Context Protocol (JSON-RPC 2.0).
  input:
    port: "integer (default 8765)"
  output:
    status: "HTTP 200 server running"
  error_handling:
    - "Handle 'tools/list' by returning only the defined municipal tools."
    - "Handle 'tools/call' by invoking the municipal agent and returning structured JSON content."
    - "Unknown method calls MUST return a JSON-RPC error with code -32601 (Method not found) and HTTP 200."
    - "Malformed JSON requests MUST return a JSON-RPC Parse error (-32700)."
