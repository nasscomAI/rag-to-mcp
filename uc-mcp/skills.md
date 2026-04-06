# skills.md — UC-MCP MCP Server
# INSTRUCTIONS:
# 1. Open your AI tool
# 2. Paste the full contents of uc-mcp/README.md
# 3. Use this prompt:
#    "Read this UC README. Generate a skills.md YAML defining the two
#     skills: query_policy_documents and serve_mcp. Each skill needs:
#     name, description, input, output, error_handling.
#     error_handling must address the failure mode in the README.
#     Output only valid YAML."
# 4. Paste the output below, replacing this placeholder

skills:
  - name: query_policy_documents
    description: "Queries the CMC policy documents (HR Leave Policy, IT Acceptable Use Policy, Finance Reimbursement Policy). Returns the answer with citations. Will refuse to answer questions outside this scope."
    input: "question (string)"
    output: "MCP content format — an object containing a 'content' array and 'isError' boolean flag."
    error_handling: "If RAG returns refused=True, return error content with isError: true and the refusal message instead of raising an exception."

  - name: serve_mcp
    description: "Starts an HTTP server on a configurable port (default 8765) to handle MCP requests (tools/list, tools/call)."
    input: "HTTP POST with JSON-RPC body"
    output: "JSON-RPC 2.0 response. Always returns HTTP 200, even for errors."
    error_handling: "unknown method returns JSON-RPC error -32601; malformed request returns JSON-RPC error -32700."
