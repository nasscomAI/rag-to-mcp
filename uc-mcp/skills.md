# Skills

### `query_policy_documents`
- **Takes:** `question` (string)
- **Action:** Calls the RAG server (stub_rag.py or rag_server.py)
- **Returns:** answer + cited sources
- **Error handling:** if RAG returns refused=True — return error content with isError: true and the refusal message

### `serve_mcp`
- **Action:** Starts the HTTP server on a configurable port (default 8765)
- **Responsibilities:** Handles `tools/list` and `tools/call` requests; Returns JSON-RPC compliant responses
- **Error handling:** unknown method → JSON-RPC error -32601
