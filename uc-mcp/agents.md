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
  An MCP server that operates as a policy retrieval layer, exposing RAG-based 
  document querying as a structured tool for AI agents.

intent: >
  To produce JSON-RPC compliant responses, providing a clearly scoped tool 
  description for policy retrieval and ensuring correct refusals for 
  out-of-scope queries.

context: >
  The server has access to RAG results based on CMC HR, IT, and Finance policies. 
  It must not make direct LLM calls or use outside knowledge to answer queries 
  outside this scope.

enforcement:
  - "Tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy."
  - "Tool description must state what it cannot answer: questions outside these three documents return the refusal template."
  - "inputSchema must require `question` as a non-empty string."
  - "Error responses must use `isError: true` — never return an empty content array on failure."
  - "The server must return HTTP 200 for all JSON-RPC responses including errors."
