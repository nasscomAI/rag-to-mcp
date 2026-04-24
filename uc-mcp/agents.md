role: >
  An MCP (Model Context Protocol) Server exposing a retrieval-augmented generation tool for CMC policy queries.

intent: >
  To strictly define the scope of the `query_policy_documents` tool to prevent agents from hallucinating or answering out-of-scope questions, and to serve standard JSON-RPC 2.0 requests over HTTP.

context: >
  The MCP server must interact exclusively through standard JSON-RPC requests for `tools/list` and `tools/call`, routing calls to the underlying RAG server.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy."
  - "Tool description must state what it cannot answer: questions outside these three documents return the refusal template."
  - "inputSchema must require `question` as a non-empty string."
  - "Error responses must use `isError: true` — never return an empty content array on failure."
  - "The server must return HTTP 200 for all JSON-RPC responses including errors — transport errors use HTTP 4xx/5xx, application errors use JSON-RPC error objects."
