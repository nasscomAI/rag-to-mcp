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
  An MCP server agent operating at the integration layer, responsible for exposing a policy retrieval capabilities as a standard Model Context Protocol (MCP) tool.

intent: >
  Produce a robust, standards-compliant MCP server that accurately processes JSON-RPC requests, provides a strictly scoped tool description, and enforces correct refusals for out-of-scope queries to prevent hallucination and wasted API calls.

context: >
  This server has access only to the RAG server results (stub_rag.py or rag_server.py). It does not make direct LLM calls and has no outside knowledge.

enforcement:
  - "The tool description must state the exact document scope: CMC HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy."
  - "The tool description must state what it cannot answer: questions outside these three documents return the refusal template."
  - "The inputSchema must require `question` as a non-empty string."
  - "Error responses must use `isError: true` — never return an empty content array on failure. If RAG returns refused=True, return error content with isError: true and the refusal message."
  - "The server must return HTTP 200 for all JSON-RPC responses including errors — transport errors use HTTP 4xx/5xx, application errors use JSON-RPC error objects."
