"""
UC-MCP — mcp_server.py
Plain HTTP MCP Server — Full Implementation

Protocol: JSON-RPC 2.0 over HTTP POST
No external dependencies beyond Python stdlib.

Run:   python3 mcp_server.py --port 8765
Test:  python3 test_client.py --port 8765
"""

import json
import argparse
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import RAG — uses stub by default, swap to rag_server once yours works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../uc-rag"))
try:
    # Try participant's rag_server first
    from rag_server import query as rag_query
    print("[mcp_server] Using participant rag_server.py")
except (ImportError, NotImplementedError):
    # Fall back to stub
    from stub_rag import query as rag_query
    print("[mcp_server] Using stub_rag.py (fallback)")

# Import LLM adapter
from llm_adapter import call_llm


# ── TOOL DEFINITION ───────────────────────────────────────────────────────────
TOOL_DEFINITION = {
    "name": "query_policy_documents",
    "description": (
        "Answers questions about CMC HR Leave Policy, IT Acceptable Use Policy, "
        "and Finance Reimbursement Policy only. Returns cited answers grounded in "
        "retrieved document chunks, with source document name and chunk index for "
        "every claim. Returns a refusal message for questions outside these three "
        "documents — it does not answer questions about budgets, forecasts, "
        "procurement, or any topic not covered by the three policy documents."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": (
                    "The policy question to answer. Must be a non-empty string. "
                    "Only questions about CMC HR Leave Policy, IT Acceptable Use "
                    "Policy, or Finance Reimbursement Policy will receive answers."
                ),
            }
        },
        "required": ["question"],
    },
}


# ── SKILL: query_policy_documents ─────────────────────────────────────────────
def query_policy_documents(question: str) -> dict:
    """
    Call the RAG server with the question.
    Return MCP content format: {"content": [...], "isError": bool}

    Enforcement:
    - If RAG refuses (no chunks above threshold) → isError: True
    - If RAG raises exception → isError: True with error message
    - Never return empty content array
    """
    if not question or not question.strip():
        return {
            "content": [{"type": "text", "text": "Error: 'question' must be a non-empty string."}],
            "isError": True
        }

    try:
        result = rag_query(question, llm_call=call_llm)

        if result.get("refused", False):
            return {
                "content": [{"type": "text", "text": result["answer"]}],
                "isError": True
            }

        # Build response with citations
        answer = result["answer"]
        cited = result.get("cited_chunks", [])
        if cited:
            citation_lines = "\n".join(
                f"  - {c['doc_name']} (chunk {c['chunk_index']}, score: {c.get('score', 'N/A')})"
                for c in cited
            )
            full_text = f"{answer}\n\nSources:\n{citation_lines}"
        else:
            full_text = answer

        return {
            "content": [{"type": "text", "text": full_text}],
            "isError": False
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"RAG server error: {str(e)}"}],
            "isError": True
        }


# ── SKILL: serve_mcp ──────────────────────────────────────────────────────────
class MCPHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler implementing JSON-RPC 2.0.
    Handles POST requests to / with JSON-RPC body.

    Enforcement:
    - tools/list  → return TOOL_DEFINITION
    - tools/call  → call query_policy_documents, return result
    - unknown methods → JSON-RPC error -32601
    - All responses return HTTP 200 (transport errors use 4xx/5xx)
    """

    def do_POST(self):
        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_length)

        # Parse JSON
        try:
            body = json.loads(raw_body)
        except json.JSONDecodeError as e:
            self._send_json_rpc_error(
                request_id=None,
                code=-32700,
                message=f"Parse error: {str(e)}"
            )
            return

        request_id = body.get("id")
        method = body.get("method", "")
        params = body.get("params", {})

        # Dispatch
        if method == "tools/list":
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": [TOOL_DEFINITION]
                }
            }
            self._send_json(response)

        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            if tool_name != "query_policy_documents":
                self._send_json_rpc_error(
                    request_id=request_id,
                    code=-32601,
                    message=f"Method not found: tool '{tool_name}' is not registered"
                )
                return

            question = arguments.get("question", "")
            if not question or not question.strip():
                self._send_json_rpc_error(
                    request_id=request_id,
                    code=-32602,
                    message="Invalid params: 'question' is required and must be non-empty"
                )
                return

            result = query_policy_documents(question)
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            self._send_json(response)

        else:
            self._send_json_rpc_error(
                request_id=request_id,
                code=-32601,
                message=f"Method not found: '{method}'"
            )

    def _send_json(self, data: dict):
        """Send HTTP 200 with JSON body."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json_rpc_error(self, request_id, code: int, message: str):
        """Send HTTP 200 with JSON-RPC error response."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        self._send_json(response)

    def log_message(self, format, *args):
        # Suppress default HTTP logging — use print for clarity
        print(f"[mcp_server] {args[0]} {args[1]}")


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UC-MCP Plain HTTP MCP Server")
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to listen on (default: 8765)")
    args = parser.parse_args()

    # Verify RAG index exists
    db_path = os.path.join(os.path.dirname(__file__), "../uc-rag/stub_chroma_db")
    if not os.path.exists(db_path):
        print("[mcp_server] WARNING: RAG stub index not found.")
        print("[mcp_server] Run first: python3 ../uc-rag/stub_rag.py --build-index")
        print("[mcp_server] Starting anyway — queries will fail until index is built.")

    server = HTTPServer(("localhost", args.port), MCPHandler)
    print(f"[mcp_server] MCP server running on http://localhost:{args.port}")
    print(f"[mcp_server] Test with: python3 test_client.py --port {args.port}")
    print(f"[mcp_server] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[mcp_server] Stopped.")


if __name__ == "__main__":
    main()
