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
    """
    try:
        result = rag_query(question, llm_call=call_llm)
        is_error = result.get('refused', False)
        
        content = [{
            "type": "text",
            "text": result['answer']
        }]
        
        return {
            "content": content,
            "isError": is_error
        }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Error calling RAG server: {str(e)}"
            }],
            "isError": True
        }

# ── SKILL: serve_mcp ─────────────────────────────────────────────────────────
class MCPHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler implementing JSON-RPC 2.0.
    Handles POST requests to / with JSON-RPC body.
    """

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length == 0:
            self.send_response(400)
            self.end_headers()
            return
            
        body = self.rfile.read(content_length)
        
        try:
            req = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            err_resp = {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}
            self.wfile.write(json.dumps(err_resp).encode('utf-8'))
            return
            
        req_id = req.get('id')
        method = req.get('method')
        
        response = {"jsonrpc": "2.0", "id": req_id}
        
        if method == 'tools/list':
            response['result'] = {"tools": [TOOL_DEFINITION]}
        elif method == 'tools/call':
            params = req.get('params', {})
            tool_name = params.get('name')
            
            if tool_name == 'query_policy_documents':
                args = params.get('arguments', {})
                question = args.get('question', '')
                if not question:
                    response['error'] = {"code": -32602, "message": "Invalid params: question is required"}
                else:
                    tool_result = query_policy_documents(question)
                    response['result'] = tool_result
            else:
                response['error'] = {"code": -32601, "message": "Tool not found"}
        else:
            response['error'] = {"code": -32601, "message": "Method not found"}
            
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

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
