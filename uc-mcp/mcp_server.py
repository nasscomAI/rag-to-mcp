"""
UC-MCP — mcp_server.py
Plain HTTP MCP Server

Protocol: JSON-RPC 2.0 over HTTP POST
No external dependencies beyond Python stdlib.

Methods:
  tools/list  — return the tool definition for query_policy_documents
  tools/call  — execute query_policy_documents, return JSON-RPC response

Run:  python3 mcp_server.py --port 8765
Test: python3 test_client.py --port 8765
"""

import json
import argparse
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import RAG — uses stub by default, swap to rag_server once yours works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../uc-rag"))
try:
    from rag_server import query as rag_query
    print("[mcp_server] Using participant rag_server.py")
except (ImportError, NotImplementedError):
    from stub_rag import query as rag_query
    print("[mcp_server] Using stub_rag.py (fallback)")

# Import LLM adapter
from llm_adapter import call_llm


# ── TOOL DEFINITION ──────────────────────────────────────────────────────────
TOOL_DEFINITION = {
    "name": "query_policy_documents",
    "description": (
        "Answers questions about CMC HR Leave Policy, IT Acceptable Use Policy, "
        "and Finance Reimbursement Policy only. Returns cited answers grounded in "
        "retrieved document chunks. Returns a refusal for questions outside these "
        "three documents. Do not call this tool for questions unrelated to HR leave, "
        "IT acceptable use, or finance reimbursement policies."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The policy question to answer. Must be a non-empty string.",
            }
        },
        "required": ["question"],
    },
}


# ── SKILL: query_policy_documents ────────────────────────────────────────────
def query_policy_documents(question: str) -> dict:
    """
    Call the RAG server with the question.
    Return MCP content format: {"content": [...], "isError": bool}
    """
    try:
        result = rag_query(question, llm_call=call_llm)

        if result.get("refused", False):
            return {
                "content": [{"type": "text", "text": result["answer"]}],
                "isError": True,
            }

        # Build answer text with citations
        answer_text = result["answer"]
        if result.get("cited_chunks"):
            sources = ", ".join(
                f"{c['doc_name']} chunk {c['chunk_index']}"
                for c in result["cited_chunks"]
            )
            answer_text += f"\n\nSources: {sources}"

        return {
            "content": [{"type": "text", "text": answer_text}],
            "isError": False,
        }

    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Internal error: {str(e)}"}],
            "isError": True,
        }


# ── SKILL: serve_mcp ─────────────────────────────────────────────────────────
class MCPHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler implementing JSON-RPC 2.0.
    Returns HTTP 200 for all JSON-RPC responses including errors.
    Transport errors use HTTP 4xx/5xx.
    """

    def do_POST(self):
        # Read request body
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self._send_jsonrpc_error(None, -32700, "Parse error: empty body")
            return

        try:
            raw = self.rfile.read(content_length)
            body = json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_jsonrpc_error(None, -32700, "Parse error: invalid JSON")
            return

        req_id = body.get("id")
        method = body.get("method")

        if not method:
            self._send_jsonrpc_error(req_id, -32600, "Invalid request: missing method")
            return

        # Dispatch
        if method == "tools/list":
            self._handle_tools_list(req_id)
        elif method == "tools/call":
            self._handle_tools_call(req_id, body.get("params", {}))
        else:
            self._send_jsonrpc_error(req_id, -32601, f"Method not found: {method}")

    def _handle_tools_list(self, req_id):
        """Return available tool definitions."""
        self._send_jsonrpc_result(req_id, {"tools": [TOOL_DEFINITION]})

    def _handle_tools_call(self, req_id, params):
        """Execute a tool by name."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if tool_name != "query_policy_documents":
            self._send_jsonrpc_error(
                req_id, -32602,
                f"Invalid params: unknown tool '{tool_name}'"
            )
            return

        question = arguments.get("question", "").strip()
        if not question:
            self._send_jsonrpc_error(
                req_id, -32602,
                "Invalid params: 'question' is required and must be non-empty"
            )
            return

        result = query_policy_documents(question)
        self._send_jsonrpc_result(req_id, result)

    def _send_jsonrpc_result(self, req_id, result):
        """Send a successful JSON-RPC response (HTTP 200)."""
        response = {"jsonrpc": "2.0", "id": req_id, "result": result}
        self._write_response(200, response)

    def _send_jsonrpc_error(self, req_id, code, message):
        """Send a JSON-RPC error response (HTTP 200)."""
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message},
        }
        self._write_response(200, response)

    def _write_response(self, status, body):
        """Write HTTP response with JSON body."""
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        print(f"[mcp_server] {args[0]} {args[1]}")


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UC-MCP Plain HTTP MCP Server")
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to listen on (default: 8765)")
    args = parser.parse_args()

    # Verify RAG index exists
    db_path = os.path.join(os.path.dirname(__file__), "../uc-rag/stub_chroma_db")
    if not os.path.exists(db_path):
        print("[mcp_server] WARNING: RAG index not found.")
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
