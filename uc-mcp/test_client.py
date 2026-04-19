"""
UC-MCP — test_client.py
Pre-built MCP test client. Do not modify.

Tests your mcp_server.py against the reference verification cases
from the UC-MCP README.

Usage:
  python3 test_client.py --port 8765
  python3 test_client.py --port 8765 --query "Who approves leave without pay?"
  python3 test_client.py --port 8765 --run-all
"""

import json
import argparse
import urllib.request
import urllib.error
import sys


def jsonrpc_call(port: int, method: str, params: dict = None, req_id: int = 1) -> dict:
    """Send a JSON-RPC request to the MCP server."""
    payload = {
        "jsonrpc": "2.0",
        "method":  method,
        "id":      req_id,
    }
    if params:
        payload["params"] = params

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(
        f"http://localhost:{port}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"[ERROR] Could not connect to server on port {port}: {e}")
        print(f"        Is the server running? Start with: python3 mcp_server.py --port {port}")
        sys.exit(1)


def print_result(label: str, result: dict, expect_error: bool = False):
    """Print a formatted test result."""
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"{'='*60}")

    if "error" in result:
        print(f"JSON-RPC Error: code={result['error'].get('code')} "
              f"message={result['error'].get('message')}")
        if expect_error:
            print("✅ PASS — expected error received")
        else:
            print("❌ FAIL — unexpected error")
        return

    res = result.get("result", {})

    # tools/list response
    if "tools" in res:
        tools = res["tools"]
        print(f"Tools returned: {len(tools)}")
        for t in tools:
            print(f"  name:        {t.get('name')}")
            print(f"  description: {t.get('description', '')[:120]}...")
            schema = t.get("inputSchema", {})
            required = schema.get("required", [])
            print(f"  required:    {required}")
        if tools and tools[0].get("name") == "query_policy_documents":
            desc = tools[0].get("description", "")
            if "CMC" in desc or "policy" in desc.lower():
                print("✅ Tool description mentions scope")
            else:
                print("⚠️  Tool description may be too vague — does it state the document scope?")
        return

    # tools/call response
    content  = res.get("content", [])
    is_error = res.get("isError", False)

    if not content:
        print("❌ FAIL — empty content array")
        return

    text = content[0].get("text", "") if content else ""
    print(f"isError: {is_error}")
    print(f"Answer:  {text[:400]}{'...' if len(text) > 400 else ''}")

    if expect_error:
        if is_error:
            print("✅ PASS — correctly refused out-of-scope question")
        else:
            print("⚠️  Expected refusal but got an answer — check tool enforcement")
    else:
        if not is_error and text:
            print("✅ PASS — got an answer")
        else:
            print("❌ FAIL — expected answer but got error or empty response")


def run_all_tests(port: int):
    """Run the full reference verification suite from the README."""
    print(f"\nRunning all reference verification tests against port {port}...")

    # Test 1 — tools/list
    result = jsonrpc_call(port, "tools/list", req_id=1)
    print_result("tools/list — discover available tools", result)

    # Test 2 — in-scope question, single document
    result = jsonrpc_call(port, "tools/call",
                          {"name": "query_policy_documents",
                           "arguments": {"question": "Who approves leave without pay?"}},
                          req_id=2)
    print_result("In-scope: 'Who approves leave without pay?'", result)

    # Test 3 — in-scope question, potential cross-doc
    result = jsonrpc_call(port, "tools/call",
                          {"name": "query_policy_documents",
                           "arguments": {"question": "Can I use my personal phone for work files from home?"}},
                          req_id=3)
    print_result("Cross-doc test: personal phone + work files", result)

    # Test 4 — out of scope → must refuse
    result = jsonrpc_call(port, "tools/call",
                          {"name": "query_policy_documents",
                           "arguments": {"question": "What is the budget forecast for 2025?"}},
                          req_id=4)
    print_result("Out-of-scope: 'What is the budget forecast for 2025?'",
                 result, expect_error=True)

    # Test 5 — unknown method → JSON-RPC -32601
    result = jsonrpc_call(port, "tools/unknown_method", req_id=5)
    print_result("Unknown method → expect JSON-RPC error -32601",
                 result, expect_error=True)

    print(f"\n{'='*60}")
    print("Reference verification complete.")
    print("Review ⚠️  warnings above — they indicate enforcement gaps.")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="UC-MCP Test Client")
    parser.add_argument("--port",    type=int, default=8765)
    parser.add_argument("--query",   type=str, help="Send a single query")
    parser.add_argument("--run-all", action="store_true",
                        help="Run full reference verification suite")
    args = parser.parse_args()

    if args.query:
        result = jsonrpc_call(args.port, "tools/call",
                              {"name": "query_policy_documents",
                               "arguments": {"question": args.query}})
        print_result(f"Query: {args.query}", result)

    elif args.run_all:
        run_all_tests(args.port)

    else:
        # Default: run all tests
        run_all_tests(args.port)


if __name__ == "__main__":
    main()
