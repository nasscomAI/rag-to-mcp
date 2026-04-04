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
    description: >
      Retrieves answers from CMC HR Leave, IT Acceptable Use, and Finance Reimbursement
      policies. Returns authoritative answers and cited sources.
    input: "question (non-empty string)"
    output: "MCP content array + isError boolean"
    error_handling: >
      If RAG refuses (out of scope), return the refusal message with isError: true.
      All failures must result in isError: true, never an empty content array.

  - name: serve_mcp
    description: >
      Hosts the MCP server on a configurable port, handling tool discovery (tools/list)
      and tool execution (tools/call) via JSON-RPC.
    input: "HTTP POST with JSON-RPC 2.0 body"
    output: "JSON-RPC 2.0 response objects, always HTTP 200"
    error_handling: >
      Unknown methods return error -32601. Malformed requests return error -32700.
      All JSON-RPC protocol responses use HTTP 200.
