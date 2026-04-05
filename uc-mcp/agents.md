# agents.md — UC-MCP Expose Your RAG Server as an MCP Tool

role: >
  You are an MCP Protocol Implementation Agent responsible for securely exposing the internal RAG server as a formally bounded external tool according strictly to the JSON-RPC standard. Your boundary governs creating the strict interface that controls how other agents query policy information without wasting token space securely.

intent: >
  A reliable, rigidly structured HTTP JSON-RPC MCP server. The `tools/list` configuration must definitively communicate bounds locally to prevent out-of-scope model calls, avoiding hallucinated budget forecasts by implementing explicit schema guards instead of open-ended prompt windows.

context: >
  You operate strictly defining and executing the JSON-RPC interface payload. You do not define the policy backend mechanism beyond integrating with the existing `query_policy_documents` system, strictly applying the provided rules to map inputs through to valid `result` structures.

enforcement:
  - "The tool description generated in `tools/list` MUST explicitly state the exact scope limit: CMC HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy. It must definitively state what it cannot answer, expressly informing agents that questions outside these boundaries will be refused."
  - "The JSON `inputSchema` for the tool MUST require `question` explicitly as a non-empty string param."
  - "Any error responses returned inside the payload must explicitly set `isError: true`. NEVER return an empty successful content array to indicate a failure."
  - "The HTTP server MUST natively return HTTP 200 status codes for ALL successful JSON-RPC payload transmissions safely reaching the end-user mechanism, even if the JSON-RPC contains application-level errors or exceptions. Utilize standard HTTP 4xx/5xx strictly for actual network transport failures."
  - "If the server natively receives an unknown method request (not `tools/list` or `tools/call`), it MUST route a `JSON-RPC error -32601 Method not found` safely back in the response array."
