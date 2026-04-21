"""
UC-RAG — stub_rag.py
Reference implementation aligned with agents.md / skills.md.

Delegates to rag_server.py; uses stub_chroma_db as the default index path so UC-MCP
pre-session checks (stub_chroma_db) match this CLI.

UC-MCP imports query from rag_server first, then falls back to stub_rag.query.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Same module directory as rag_server
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from rag_server import (  # noqa: E402
    TOP_K,
    SIMILARITY_THRESHOLD,
    build_index as _build_index,
    chunk_documents,
    get_embedder,
    query as _query,
    retrieve_and_answer as _retrieve_and_answer,
)

DOCS_DIR = os.path.normpath(os.path.join(_HERE, "..", "data", "policy-documents"))
DB_PATH = os.path.join(_HERE, "stub_chroma_db")


def build_index(docs_dir: str = DOCS_DIR, db_path: str = DB_PATH) -> None:
    """Build Chroma index at stub path (agents.md io_contract / UC-MCP checks)."""
    _build_index(docs_dir, db_path)


def query(question: str, llm_call=None, top_k: int = TOP_K, threshold: float = SIMILARITY_THRESHOLD):
    """UC-MCP entrypoint — uses stub_chroma_db by default."""
    return _query(
        question,
        llm_call=llm_call,
        db_path=DB_PATH,
        docs_dir=DOCS_DIR,
        top_k=top_k,
        threshold=threshold,
    )


def retrieve_and_answer(
    user_query: str,
    llm_call=None,
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
):
    """Same pipeline as rag_server.retrieve_and_answer with stub index path."""
    return _retrieve_and_answer(
        user_query,
        llm_call=llm_call,
        docs_dir=DOCS_DIR,
        db_path=DB_PATH,
        top_k=top_k,
        threshold=threshold,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="UC-RAG Stub — rag_server-backed reference")
    parser.add_argument("--build-index", action="store_true")
    parser.add_argument("--query", type=str)
    parser.add_argument("--docs-dir", type=str, default=DOCS_DIR)
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.build_index:
        build_index(args.docs_dir)

    if args.query:
        llm_call = None
        try:
            sys.path.insert(0, os.path.join(_HERE, "../uc-mcp"))
            from llm_adapter import call_llm

            llm_call = call_llm
        except Exception:
            print("[stub_rag] No LLM adapter found — returning retrieved chunks only.")

        result = query(args.query, llm_call=llm_call)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\nAnswer:\n{result['answer']}")
            if result["cited_chunks"]:
                print("\nSources:")
                for c in result["cited_chunks"]:
                    print(
                        f"  [{c['doc_name']}, chunk {c['chunk_index']}] score={c['score']}"
                    )
            if result.get("refused"):
                print("\n[REFUSED — no chunks above similarity threshold]")


if __name__ == "__main__":
    main()
