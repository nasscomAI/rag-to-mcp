role: >
  An MCP (Model Context Protocol) server operating at the integration layer that exposes policy retrieval as an external tool, allowing AI agents to discover and query the CMC policy documents securely and deterministically over a standard interface.

intent: >
  To expose a plain HTTP server that implements the `tools/list` and `tools/call` JSON-RPC methods, producing strictly JSON-RPC compliant responses, a highly-scoped tool description (`query_policy_documents`), and correct, deterministic refusals for out-of-scope inquiries.

context: >
  The server strictly has access to query results provided by the existing backend RAG server (for CMC HR, IT, and Finance policies). It cannot make direct, unrestricted LLM calls or rely on outside knowledge to answer inquiries.

enforcement:
  - "The tool description MUST explicitly state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy."
  - "The tool description MUST explicitly state what it cannot answer: any questions outside the stated three documents will return a refusal template."
  - "The inputSchema MUST require `question` as a non-empty string property."
  - "All error responses MUST use `isError: true` — never return an empty content array on failure."
  - "The server MUST return HTTP 200 for all JSON-RPC responses including errors (transport-level errors use HTTP 4xx/5xx, while application-level errors use JSON-RPC error objects)."
