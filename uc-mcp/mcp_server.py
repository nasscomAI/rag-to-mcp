"""
UC-MCP — mcp_server.py
Plain HTTP MCP Server — Starter File

Build this using your AI coding tool:
1. Share agents.md, skills.md, and uc-mcp/README.md with your AI tool
2. Ask it to implement this file following the MCP protocol
   described in the README
3. Run with: python3 mcp_server.py --port 8765
4. Test with: python3 test_client.py --port 8765

Protocol: JSON-RPC 2.0 over HTTP POST
No external dependencies beyond Python stdlib.

Methods to implement:
  tools/list  — return the tool definition for query_policy_documents
  tools/call  — execute query_policy_documents, return JSON-RPC response
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


# ── TOOL DEFINITION ──────────────────────────────────────────────────────────
# This is what the agent reads to decide when to call your tool.
# The description IS the enforcement — make it specific.
TOOL_DEFINITION = {
    "name": "query_policy_documents",
    "description": (
        "Answers questions about CMC HR Leave Policy, IT Acceptable Use "
        "Policy, and Finance Reimbursement Policy only. Returns cited "
        "answers grounded in retrieved document chunks. Returns a refusal "
        "for questions outside these three documents."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The policy question to answer",
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

    Error handling:
    - If RAG refuses (no chunks above threshold) → isError: True
    - If RAG raises exception → isError: True with error message
    """
    try:
        result = rag_query(question, llm_call=call_llm)
        if result.get('refused', False):
            return {
                "content": [{"type": "text", "text": result.get('answer', 'Refusal: request out of scope.')}],
                "isError": True
            }
        return {
            "content": [{"type": "text", "text": result.get('answer', '')}],
            "isError": False
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "isError": True
        }


# ── SKILL: serve_mcp ─────────────────────────────────────────────────────────
class MCPHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler implementing JSON-RPC 2.0.
    Handles POST requests to / with JSON-RPC body.

    Implement:
    - tools/list  → return TOOL_DEFINITION
    - tools/call  → call query_policy_documents, return result
    - unknown methods → JSON-RPC error -32601
    """

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.send_error_response(-32700, "Parse error", None)
                return
            
            body = self.rfile.read(content_length)
            try:
                req = json.loads(body)
            except json.JSONDecodeError:
                self.send_error_response(-32700, "Parse error", None)
                return
            
            req_id = req.get("id")
            if req.get("jsonrpc") != "2.0":
                self.send_error_response(-32600, "Invalid Request", req_id)
                return
                
            method = req.get("method")
            if method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [TOOL_DEFINITION]
                    }
                }
            elif method == "tools/call":
                params = req.get("params", {})
                name = params.get("name")
                if name != "query_policy_documents":
                    self.send_error_response(-32601, "Method not found", req_id)
                    return
                args = params.get("arguments", {})
                question = args.get("question")
                if not question:
                    self.send_error_response(-32602, "Invalid params", req_id)
                    return
                
                result = query_policy_documents(question)
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result
                }
            else:
                self.send_error_response(-32601, "Method not found", req_id)
                return
                
            self.send_json_response(response)
            
        except Exception as e:
            self.send_error_response(-32603, "Internal error", req.get("id") if 'req' in locals() and isinstance(req, dict) else None)

    def send_error_response(self, code, message, req_id):
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        self.send_json_response(response)
        
    def send_json_response(self, response):
        payload = json.dumps(response).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        # Suppress default HTTP logging — use print for clarity
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
