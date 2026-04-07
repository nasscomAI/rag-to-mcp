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
    description: "Calls the RAG server to answer questions specifically about CMC policies and return cited sources."
    input: "question (string)"
    output: "MCP content format dictionary with 'content' array and 'isError' boolean flag."
    error_handling: "If the RAG server returns refused=True, returns the refusal message with `isError: true`. If an exception occurs, returns exception message with `isError: true`."

  - name: serve_mcp
    description: "Starts the JSON-RPC HTTP server, processing tools/list and tools/call."
    input: "HTTP POST request with a JSON-RPC 2.0 payload."
    output: "JSON-RPC 2.0 response, always with a HTTP 200 status code even for errors."
    error_handling: "unknown method → returns JSON-RPC error -32601; malformed request → returns JSON-RPC error -32700"
