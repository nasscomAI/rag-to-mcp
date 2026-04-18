# Skills Definition

## query_policy_documents
- **name:** `query_policy_documents`
- **description:** Calls the backend RAG server to retrieve answers about CMC policy documents. To resolve the root cause of the failure mode identified in the README, the description exposed to agents MUST explicitly state the scope: CMC HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy. 
- **input:** `question` (string) - A non-empty string representing the user's inquiry.
- **output:** The answer to the policy question along with the cited sources.
- **error_handling:** Directly addresses the failure mode where an agent makes an out-of-scope request (e.g., asking about budget forecasts). If the query is out of scope and the RAG server returns `refused=True`, the tool must catch this and return an error content object with `isError: true` along with the specific refusal message. It must never return an empty content array on failure.

## serve_mcp
- **name:** `serve_mcp`
- **description:** Starts the MCP HTTP server on a configurable port (default 8765) to expose the policy retrieval tools. It parses and routes incoming `tools/list` and `tools/call` JSON-RPC requests.
- **input:** Configurable port number (default `8765`).
- **output:** Strictly JSON-RPC compliant responses for tool discovery and execution.
- **error_handling:** If an agent attempts to call an unknown JSON-RPC method, the server must return a JSON-RPC error with code `-32601` (Method not found). Additionally, to ensure protocol compliance, all JSON-RPC responses (including application errors) must return an HTTP 200 status code, while standard HTTP 4xx/5xx status codes are reserved exclusively for transport-level errors.
