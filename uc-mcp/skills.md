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
    description: "Answers questions about CMC HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy only. Returns cited answers grounded in retrieved document chunks."
    input: "question (string)"
    output: "MCP content format: {'content': [...], 'isError': bool}"
    error_handling: "Returns isError: true with a refusal message if the RAG query is out-of-scope or fails."

  - name: serve_mcp
    description: "Defines and manages an HTTP server providing an MCP-compliant JSON-RPC interface."
    input: "HTTP POST with JSON-RPC 2.0 body"
    output: "JSON-RPC 2.0 response, always HTTP 200 for application logic."
    error_handling: "Returns JSON-RPC error -32601 for unknown methods, -32700 for parse errors, and -32600 for invalid requests."
