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
  An MCP server that acts as a bridge between the CMC policy RAG system and standardized
  AI agent interfaces, exposing policy retrieval as a discoverable tool.

intent: >
  Produce JSON-RPC compliant responses that expose a scoped tool description to prevent
  out-of-scope calls, ensuring correct refusals and structured error reporting.

context: >
  Access to the UC-RAG server results only; the server has no direct LLM access or
  outside knowledge and relies entirely on retrieved policy segments.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy."
  - "Tool description must state what it cannot answer: questions outside these three documents return the refusal template."
  - "inputSchema must require 'question' as a non-empty string."
  - "Error responses must use 'isError: true' — never return an empty content array on failure."
  - "The server must return HTTP 200 for all JSON-RPC responses including errors (application errors use JSON-RPC error objects)."
