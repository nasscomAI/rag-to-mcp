# agents.md — UC-MCP MCP Server

role: >
  An MCP server that exposes the RAG policy retrieval system as a tool
  for AI agents. The server implements JSON-RPC over plain HTTP to allow
  any MCP-compatible agent to discover and call the policy query tool.

intent: >
  The server must return JSON-RPC compliant responses with: (1) tools/list
  returning the query_policy_documents tool with scoped description, (2)
  tools/call executing queries and returning answers or refusal templates.
  All responses must use HTTP 200 with proper JSON-RPC format.

context: >
  The server has access to the RAG server (uc-rag/rag_server.py or stub_rag.py)
  for answering policy questions. It must ONLY use retrieved context from the
  RAG server — no direct LLM calls, no outside knowledge.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy"
  - "Tool description must state what it cannot answer: questions outside these three documents return the refusal template"
  - "inputSchema must require question as a non-empty string"
  - "Error responses must use isError: true — never return an empty content array on failure"
  - "The server must return HTTP 200 for all JSON-RPC responses including errors"
  - "[FILL IN: isError on failure rule]"
  - "[FILL IN: HTTP 200 for all JSON-RPC responses rule]"
