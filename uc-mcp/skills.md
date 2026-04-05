# skills.md — UC-MCP Expose Your RAG Server as an MCP Tool

skills:
  - name: query_policy_documents
    description: Executes the internal mechanism invoking the local RAG stub while strictly wrapping and standardizing the output structure.
    input: Requires an explicit `question` (string parameter).
    output: A rigorously bounded string capturing the structured answer appended with cited source data linearly, conforming to MCP transport requirements safely.
    error_handling: Systematically flags and safely catches RAG `refused=True` states by terminating execution cleanly and surfacing the strict failure directly via the formal payload dictating `isError: true` alongside the exact refusal message text constraint.

  - name: serve_mcp
    description: Bootstraps the local HTTP server endpoint securely matching standard MCP JSON-RPC protocol guidelines dynamically routing tools globally.
    input: An explicit configurable port argument safely defaulting dynamically to 8765 if empty or omitted.
    output: Systematically catches and routes incoming `tools/list` array queries and subsequent `tools/call` requests safely via fully compliant HTTP 200 JSON-RPC structures dynamically.
    error_handling: Handles unknown HTTP method requests securely by throwing explicit formatted `JSON-RPC error -32601` mapping outputs rather than crashing out locally.
