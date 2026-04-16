role: >
  An MCP server operating at the integration layer that exposes semantic search and policy retrieval over CMC policies as a standard MCP tool.

intent: >
  Produces JSON-RPC 2.0 compliant responses, exposes the query_policy_documents tool with a highly specific scoped description, and returns correct refusals for out-of-scope queries.

context: >
  Has access to RAG server results only (specifically CMC HR, IT, and Finance policies). Makes no direct LLM calls and has no outside knowledge.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy."
  - "Tool description must state what it cannot answer: questions outside these three documents return the refusal template."
  - "inputSchema must require `question` as a non-empty string."
  - "Error responses must use `isError: true` — never return an empty content array on failure."
  - "The server must return HTTP 200 for all JSON-RPC responses including errors — transport errors use HTTP 4xx/5xx, application errors use JSON-RPC error objects."
