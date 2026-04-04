import sys
import os
import json
from io import BytesIO
from unittest.mock import MagicMock

# Add local directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import the server implementation
from mcp_server import MCPHandler, TOOL_DEFINITION

class TestableHandler(MCPHandler):
    def __init__(self, request_body):
        self.headers = {"Content-Length": str(len(request_body))}
        self.rfile = BytesIO(request_body.encode("utf-8"))
        self.output_buffer = BytesIO()
        self.sent_code = None

    def send_response(self, code, message=None):
        self.sent_code = code

    def send_header(self, keyword, value):
        pass

    def end_headers(self):
        pass

    def wfile_write(self, data):
        self.output_buffer.write(data)

    @property
    def wfile(self):
        # Return an object with a write method
        mock_wfile = MagicMock()
        mock_wfile.write = self.wfile_write
        return mock_wfile

def mock_handler(request_body):
    """Wait for handler to process a mocked POST request."""
    handler = TestableHandler(request_body)
    handler.do_POST()
    return json.loads(handler.output_buffer.getvalue().decode("utf-8"))

def test_logic():
    print("Verifying MCP server logic (Mocked Server)...")
    
    # 1. Test tools/list
    print("\n[Test 1] tools/list")
    body = json.dumps({"jsonrpc": "2.0", "method": "tools/list", "id": 1})
    resp = mock_handler(body)
    print(f"Response: {json.dumps(resp, indent=2)}")
    assert resp["result"]["tools"][0]["name"] == "query_policy_documents"
    assert "CMC HR Leave Policy" in resp["result"]["tools"][0]["description"]
    print("✅ tools/list passed")

    # 2. Test tools/call (in-scope question)
    print("\n[Test 2] tools/call (in-scope)")
    body = json.dumps({
        "jsonrpc": "2.0", 
        "method": "tools/call", 
        "params": {
            "name": "query_policy_documents",
            "arguments": {"question": "Who approves leave?"}
        },
        "id": 2
    })
    resp = mock_handler(body)
    print(f"Response: {json.dumps(resp, indent=2)}")
    # Should get the mock refusal since RAG is unreachable, but logic should hold
    assert resp["result"]["isError"] == True
    assert "RAG server not reachable" in resp["result"]["content"][0]["text"]
    print("✅ tools/call structure passed (handled unreachable RAG gracefully)")

    # 3. Test unknown method
    print("\n[Test 3] unknown method")
    body = json.dumps({"jsonrpc": "2.0", "method": "tools/unknown", "id": 3})
    resp = mock_handler(body)
    print(f"Response: {json.dumps(resp, indent=2)}")
    assert resp["error"]["code"] == -32601
    print("✅ unknown method passed")

    print("\nLogic verification complete. Protocol implementation is sound.")

if __name__ == "__main__":
    test_logic()
