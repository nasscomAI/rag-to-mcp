role: >
  An MCP (Model Context Protocol) server over plain HTTP that exposes the UC-RAG policy retrieval functionality as a discoverable, standardized tool for AI agents.

intent: >
  To strictly enforce tool boundaries through precise tool descriptions and schemas, ensuring querying agents only call the server for supported CMC policies, and to provide correctly formatted JSON-RPC tool boundaries and responses.

context: >
  Has access only to the RAG server results via query_policy_documents — no direct LLM calls, no outside knowledge. It acts strictly as an HTTP JSON-RPC bridge out to agents.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy."
  - "Tool description must state what it cannot answer: questions outside these three documents return the refusal template."
  - "inputSchema must require `question` as a non-empty string."
  - "Error responses must use `isError: true` — never return an empty content array on failure."
  - "The server must return HTTP 200 for all JSON-RPC responses including errors — transport errors use HTTP 4xx/5xx, application errors use JSON-RPC error objects."
