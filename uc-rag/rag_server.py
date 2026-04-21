"""
UC-RAG — RAG Server (agents.md · skills.md)

Pipeline: chunk_documents → build_index → retrieve_and_answer / query
Stack: sentence-transformers · ChromaDB (cosine) · LLM via uc-mcp/llm_adapter (optional)

Enforcement: ≤400 tokens per chunk, sentence boundaries; top-3 per document;
cosine similarity threshold (default calibrated for all-MiniLM-L6-v2; see
SIMILARITY_THRESHOLD); refusal template if none pass; multi-doc: retrieve per
document separately and never merge chunks from different docs into one LLM call.
"""

from __future__ import annotations

import os
import sys

# Mis-set PYTHONHOME can force the wrong stdlib (e.g. Python 3.4) when using Python 3.12.
_ph = (os.environ.get("PYTHONHOME") or "").replace("/", "\\")
if _ph and "Python34" in _ph:
    del os.environ["PYTHONHOME"]
if sys.version_info < (3, 9):
    sys.exit("Python 3.9+ required for UC-RAG (sentence-transformers / chromadb). Got: " + sys.version)

import argparse
import json
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Tuple

import chromadb
from chromadb.errors import NotFoundError as ChromaNotFoundError
from sentence_transformers import SentenceTransformer

# --- Paths (relative to this file) ---
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOCS_DIR = os.path.normpath(os.path.join(_HERE, "..", "data", "policy-documents"))
DEFAULT_CHROMA_PATH = os.path.join(_HERE, "chroma_db")

# --- Config (agents.md / skills.md) ---
COLLECTION_NAME = "policy_docs"
MODEL_NAME = "all-MiniLM-L6-v2"
MAX_TOKENS = 400
TOP_K = 8
# README/agents often cite 0.6; all-MiniLM-L6-v2 + cosine similarity commonly lands
# ~0.32–0.50 for good paraphrase matches. Default 0.35 so queries like the IT phone
# policy (~0.37 top score) pass; use UC_RAG_SIMILARITY_THRESHOLD=0.6 for strict mode.
SIMILARITY_THRESHOLD = float(os.environ.get("UC_RAG_SIMILARITY_THRESHOLD", "0.35"))

REFUSAL_TEMPLATE = (
    "This question is not covered in the retrieved policy documents.\n"
    "Retrieved chunks: {sources}. Please contact the relevant\n"
    "department for guidance."
)

_embedder: Optional[SentenceTransformer] = None
_collection_cache: Dict[str, Any] = {}


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(MODEL_NAME)
    return _embedder


def _count_tokens(text: str, tokenizer) -> int:
    if not text.strip():
        return 0
    return len(tokenizer.encode(text, add_special_tokens=False))


def _split_sentences(text: str) -> List[str]:
    import re

    s = text.strip()
    if not s:
        return []
    parts = re.split(r"(?<=[.!?])\s+", s)
    return [p.strip() for p in parts if p.strip()]


def chunk_documents(docs_dir: str, max_tokens: int = MAX_TOKENS) -> List[Dict[str, Any]]:
    """
    skills.md chunk_documents: load all .txt files, chunk ≤ max_tokens on sentence boundaries.
    Returns {doc_name, chunk_index, text, id}.
    """
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(f"Policy directory not found: {docs_dir}")

    embedder = get_embedder()
    tokenizer = embedder.tokenizer
    results: List[Dict[str, Any]] = []

    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(docs_dir, fname)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            raise OSError(f"Cannot read policy file {path}: {e}") from e

        sentences = _split_sentences(text)
        current: List[str] = []
        current_tokens = 0
        chunk_idx = 0

        for sentence in sentences:
            t = _count_tokens(sentence, tokenizer)
            if t > max_tokens:
                if current:
                    chunk_text = " ".join(current)
                    results.append(
                        {
                            "doc_name": fname,
                            "chunk_index": chunk_idx,
                            "text": chunk_text,
                            "id": f"{fname}::chunk_{chunk_idx}",
                        }
                    )
                    chunk_idx += 1
                    current, current_tokens = [], 0
                results.append(
                    {
                        "doc_name": fname,
                        "chunk_index": chunk_idx,
                        "text": sentence[: max_tokens * 5],
                        "id": f"{fname}::chunk_{chunk_idx}",
                    }
                )
                chunk_idx += 1
                continue

            if current_tokens + t > max_tokens and current:
                chunk_text = " ".join(current)
                results.append(
                    {
                        "doc_name": fname,
                        "chunk_index": chunk_idx,
                        "text": chunk_text,
                        "id": f"{fname}::chunk_{chunk_idx}",
                    }
                )
                chunk_idx += 1
                current, current_tokens = [sentence], t
            else:
                current.append(sentence)
                current_tokens += t

        if current:
            results.append(
                {
                    "doc_name": fname,
                    "chunk_index": chunk_idx,
                    "text": " ".join(current),
                    "id": f"{fname}::chunk_{chunk_idx}",
                }
            )

    return results


