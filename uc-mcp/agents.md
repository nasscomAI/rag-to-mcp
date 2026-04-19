# agents.md — UC-MCP MCP Server
# INSTRUCTIONS:
# 1. Open your AI tool
# 2. Paste the full contents of uc-mcp/README.md
# 3. Use this prompt:
#    "Read this UC README. Using the R.I.C.E framework, generate an
#     agents.md YAML with four fields: role, intent, context, enforcement.
#     The enforcement must include every rule listed under
#     'Enforcement Rules Your agents.md Must Include'.
#     Output only valid YAML."
# 4. Paste the output below, replacing this placeholder
# 5. Pay special attention to enforcement rule 1 — the tool description
#    must state exact document scope

role: >
  An MCP server that exposes policy retrieval as a tool. Operating at the Model Context Protocol layer, acting as a bridge between AI agents and the RAG server to enable standard tool discovery and execution.

intent: >
  Correctly implement an MCP server that produces JSON-RPC 2.0 compliant responses, provides a precisely scoped tool description for `query_policy_documents`, and handles out-of-scope queries with correct refusal objects and application-level error markers.

context: >
  Access to the RAG server results for specific policy documents: CMC HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy. No direct LLM calls or access to outside knowledge.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy."
  - "Tool description must state what it cannot answer: questions outside these three documents return the refusal template."
  - "inputSchema must require `question` as a non-empty string."
  - "Error responses must use `isError: true` — never return an empty content array on failure."
  - "The server must return HTTP 200 for all JSON-RPC responses including errors — transport errors use HTTP 4xx/5xx, application errors use JSON-RPC error objects."
