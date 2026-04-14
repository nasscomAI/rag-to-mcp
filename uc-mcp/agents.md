role: >
  City Municipal Corporation (CMC) MCP Server responsible for exposing policy retrieval tools to external AI agents. 
  The server acts as a strictly bounded adapter for the RAG Policy Server, ensuring no queries are processed outside 
  the approved municipal documentation scope.
intent: >
  Expose a verifiable 'query_policy_documents' tool through a standard JSON-RPC interface. Success is defined by 
  accurate tool discovery via 'tools/list', grounded responses for in-scope queries, and explicit error-handling 
  (isError: true) for out-of-scope or malformed requests.
context: >
  The server utilizes context from the CMC HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy. 
  Exclusions: The server must not process budget forecasts, external legal data, or any query not addressed by the 
  three primary policy files.
enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy."
  - "Tool description must state what it cannot answer: questions outside these three documents return the refusal template."
  - "inputSchema must require 'question' as a non-empty string."
  - "Error responses must use 'isError: true' — never return an empty content array on failure."
  - "The server must return HTTP 200 for all JSON-RPC responses including errors — transport errors use HTTP 4xx/5xx, application errors use JSON-RPC error objects."
