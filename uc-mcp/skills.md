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
    description: "Queries CMC policy documents (HR, IT, Finance) using a RAG server and returns the answer with citations."
    input: "question (string): The user query about CMC policies."
    output: "A result object containing a content array with text blocks and an isError boolean."
    error_handling: "If the RAG result indicates a refusal (out of scope), returns isError: true with the refusal text."

  - name: serve_mcp
    description: "Starts a plain HTTP server that implements the MCP JSON-RPC protocol on port 8765."
    input: "JSON-RPC 2.0 requests (tools/list, tools/call) sent via HTTP POST."
    output: "JSON-RPC 2.0 compliant responses, always returning HTTP 200 for application-level results."
    error_handling: "Returns standard JSON-RPC error codes (e.g., -32601 for unknown methods)."