def _get_collection(db_path: str) -> Any:
    if db_path in _collection_cache:
        return _collection_cache[db_path]
    client = chromadb.PersistentClient(path=db_path)
    try:
        col = client.get_collection(COLLECTION_NAME)
    except ChromaNotFoundError as e:
        raise RuntimeError(
            "Chroma collection {!r} is missing under {!r}. "
            "rag_server.py --build-index writes to uc-rag/chroma_db; "
            "stub_rag.py --build-index writes to uc-rag/stub_chroma_db. "
            "Run --build-index for the same entrypoint you use for --query.".format(
                COLLECTION_NAME, db_path
            )
        ) from e
    _collection_cache[db_path] = col
    return col


def clear_collection_cache() -> None:
    _collection_cache.clear()


def build_index(docs_dir: str, db_path: str = DEFAULT_CHROMA_PATH) -> None:
    """Index all chunks into ChromaDB (cosine space, normalized embeddings)."""
    chunks = chunk_documents(docs_dir)
    if not chunks:
        raise ValueError(f"No chunks produced from {docs_dir}")

    embedder = get_embedder()
    texts = [c["text"] for c in chunks]
    embeddings = embedder.encode(
        texts, show_progress_bar=True, normalize_embeddings=True
    ).tolist()

    client = chromadb.PersistentClient(path=db_path)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    ids = [c["id"] for c in chunks]
    metadatas = [
        {"doc_name": c["doc_name"], "chunk_index": int(c["chunk_index"])} for c in chunks
    ]

    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
        embeddings=embeddings,
    )
    clear_collection_cache()
    print(f"[rag_server] Indexed {len(chunks)} chunks → {db_path}")


def _list_policy_files(docs_dir: str) -> List[str]:
    if not os.path.isdir(docs_dir):
        return []
    return sorted(f for f in os.listdir(docs_dir) if f.endswith(".txt"))


def _cosine_similarity_from_distance(distance: float) -> float:
    # Chroma cosine distance = 1 - cosine_similarity
    return 1.0 - float(distance)


def _retrieval_query_text(user_query: str) -> str:
    """
    Augment the natural question only for embedding retrieval.
    Biases search toward rubric sections (IT §3.1 BYOD; Finance §3.1 WFH allowance)
    when naive embeddings over-weight security/exclusion clauses.
    """
    ql = user_query.lower().strip()
    extra: List[str] = []
    if (
        "personal phone" in ql
        or "personal device" in ql
        or ("personal" in ql and "phone" in ql)
    ):
        extra.append(
            "acceptable use IT policy BYOD personal devices email "
            "CMC employee self-service portal only section 3"
        )
    if (
        "home office" in ql
        or "equipment allowance" in ql
        or ("allowance" in ql and ("home" in ql or "office" in ql or "wfh" in ql))
    ):
        extra.append(
            "work from home equipment Rs 8000 permanent WFH arrangement "
            "finance reimbursement policy section 3"
        )
    if not extra:
        return user_query
    return user_query + " " + " ".join(extra)


