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
except (ImportError, NotImplementedError, ModuleNotFoundError):
    try:
        # Fall back to stub
        from stub_rag import query as rag_query
        print("[mcp_server] Using stub_rag.py (fallback)")
    except (ImportError, NotImplementedError, ModuleNotFoundError):
        # Final fallback: local mock for testing MCP protocol without RAG
        print("[mcp_server] WARNING: RAG modules not found. Using local mock.")
        def rag_query(question, llm_call=None):
            return {
                "answer": "RAG server not reachable. Please check your workspace paths.",
                "cited_chunks": [],
                "refused": True
            }

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
                "minLength": 1,
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
        if not question or not question.strip():
            return {
                "content": [{"type": "text", "text": "Error: Question cannot be empty."}],
                "isError": True
            }

        result = rag_query(question, llm_call=call_llm)
        is_refused = result.get("refused", False)
        
        return {
            "content": [{
                "type": "text",
                "text": result.get("answer", "No answer produced.")
            }],
            "isError": is_refused
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
        """Handle JSON-RPC 2.0 requests over HTTP POST."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error(-32700, "Parse error: No content body found")
                return

            post_data = self.rfile.read(content_length)
            try:
                request = json.loads(post_data.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_error(-32700, "Parse error: Invalid JSON")
                return

            # Basic JSON-RPC validation
            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                self._send_error(-32600, "Invalid request: Must be JSON-RPC 2.0")
                return

            method = request.get("method")
            req_id = request.get("id")

            # Dispatch
            if method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [TOOL_DEFINITION]
                    }
                }
                self._send_response(response)

            elif method == "tools/call":
                params = request.get("params", {})
                tool_name = params.get("name")
                args = params.get("arguments", {})
                question = args.get("question")

                if tool_name != "query_policy_documents":
                    self._send_error(-32601, f"Tool '{tool_name}' not found", req_id)
                    return

                if not isinstance(question, str) or not question.strip():
                    # Return application error in MCP format per requirements
                    response = {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": "Error: 'question' argument is required and must be a non-empty string."}],
                            "isError": True
                        }
                    }
                    self._send_response(response)
                    return

                # Execute skill
                result = query_policy_documents(question)
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": result
                }
                self._send_response(response)

            else:
                self._send_error(-32601, "Method not found", req_id)

        except Exception as e:
            # Catch-all for unexpected server internal errors
            self._send_error(-32603, f"Internal error: {str(e)}")

    def _send_response(self, body_dict):
        """Send a standard HTTP 200 response with JSON object."""
        try:
            body = json.dumps(body_dict).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            print(f"[mcp_server] Error sending response: {e}")

    def _send_error(self, code, message, req_id=None):
        """Send a JSON-RPC error response over HTTP 200."""
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        self._send_response(response)

    def log_message(self, format, *args):
        # Suppress default HTTP logging — use print for clarity
        print(f"[mcp_server] {args[0]} {args[1]}")


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UC-MCP Plain HTTP MCP Server")
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to listen on (default: 8765)")
    args = parser.parse_args()

    # Verify RAG index exists (check rag_server's default path)
    db_path = os.path.join(os.path.dirname(__file__), "../uc-rag/chroma_db")
    if not os.path.exists(db_path):
        print("[mcp_server] WARNING: RAG index not found at " + db_path)
        print("[mcp_server] Run first: python3 ../uc-rag/rag_server.py --build-index")
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
