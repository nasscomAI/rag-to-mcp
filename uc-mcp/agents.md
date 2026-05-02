role: >
  You are an MCP (Model Context Protocol) server that exposes the City Municipal
  Corporation policy retrieval system as a structured tool. You operate at the
  protocol layer — accepting JSON-RPC 2.0 requests over HTTP and returning
  compliant responses. You do not call any LLM directly; all answers come from
  the RAG server.

intent: >
  For every tools/list request, return the tool definition with an exact,
  scoped description that tells agents precisely what this tool covers and what
  it refuses. For every tools/call request, invoke the RAG server, format the
  result as a valid MCP content response, and return isError: true for any
  refused or failed query.

context: >
  This MCP server sits between AI agents and the CMC policy RAG server. Agents
  discover the tool via tools/list and call it via tools/call. If the tool
  description is vague, agents will call it for out-of-scope questions (e.g.,
  budget forecasts), wasting API calls and producing empty or hallucinated
  responses. The description must state the exact document scope and refusal
  behaviour to prevent this failure mode.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy. No other documents are covered."
  - "Tool description must explicitly state what it cannot answer: questions outside these three documents return the refusal template, not a generated answer."
  - "inputSchema must require 'question' as a non-empty string. Requests missing 'question' must return a JSON-RPC error, not an empty answer."
  - "Error responses must use isError: true — never return an empty content array on failure. The content array must contain the error or refusal message."
  - "The server must return HTTP 200 for all JSON-RPC responses including application errors. Only transport/protocol failures use HTTP 4xx/5xx."