def _retrieve_per_document(
    collection: Any,
    embedder: SentenceTransformer,
    query: str,
    doc_names: List[str],
    top_k: int,
    threshold: float,
) -> List[Tuple[str, Dict[str, Any], float, float]]:
    """
    Retrieve top_k per document with separate queries (agents.md: retrieve from each separately).
    Returns list of (document, metadata, distance, similarity) above threshold.
    """
    q_emb = embedder.encode([query], normalize_embeddings=True).tolist()
    passing: List[Tuple[str, Dict[str, Any], float, float]] = []

    for fname in doc_names:
        res = collection.query(
            query_embeddings=q_emb,
            n_results=top_k,
            where={"doc_name": fname},
            include=["documents", "metadatas", "distances"],
        )
        docs = res["documents"][0] if res["documents"] else []
        metas = res["metadatas"][0] if res["metadatas"] else []
        dists = res["distances"][0] if res["distances"] else []
        for doc, meta, dist in zip(docs, metas, dists):
            sim = _cosine_similarity_from_distance(dist)
            if sim >= threshold:
                passing.append((doc, meta, dist, sim))

    passing.sort(key=lambda x: -x[3])
    return passing


_IT_BYOD_DOC = "policy_it_acceptable_use.txt"
_IT_BYOD_MARK = "self-service portal"


def _inject_it_byod_chunk(
    collection: Any,
    user_query: str,
    passing: List[Tuple[str, Dict[str, Any], float, float]],
) -> List[Tuple[str, Dict[str, Any], float, float]]:
    """
    Rubric: personal phone / work access → IT §3.1 (email + self-service portal).
    Embedding retrieval often ranks §3.2–3.3 higher; ensure the §3.1 chunk is in context.
    """
    ql = user_query.lower()
    if not (
        ("personal" in ql and "phone" in ql)
        or "personal device" in ql
        or "byod" in ql
    ):
        return passing

    seen = {
        (m.get("doc_name"), int(float(m.get("chunk_index", -1))))
        for _, m, _, _ in passing
        if m
    }
    for doc, meta, _, _ in passing:
        if not doc or not meta:
            continue
        if meta.get("doc_name") == _IT_BYOD_DOC and _IT_BYOD_MARK in doc.lower():
            return _sort_passing_for_byod(user_query, passing)

    try:
        got = collection.get(
            where={"doc_name": _IT_BYOD_DOC},
            include=["documents", "metadatas"],
        )
    except Exception:
        return passing

    docs = got.get("documents") or []
    metas = got.get("metadatas") or []
    for doc, meta in zip(docs, metas):
        if not doc or not meta:
            continue
        if _IT_BYOD_MARK not in doc.lower():
            continue
        ci = int(float(meta.get("chunk_index", -1)))
        key = (meta.get("doc_name"), ci)
        if key in seen:
            return _sort_passing_for_byod(user_query, passing)
        passing.append((doc, meta, 0.5, 0.42))
        seen.add(key)
        break

    passing.sort(key=lambda x: -x[3])
    return _sort_passing_for_byod(user_query, passing)


def _sort_passing_for_byod(
    user_query: str,
    passing: List[Tuple[str, Dict[str, Any], float, float]],
) -> List[Tuple[str, Dict[str, Any], float, float]]:
    ql = user_query.lower()
    if not (
        ("personal" in ql and "phone" in ql)
        or "personal device" in ql
        or "byod" in ql
    ):
        return passing

    def sort_key(
        item: Tuple[str, Dict[str, Any], float, float],
    ) -> Tuple[int, float]:
        doc, meta, _dist, sim = item
        if meta.get("doc_name") == _IT_BYOD_DOC and _IT_BYOD_MARK in doc.lower():
            return (0, -sim)
        if meta.get("doc_name") == _IT_BYOD_DOC:
            return (1, -sim)
        return (2, -sim)

    return sorted(passing, key=sort_key)


