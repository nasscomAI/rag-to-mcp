"""
UC-MCP — mcp_server.py
Plain HTTP MCP Server — Implementation

Protocol: JSON-RPC 2.0 over HTTP POST
No external dependencies beyond Python stdlib.

Methods implemented:
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
        
        is_error = result.get("refused", False)
        message = result.get("answer", "No answer provided.")
        
        # If cited sources exist, append them to the message
        sources = result.get("sources", [])
        if sources:
            message += "\n\nSources:\n" + "\n".join(f"- {s}" for s in sources)

        return {
            "content": [{"type": "text", "text": message}],
            "isError": is_error
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Internal Error: {str(e)}"}],
            "isError": True
        }


# ── SKILL: serve_mcp ─────────────────────────────────────────────────────────
class MCPHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler implementing JSON-RPC 2.0.
    Handles POST requests to / with JSON-RPC body.
    """

    def do_POST(self):
        try:
            # 1. Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error(-32600, "Empty request body")
                return

            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self._send_error(-32700, "Parse error")
                return

            # 2. Extract JSON-RPC fields
            req_id = data.get("id")
            method = data.get("method")
            params = data.get("params", {})

            # 3. Dispatch
            if method == "tools/list":
                result = {"tools": [TOOL_DEFINITION]}
                self._send_response(result, req_id)
            
            elif method == "tools/call":
                tool_name = params.get("name")
                args = params.get("arguments", {})
                
                if tool_name == "query_policy_documents":
                    question = args.get("question")
                    if not question or not isinstance(question, str):
                        self._send_error(-32602, "Invalid params: 'question' is required as a string", req_id)
                        return
                    
                    # Execute tool
                    execution_result = query_policy_documents(question)
                    self._send_response(execution_result, req_id)
                else:
                    self._send_error(-32601, f"Tool not found: {tool_name}", req_id)
            
            else:
                self._send_error(-32601, f"Method not found: {method}", req_id)

        except Exception as e:
            print(f"[mcp_server] Error handling POST: {str(e)}")
            self._send_error(-32603, "Internal error", data.get("id") if 'data' in locals() else None)

    def _send_response(self, result, req_id):
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }
        self._write_json(response)

    def _send_error(self, code, message, req_id=None):
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        self._write_json(response)

    def _write_json(self, data):
        # Requirements: return HTTP 200 for all JSON-RPC responses including errors
        body = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Suppress default HTTP logging — use print for clarity
        print(f"[mcp_server] {args[0]} {args[1]}")


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UC-MCP Plain HTTP MCP Server")
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to listen on (default: 8765)")
    args = parser.parse_args()

    # Verify RAG index exists - check both participant and stub paths
    paths_to_check = [
        os.path.join(os.path.dirname(__file__), "../uc-rag/chroma_db"),
        os.path.join(os.path.dirname(__file__), "../uc-rag/stub_chroma_db")
    ]
    if not any(os.path.exists(p) for p in paths_to_check):
        print("[mcp_server] WARNING: RAG index not found.")
        print("[mcp_server] Run first: python3 ../uc-rag/stub_rag.py --build-index")
        print("[mcp_server] Starting anyway — queries will fail until index is built.")

    # Warm up RAG - pre-load models and connection
    print("[mcp_server] Warming up RAG backend...")
    try:
        # Dummy query to trigger model loading
        rag_query("warmup")
        print("[mcp_server] RAG context loaded.")
    except Exception as e:
        print(f"[mcp_server] Warmup failed (expected if non-critical): {str(e)}")

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
