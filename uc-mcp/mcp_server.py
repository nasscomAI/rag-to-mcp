import json
import argparse
import sys
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import RAG and LLM logic
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../uc-rag"))
try:
    from stub_rag import query as rag_query
except ImportError:
    # Fallback to a mock query if stub_rag or deps are missing
    def rag_query(question, llm_call=None):
        return {"answer": "RAG server not initialized.", "cited_chunks": [], "refused": True}

from llm_adapter import call_llm

class MCPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self.send_error_response(-32700, "Parse error")
            return

        method = request.get("method")
        req_id = request.get("id")

        if method == "tools/list":
            self.handle_tools_list(req_id)
        elif method == "tools/call":
            self.handle_tools_call(req_id, request.get("params", {}))
        else:
            self.send_error_response(-32601, "Method not found", req_id)

    def handle_tools_list(self, req_id):
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [{
                    "name": "query_policy_documents",
                    "description": (
                        "Answers questions about City Municipal Corporation (CMC) policies. "
                        "Scope: HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy. "
                        "Questions outside these documents will return a refusal message."
                    ),
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The policy question to ask."
                            }
                        },
                        "required": ["question"]
                    }
                }]
            }
        }
        self.send_json_response(response)

    def handle_tools_call(self, req_id, params):
        name = params.get("name")
        args = params.get("arguments", {})
        question = args.get("question")

        if name != "query_policy_documents":
            self.send_error_response(-32602, "Invalid tool name", req_id)
            return

        if not question or not isinstance(question, str):
            self.send_tool_call_error(req_id, "Missing or invalid 'question' argument.")
            return

        # Execute RAG
        result = rag_query(question, llm_call=call_llm)
        
        is_error = result.get("refused", False)
        content_text = result.get("answer", "No answer provided.")

        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": content_text}],
                "isError": is_error
            }
        }
        self.send_json_response(response)

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_error_response(self, code, message, req_id=None):
        error_data = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message}
        }
        self.send_json_response(error_data)

    def send_tool_call_error(self, req_id, message):
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": message}],
                "isError": True
            }
        }
        self.send_json_response(response)

def run(port):
    server_address = ('', port)
    httpd = HTTPServer(server_address, MCPHandler)
    print(f"MCP Server running on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UC-MCP Server")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    run(args.port)
