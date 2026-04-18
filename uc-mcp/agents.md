# agents.md — UC-MCP MCP Server (RICE Framework)

role: >
  MCP Server exposing City Municipal Corporation policy retrieval as a
  standardized tool. Operates at the tool integration layer of the AI stack.
  Allows any agent (not just custom scripts) to query CMC policies through
  a standard JSON-RPC interface.

intent: >
  Respond to tools/list with clear tool scope and refuse-behavior documentation.
  Respond to tools/call with grounded answers from the RAG server or a
  structured refusal when out of scope. All responses are JSON-RPC 2.0 compliant.

context: >
  This server has access to:
  - RAG server results only (stub_rag.py or rag_server.py)
  - No direct LLM calls without retrieved context
  - No outside knowledge; scope strictly to CMC HR Leave, IT Acceptable Use,
    and Finance Reimbursement policies

enforcement:
  - rule: "Tool Description Scope Specification"
    description: "Tool description must explicitly state exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy. Must also state refusal behavior: 'Returns answers grounded in retrieved document chunks with cited sources. Questions outside these three documents return a refusal message — this tool does not answer general knowledge questions, budget forecasts, or topics not covered by the indexed CMC policy documents.'"
    keywords: "exact scope, document names, refusal note"
  
  - rule: "Refusal Documentation"
    description: "Tool description must state what the tool cannot answer: 'This tool will not answer general knowledge questions, budget forecasts, or any topics not covered by the indexed CMC policy documents.'"
    keywords: "what not to answer, limitations, scope boundaries"
  
  - rule: "inputSchema Required Field"
    description: "inputSchema must require 'question' as a non-empty string. The field is mandatory (in required array). Help agent validate input before calling."
    keywords: "question required, input validation, type string"
  
  - rule: "Error Responses Use isError: true"
    description: "All error conditions must use isError: true in the response, never return an empty content array. Always include a text explanation of why the request failed."
    keywords: "isError: true, error handling, explicit failure indication"
  
  - rule: "HTTP 200 for All JSON-RPC Responses"
    description: "Transport errors (malformed requests, connection failures) use HTTP 4xx/5xx. Application-level errors (unknown method, invalid params) use HTTP 200 with JSON-RPC error object. Never fail with HTTP 5xx for application errors."
    keywords: "HTTP 200, JSON-RPC error object, transport vs application errors"