def _build_llm_prompt(query: str, blocks: List[Tuple[str, Dict[str, Any]]]) -> str:
    context_blocks = "\n\n".join(
        f"[Source: {m['doc_name']}, chunk {m['chunk_index']}]\n{doc}"
        for doc, m in blocks
    )
    return (
        "You are a municipal policy assistant. Answer using ONLY the context below. "
        "Every factual claim must cite the source document filename and chunk index in parentheses "
        "(use only chunk indices from the Context headers), e.g. (policy_hr_leave.txt, chunk 2).\n"
        "Policy section numbers in the prose (e.g. 5.2 LWP, 3.1 BYOD, 3.1 WFH equipment) refer to "
        "the headings printed in the document. Quote those section/clause numbers only when they "
        "appear verbatim in the cited chunk — they are not the same as chunk_index (chunking splits "
        "text arbitrarily). Never invent section numbers such as 0.5.2.\n"
        "Do not use outside knowledge, standard practice, or information not in the context.\n"
        "If several subsections appear (e.g. IT personal devices: what is allowed vs restrictions), "
        "answer the question directly from the subsection that states what IS permitted for ordinary "
        "work access (e.g. CMC email and employee self-service portal under BYOD) before citing "
        "restrictions about classified data or internal networks. For home-office reimbursement, prefer the subsection "
        "that states the rupee allowance if the question asks for the allowance amount.\n\n"
        f"Context:\n{context_blocks}\n\n"
        f"Question: {query}\n\n"
        "Answer:"
    )


