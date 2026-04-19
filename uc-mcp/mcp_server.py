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

# RAG and LLM logic will be lazy-loaded in the handler to prevent startup hangs
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
    # Lazy-load RAG logic
    rag_dir = os.path.join(os.path.dirname(__file__), "../uc-rag")
    if rag_dir not in sys.path:
        sys.path.insert(0, rag_dir)
    
    try:
        try:
            from rag_server import query as rag_query
        except (ImportError, AttributeError):
            from stub_rag import query as rag_query
            
        result = rag_query(question, llm_call=call_llm)
        is_error = result.get("refused", False)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": result.get("answer", "No answer provided.")
                }
            ],
            "isError": is_error
        }
    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error querying policy documents: {str(e)}"
                }
            ],
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
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            request = json.loads(post_data)
        except json.JSONDecodeError:
                self.send_json_rpc_error(None, -32700, "Parse error")
                return

        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "tools/list":
            self.send_json_rpc_result(request_id, {"tools": [TOOL_DEFINITION]})
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "query_policy_documents":
                question = arguments.get("question")
                if not question:
                    self.send_json_rpc_error(request_id, -32602, "Invalid params: 'question' is required")
                else:
                    result = query_policy_documents(question)
                    self.send_json_rpc_result(request_id, result)
            else:
                self.send_json_rpc_error(request_id, -32601, f"Method not found: {tool_name}")
        else:
            self.send_json_rpc_error(request_id, -32601, f"Method not found: {method}")

    def send_json_rpc_result(self, request_id, result):
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def send_json_rpc_error(self, request_id, code, message):
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message}
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode("utf-8"))

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
    db_root = os.path.join(os.path.dirname(__file__), "../uc-rag")
    participant_db = os.path.join(db_root, "chroma_db")
    stub_db = os.path.join(db_root, "stub_chroma_db")
    
    if not os.path.exists(participant_db) and not os.path.exists(stub_db):
        print("[mcp_server] WARNING: RAG index not found (neither chroma_db nor stub_chroma_db).")
        print("[mcp_server] Run first: python rag_server.py --build-index")
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
