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
    from rag_server import retrieve_and_answer as rag_retrieve
    from rag_server import get_collection, get_embedder
    print("[mcp_server] Using participant rag_server.py")
    def rag_query(question, llm_call=None):
        collection = get_collection()
        embedder = get_embedder()
        return rag_retrieve(question, collection, embedder, llm_call)
except (ImportError, Exception) as e:
    # Fall back to stub
    from stub_rag import query as rag_query
    print(f"[mcp_server] Using stub_rag.py (fallback: {e})")

# Import LLM adapter
from llm_adapter import call_llm


# ── TOOL DEFINITION ──────────────────────────────────────────────────────────
# This is what the agent reads to decide when to call your tool.
# The description IS the enforcement — make it specific.
TOOL_DEFINITION = {
    "name": "query_policy_documents",
    "description": (
        "Answers questions about CMC HR Leave Policy, IT Acceptable Use Policy, "
        "and Finance Reimbursement Policy only. Returns cited answers grounded in "
        "retrieved document chunks. Returns a refusal for questions outside these three documents."
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
        
        if result.get('refused'):
            return {
                "content": [{"type": "text", "text": result['answer']}],
                "isError": True
            }
        
        return {
            "content": [{"type": "text", "text": result['answer']}],
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
            body = self.rfile.read(content_length)
            request = json.loads(body)
            
            method = request.get('method')
            request_id = request.get('id')
            
            # Handle methods
            if method == 'tools/list':
                result = {"tools": [TOOL_DEFINITION]}
            elif method == 'tools/call':
                params = request.get('params', {})
                tool_name = params.get('name')
                arguments = params.get('arguments', {})
                
                if tool_name == 'query_policy_documents':
                    question = arguments.get('question', '')
                    if not question:
                        result = {
                            "error": {
                                "code": -32602,
                                "message": "Missing required parameter: question"
                            }
                        }
                    else:
                        tool_result = query_policy_documents(question)
                        result = {"content": tool_result['content'], "isError": tool_result['isError']}
                else:
                    result = {
                        "error": {
                            "code": -32601,
                            "message": f"Unknown tool: {tool_name}"
                        }
                    }
            else:
                result = {
                    "error": {
                        "code": -32601,
                        "message": f"Unknown method: {method}"
                    }
                }
            
            response = {"jsonrpc": "2.0", "id": request_id, "result": result}
            
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
        except Exception as e:
            response = {
                "jsonrpc": "2.0",
                "id": request_id if 'request_id' in locals() else None,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

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