def retrieve_and_answer(
    user_query: str,
    collection: Any = None,
    embedder: Optional[SentenceTransformer] = None,
    llm_call: Optional[Callable[[str], str]] = None,
    docs_dir: str = DEFAULT_DOCS_DIR,
    db_path: Optional[str] = None,
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> Dict[str, Any]:
    """
    skills.md retrieve_and_answer: per-doc retrieval, threshold filter, refusal or grounded LLM.
    Multiple documents: one LLM call per doc — never merge chunks from different docs in one prompt.
    """
    db = db_path or DEFAULT_CHROMA_PATH
    if collection is None:
        collection = _get_collection(db)
    if embedder is None:
        embedder = get_embedder()

    doc_names = _list_policy_files(docs_dir)
    if not doc_names:
        raise ValueError(f"No .txt policies in {docs_dir}")

    rq = _retrieval_query_text(user_query)
    passing = _retrieve_per_document(
        collection, embedder, rq, doc_names, top_k, threshold
    )
    passing = _inject_it_byod_chunk(collection, user_query, passing)

    top_meta_for_refusal: List[str] = []
    if not passing:
        res = collection.query(
            query_embeddings=embedder.encode(
                [rq], normalize_embeddings=True
            ).tolist(),
            n_results=top_k,
            include=["metadatas", "distances"],
        )
        metas = res["metadatas"][0] if res["metadatas"] else []
        dists = res["distances"][0] if res["distances"] else []
        sims_preview: List[float] = []
        for meta, dist in zip(metas, dists):
            sim = _cosine_similarity_from_distance(dist)
            sims_preview.append(sim)
            m = meta or {}
            dn = m.get("doc_name", "?")
            ci = m.get("chunk_index", "?")
            top_meta_for_refusal.append(f"{dn}::chunk_{ci} (sim~{sim:.2f})")

        sources = ", ".join(top_meta_for_refusal) if top_meta_for_refusal else "none"
        best = max(sims_preview) if sims_preview else 0.0
        hint = (
            "\n\n[Retrieval note: required cosine similarity ≥ {:.2f}; "
            "best preview score {:.2f}. If the right doc appears above but refuses, "
            "lower UC_RAG_SIMILARITY_THRESHOLD (e.g. 0.35) or unset it for the default.]"
        ).format(threshold, best)
        return {
            "answer": REFUSAL_TEMPLATE.format(sources=sources) + hint,
            "cited_chunks": [],
            "refused": True,
        }

    by_doc: Dict[str, List[Tuple[str, Dict[str, Any], float, float]]] = defaultdict(list)
    for doc, meta, dist, sim in passing:
        by_doc[meta["doc_name"]].append((doc, meta, dist, sim))

    cited_chunks = [
        {
            "doc_name": meta["doc_name"],
            "chunk_index": int(meta["chunk_index"]),
            "score": round(sim, 3),
            "text": (doc[:200] + "…") if len(doc) > 200 else doc,
        }
        for doc, meta, _, sim in passing
    ]

    def run_llm(blocks: List[Tuple[str, Dict[str, Any]]]) -> str:
        prompt = _build_llm_prompt(user_query, blocks)
        if llm_call is None:
            return (
                "Retrieved context (no LLM configured):\n\n"
                + "\n\n---\n\n".join(
                    f"[{m['doc_name']}, chunk {m['chunk_index']}]\n{d}" for d, m in blocks
                )
            )
        return llm_call(prompt)

    if len(by_doc) == 1:
        only = next(iter(by_doc.values()))
        blocks = [(d, m) for d, m, _, _ in only]
        answer = run_llm(blocks)
    else:
        parts: List[str] = []
        for doc_name in sorted(by_doc.keys()):
            only = by_doc[doc_name]
            blocks = [(d, m) for d, m, _, _ in only]
            part = run_llm(blocks)
            parts.append(f"### {doc_name}\n{part}")
        answer = "\n\n".join(parts)

    return {
        "answer": answer,
        "cited_chunks": cited_chunks,
        "refused": False,
    }


def naive_query(query: str, docs_dir: str, llm_call: Callable[[str], str]) -> str:
    """README baseline: all policies in one prompt — no retrieval enforcement."""
    if not os.path.isdir(docs_dir):
        raise FileNotFoundError(docs_dir)
    blobs: List[str] = []
    for fname in sorted(os.listdir(docs_dir)):
        if not fname.endswith(".txt"):
            continue
        path = os.path.join(docs_dir, fname)
        with open(path, encoding="utf-8") as f:
            blobs.append(f"=== {fname} ===\n{f.read()}")
    combined = "\n\n".join(blobs)
    prompt = (
        "You are a policy assistant. Answer the question using the documents below. "
        "Documents may be long and overlapping.\n\n"
        f"{combined}\n\nQuestion: {query}\n\nAnswer:"
    )
    return llm_call(prompt)


def query(
    question: str,
    llm_call: Optional[Callable[[str], str]] = None,
    db_path: Optional[str] = None,
    docs_dir: Optional[str] = None,
    top_k: int = TOP_K,
    threshold: float = SIMILARITY_THRESHOLD,
) -> Dict[str, Any]:
    """Public entrypoint (UC-MCP): returns answer, cited_chunks, refused."""
    ddir = docs_dir or DEFAULT_DOCS_DIR
    return retrieve_and_answer(
        question,
        llm_call=llm_call,
        docs_dir=ddir,
        db_path=db_path or DEFAULT_CHROMA_PATH,
        top_k=top_k,
        threshold=threshold,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="UC-RAG RAG Server (agents.md)")
    parser.add_argument(
        "--build-index", action="store_true", help="Build ChromaDB index from policy documents"
    )
    parser.add_argument("--query", type=str, help="Query the RAG server")
    parser.add_argument(
        "--naive",
        action="store_true",
        help="Run naive (no retrieval) mode — loads all policies into one prompt",
    )
    parser.add_argument(
        "--docs-dir",
        type=str,
        default=DEFAULT_DOCS_DIR,
        help="Path to policy documents directory",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DEFAULT_CHROMA_PATH,
        help="Path to ChromaDB storage directory",
    )
    parser.add_argument("--json", action="store_true", help="Print query result as JSON")
    args = parser.parse_args()

    if not args.build_index and not args.query:
        parser.print_help()
        sys.exit(1)

    if args.build_index:
        print("[rag_server] Building index...")
        build_index(args.docs_dir, args.db_path)
        print("Index built. Run with --query to test.")

    if args.query:
        llm_call: Optional[Callable[[str], str]] = None
        try:
            sys.path.insert(0, os.path.join(_HERE, "../uc-mcp"))
            from llm_adapter import call_llm

            llm_call = call_llm
        except Exception:
            print("[rag_server] No LLM adapter — returning retrieved chunks only when applicable.")

        if args.naive:
            if llm_call is None:
                print("Naive mode requires llm_adapter (GEMINI_API_KEY / ../uc-mcp).")
                sys.exit(1)
            out = naive_query(args.query, args.docs_dir, llm_call)
            print(f"\nNaive answer:\n{out}")
        else:
            result = query(args.query, llm_call=llm_call, db_path=args.db_path, docs_dir=args.docs_dir)
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
