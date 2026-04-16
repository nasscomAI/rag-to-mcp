"""
UC-MCP — mcp_server.py
Plain HTTP MCP Server

Role    (agents.md): MCP transport layer exposing RAG as a standardised tool.
Intent  (agents.md): Scoped tool description, JSON-RPC 2.0 compliant responses,
                     isError: true on all failures, HTTP 200 always.
Skills  (skills.md): query_policy_documents, serve_mcp

Run:
    python mcp_server.py --port 8765
Test:
    python test_client.py --port 8765 --run-all

Protocol: JSON-RPC 2.0 over HTTP POST — Python stdlib only.
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
# Enforcement (agents.md rule 1 & 2): description must state exact scope
# AND what it refuses. The description IS what the agent reads to decide
# whether to call this tool — vague descriptions cause out-of-scope calls.
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
                "description": (
                    "A non-empty policy question from a CMC staff member, "
                    "e.g. 'Who approves leave without pay?' or "
                    "'Can I use my personal phone to access work files?'"
                ),
            }
        },
        "required": ["question"],   # enforcement: agents.md rule 3
    },
}


# ── SKILL: query_policy_documents ────────────────────────────────────────────
def query_policy_documents(question: str) -> dict:
    """
    Call the RAG server with the question.
    Return MCP content format: {"content": [...], "isError": bool}

    Enforcement (agents.md rules 3, 4):
    - Missing/empty question → isError: True (never reach RAG)
    - RAG refusal (refused=True) → isError: True with refusal message
    - RAG exception → isError: True with error message
    - Never return empty content array
    """
    # Validate input — agents.md rule 3
    if not question or not question.strip():
        return {
            "content": [{"type": "text", "text": "Error: 'question' must be a non-empty string."}],
            "isError": True,
        }

    try:
        result = rag_query(question.strip(), llm_call=call_llm)

        # RAG refused — no chunks above threshold
        if result.get("refused", False):
            return {
                "content": [{"type": "text", "text": result["answer"]}],
                "isError": True,   # enforcement: agents.md rule 4
            }

        # Build cited answer text
        answer_text = result["answer"]
        cited = result.get("cited_chunks", [])
        if cited:
            sources = ", ".join(
                f"{c['doc_name']} chunk {c['chunk_index']}"
                for c in cited
            )
            answer_text += f"\n\nSources: {sources}"

        return {
            "content": [{"type": "text", "text": answer_text}],
            "isError": False,
        }

    except Exception as exc:
        # Never return empty content — agents.md rule 4
        return {
            "content": [{"type": "text", "text": f"Error querying policy documents: {exc}"}],
            "isError": True,
        }


# ── JSON-RPC helpers ──────────────────────────────────────────────────────────
def _ok(req_id, result):
    return {"jsonrpc": "2.0", "id": req_id, "result": result}

def _err(req_id, code, message):
    return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}


# ── SKILL: serve_mcp (MCPHandler) ────────────────────────────────────────────
class MCPHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler implementing JSON-RPC 2.0 over HTTP POST.

    Enforcement (agents.md rule 5):
    - ALL responses use HTTP 200 — application errors go in the JSON-RPC body
    - Unknown method → error code -32601
    - Malformed JSON → error code -32700
    """

    def do_POST(self):
        # Read body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        # Parse JSON — malformed → -32700 Parse error
        try:
            rpc = json.loads(body)
        except json.JSONDecodeError:
            self._send(_err(None, -32700, "Parse error"))
            return

        req_id = rpc.get("id")
        method = rpc.get("method", "")

        # ── tools/list ────────────────────────────────────────────────────
        if method == "tools/list":
            self._send(_ok(req_id, {"tools": [TOOL_DEFINITION]}))

        # ── tools/call ────────────────────────────────────────────────────
        elif method == "tools/call":
            params = rpc.get("params", {})
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})

            if tool_name != "query_policy_documents":
                self._send(_err(req_id, -32601, f"Unknown tool: '{tool_name}'"))
                return

            question = arguments.get("question", "")
            tool_result = query_policy_documents(question)
            self._send(_ok(req_id, tool_result))

        # ── unknown method → -32601 ───────────────────────────────────────
        else:
            self._send(_err(req_id, -32601, f"Method not found: '{method}'"))

    def _send(self, payload: dict):
        """Always HTTP 200 for JSON-RPC responses — agents.md rule 5."""
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[mcp_server] {args[0]} {args[1]}")


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="UC-MCP Plain HTTP MCP Server")
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to listen on (default: 8765)")
    args = parser.parse_args()

    # Verify RAG index exists (chroma_db from rag_server, or stub_chroma_db from stub_rag)
    chroma_db = os.path.join(os.path.dirname(__file__), "../uc-rag/chroma_db")
    stub_db   = os.path.join(os.path.dirname(__file__), "../uc-rag/stub_chroma_db")
    if not os.path.exists(chroma_db) and not os.path.exists(stub_db):
        print("[mcp_server] WARNING: RAG index not found.")
        print("[mcp_server] Run first: python ../uc-rag/rag_server.py --build-index")
        print("[mcp_server] Starting anyway — queries will fail until index is built.")

    # Pre-warm the RAG embedder + ChromaDB connection before accepting requests
    # so the first tools/call doesn't time out loading the model.
    print("[mcp_server] Pre-loading RAG embedder and index (this may take a moment)...")
    try:
        rag_query("warmup", llm_call=lambda p: "")
    except Exception:
        pass  # warmup failure is non-fatal — real errors surface on actual queries
    print("[mcp_server] Ready.")

    server = HTTPServer(("localhost", args.port), MCPHandler)
    print(f"[mcp_server] MCP server running on http://localhost:{args.port}")
    print(f"[mcp_server] Test with: python test_client.py --port {args.port}")
    print(f"[mcp_server] Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[mcp_server] Stopped.")


if __name__ == "__main__":
    main()

