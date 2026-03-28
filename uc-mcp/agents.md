# agents.md — UC-MCP MCP Server

role: >
  MCP (Model Context Protocol) server that exposes the RAG policy retrieval
  system as a discoverable tool over plain HTTP using JSON-RPC 2.0. Operates
  at the tool-serving layer — it does not answer questions itself but
  delegates to the RAG server and returns structured, protocol-compliant
  responses.

intent: >
  Serve a single MCP tool (query_policy_documents) that any AI agent can
  discover via tools/list and invoke via tools/call. Responses must be
  JSON-RPC 2.0 compliant. The tool description must clearly communicate
  scope so agents only call it for relevant queries. Refusals and errors
  must be signalled correctly through the protocol.

context: >
  The server wraps the RAG server (rag_server.py or stub_rag.py) from
  UC-RAG. It has access to RAG query results only — it does not make
  direct LLM calls and has no knowledge outside of what the RAG server
  returns. The three policy documents in scope are: CMC HR Leave Policy,
  IT Acceptable Use Policy, and Finance Reimbursement Policy.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy. A vague description causes agents to call the tool for out-of-scope questions."
  - "Tool description must state what it cannot answer: questions outside these three policy documents will return a refusal. This prevents wasted tool calls from agents."
  - "inputSchema must require 'question' as a non-empty string. The question field is the only accepted input."
  - "Error responses must use isError: true in the result. Never return an empty content array on failure — always include a descriptive error message."
  - "The server must return HTTP 200 for all JSON-RPC responses, including application-level errors. Transport errors (malformed HTTP, etc.) use HTTP 4xx/5xx. Application errors use JSON-RPC error objects within a 200 response."
