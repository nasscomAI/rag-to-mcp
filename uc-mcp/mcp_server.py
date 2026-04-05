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

from llm_adapter import call_llm

# ── TOOL DEFINITION ──────────────────────────────────────────────────────────
TOOL_DEFINITION = {
    "name": "query_policy_documents",
    "description": (
        "Answers questions exclusively pertaining to the CMC HR Leave Policy, "
        "IT Acceptable Use Policy, and Finance Reimbursement Policy. "
        "Strictly bounded to these exact three documents. It explicitly "
        "refuses to answer any questions mapping outside these parameters "
        "or concerning generic company operations."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The exact policy query string.",
            }
        },
        "required": ["question"],
    },
}

# ── SKILL: query_policy_documents ────────────────────────────────────────────
def query_policy_documents(question: str) -> dict:
    """
    Call the RAG server with the question.
    Returns MCP natively wrapped responses.
    """
    try:
        result = rag_query(question, llm_call=call_llm)
        
        # Enforce error surfacing dynamically without hiding failures in text
        if result.get("refused", False):
            return {
                "content": [{"type": "text", "text": result.get("answer", "Refusal triggered by explicit boundary filters.")}],
                "isError": True
            }
        else:
            return {
                "content": [{"type": "text", "text": result.get("answer", "Empty Success.")}],
                "isError": False
            }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Agent Internal Execution Error: {str(e)}"}],
            "isError": True
        }

# ── SKILL: serve_mcp ─────────────────────────────────────────────────────────
class MCPHandler(BaseHTTPRequestHandler):
    """
    Strict HTTP JSON-RPC router mapped dynamically.
    """
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            request = json.loads(body)
            
            req_id = request.get("id")
            method = request.get("method")
            
            if method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [TOOL_DEFINITION]
                    }
                }
            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                
                if tool_name == "query_policy_documents":
                    args = params.get("arguments", {})
                    question = args.get("question", "")
                    
                    if not question:
                        response = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32602, "message": "Invalid params: 'question' is required"}
                        }
                    else:
                        tool_result = query_policy_documents(question)
                        response = {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": tool_result
                        }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Tool not found locally: {tool_name}"}
                    }
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
                
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse internal failure"}
            }
        except Exception as e:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": f"Internal JSON-RPC Engine Failure: {str(e)}"}
            }

        # Rule Enforcement: JSON-RPC MUST emit 200 HTTP codes irrespective of App errors
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[mcp_server] {args[0]} {args[1]}")

# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UC-MCP Plain HTTP MCP Server")
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to listen on (default: 8765)")
    args = parser.parse_args()

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
