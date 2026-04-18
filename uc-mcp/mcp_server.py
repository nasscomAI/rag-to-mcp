"""
UC-MCP — mcp_server.py
Plain HTTP MCP Server implementing JSON-RPC 2.0

RICE-enforced scope:
- Tool description explicitly states document scope (CMC policies)
- Tool description states refusal behavior
- All errors use isError: true
- All responses HTTP 200

Stack: Python stdlib only (http.server, json)

Usage:
  python3 mcp_server.py --port 8765
  python3 test_client.py --port 8765
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
    from rag_server import retrieve_and_answer
    print("[mcp_server] Using participant rag_server.py")
    rag_mode = "participant"
except (ImportError, NotImplementedError, AttributeError):
    # Fall back to stub
    from stub_rag import query as rag_query
    print("[mcp_server] Using stub_rag.py (fallback)")
    rag_mode = "stub"

# Import LLM adapter
from llm_adapter import call_llm


# ══════════════════════════════════════════════════════════════════════════════
# ENFORCEMENT: Tool Description = Policy Scope + Refusal Note
# ══════════════════════════════════════════════════════════════════════════════
TOOL_DEFINITION = {
    "name": "query_policy_documents",
    "description": (
        "Answers questions about City Municipal Corporation (CMC) policy documents: "
        "HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy. "
        "Returns answers grounded in retrieved document chunks with cited sources. "
        "Questions outside these three documents return a refusal message — "
        "this tool does not answer general knowledge questions, budget forecasts, "
        "or topics not covered by the indexed CMC policy documents."
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


# ══════════════════════════════════════════════════════════════════════════════
# SKILL: query_policy_documents
# ══════════════════════════════════════════════════════════════════════════════
def query_policy_documents(question: str) -> dict:
    """
    ENFORCEMENT: Call RAG server and format response as MCP content.
    
    Returns: {"content": [{type, text}], "isError": bool}
    
    Error handling:
    - If RAG refuses (no chunks above threshold) → isError: true
    - If RAG raises exception → isError: true with error message
    """
    try:
        if rag_mode == "participant":
            # Our rag_server.py implementation
            import chromadb
            from sentence_transformers import SentenceTransformer
            
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            db_path = os.path.join(os.path.dirname(__file__), "../uc-rag/chroma_db")
            client = chromadb.PersistentClient(path=db_path)
            collection = client.get_or_create_collection("policies")
            
            result = retrieve_and_answer(question, collection, embedder)
            
            if result.get("is_refusal", False):
                return {
                    "content": [{"type": "text", "text": result["answer"]}],
                    "isError": True
                }
            else:
                return {
                    "content": [{"type": "text", "text": result["answer"]}],
                    "isError": False
                }
        else:
            # stub_rag.py implementation
            result = rag_query(question, llm_call=call_llm)
            
            if result.get("refused", False):
                return {
                    "content": [{"type": "text", "text": result.get("answer", "Refused")}],
                    "isError": True
                }
            else:
                return {
                    "content": [{"type": "text", "text": result.get("answer", "")}],
                    "isError": False
                }
    
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error querying RAG server: {str(e)}"}],
            "isError": True
        }


# ══════════════════════════════════════════════════════════════════════════════
# SKILL: serve_mcp — JSON-RPC 2.0 Handler
# ══════════════════════════════════════════════════════════════════════════════
class MCPHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler implementing JSON-RPC 2.0 over POST.
    
    Methods:
    - tools/list  → return TOOL_DEFINITION
    - tools/call  → invoke query_policy_documents
    - unknown     → JSON-RPC error -32601
    
    ENFORCEMENT: All responses HTTP 200, errors in JSON-RPC body
    """

    def do_POST(self):
        """
        Handle incoming JSON-RPC request.
        ENFORCEMENT: Always return HTTP 200 for application errors.
        """
        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self._send_json_rpc_error(None, -32700, "Parse error: empty body")
                return
            
            body = self.rfile.read(content_length).decode("utf-8")
            
            try:
                request = json.loads(body)
            except json.JSONDecodeError as e:
                self._send_json_rpc_error(None, -32700, f"Parse error: {str(e)}")
                return
            
            # Validate JSON-RPC structure
            if not isinstance(request, dict):
                self._send_json_rpc_error(None, -32700, "Parse error: not an object")
                return
            
            method = request.get("method")
            params = request.get("params")
            req_id = request.get("id")
            
            if not method:
                self._send_json_rpc_error(req_id, -32700, "Parse error: missing method")
                return
            
            # Dispatch to method
            if method == "tools/list":
                self._handle_tools_list(req_id)
            
            elif method == "tools/call":
                self._handle_tools_call(req_id, params)
            
            else:
                # Unknown method
                self._send_json_rpc_error(req_id, -32601, f"Method not found: {method}")
        
        except Exception as e:
            self._send_json_rpc_error(None, -32603, f"Internal error: {str(e)}")

    def _handle_tools_list(self, req_id):
        """
        Respond to tools/list with tool definition.
        Response format: {result: {tools: [TOOL_DEFINITION]}}
        """
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [TOOL_DEFINITION]
            }
        }
        self._send_response_json(response)

    def _handle_tools_call(self, req_id, params):
        """
        Respond to tools/call by invoking query_policy_documents.
        Response format: {result: {content: [...], isError: bool}}
        """
        if not isinstance(params, dict):
            self._send_json_rpc_error(req_id, -32602, "Invalid params: not an object")
            return
        
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name != "query_policy_documents":
            self._send_json_rpc_error(req_id, -32602, f"Unknown tool: {tool_name}")
            return
        
        if not isinstance(arguments, dict):
            self._send_json_rpc_error(req_id, -32602, "Invalid arguments: not an object")
            return
        
        question = arguments.get("question")
        if not question or not isinstance(question, str):
            self._send_json_rpc_error(req_id, -32602, "Invalid arguments: missing or invalid 'question' field")
            return
        
        # Call the skill
        result = query_policy_documents(question)
        
        # Wrap in JSON-RPC response
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }
        self._send_response_json(response)

    def _send_response_json(self, response_dict: dict):
        """Send a JSON-RPC response with HTTP 200."""
        response_json = json.dumps(response_dict)
        response_bytes = response_json.encode("utf-8")
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response_bytes))
        self.end_headers()
        self.wfile.write(response_bytes)

    def _send_json_rpc_error(self, req_id, error_code: int, error_message: str):
        """Send a JSON-RPC error response with HTTP 200."""
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": error_code,
                "message": error_message
            }
        }
        self._send_response_json(response)

    def log_message(self, format, *args):
        """Suppress default HTTP logging."""
        if len(args) > 1:
            print(f"[mcp_server] {args[1]}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="UC-MCP Plain HTTP MCP Server")
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to listen on (default: 8765)")
    args = parser.parse_args()

    # Verify stub RAG index exists
    stub_db_path = os.path.join(os.path.dirname(__file__), "../uc-rag/stub_chroma_db")
    participant_db_path = os.path.join(os.path.dirname(__file__), "../uc-rag/chroma_db")
    
    if not os.path.exists(stub_db_path) and not os.path.exists(participant_db_path):
        print("[mcp_server] WARNING: RAG index not found at either location:")
        print(f"[mcp_server]   stub: {stub_db_path}")
        print(f"[mcp_server]   participant: {participant_db_path}")
        print("[mcp_server] Build stub index: python3 ../uc-rag/stub_rag.py --build-index")
        print("[mcp_server] Or build your own: python3 ../uc-rag/rag_server.py --build-index")

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

