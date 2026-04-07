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
  An MCP server that exposes the CMC policy RAG system as a standard tool for other agents.

intent: >
  To provide JSON-RPC 2.0 compliant responses, properly scoped tool descriptions, and strict correct refusals for any questions outside the policy scope.

context: >
  This server only has access to RAG server results for the CMC HR, IT, and Finance policies. It cannot make direct LLM calls for general knowledge or answer questions outside the three policy documents.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy."
  - "Tool description must state what it cannot answer: questions outside these three documents return the refusal template."
  - "inputSchema must require `question` as a non-empty string."
  - "Error responses must use `isError: true` — never return an empty content array on failure."
  - "The server must return HTTP 200 for all JSON-RPC responses including errors — transport errors use HTTP 4xx/5xx, application errors use JSON-RPC error objects."
