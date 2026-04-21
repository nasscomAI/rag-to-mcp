"""
README reference verification (agents.md reference_verification).

Runs the four rubric queries through rag_server.query and applies lightweight checks.
Requires a built Chroma index (rag_server.py --build-index or stub_rag.py --build-index).

Usage:
  set GEMINI_API_KEY=...   (recommended for answer-quality checks)
  python verify_reference_queries.py
  python verify_reference_queries.py --db-path chroma_db
"""

from __future__ import annotations

import argparse
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from rag_server import DEFAULT_CHROMA_PATH, query  # noqa: E402

# Load LLM if available (uc-mcp)
_llm = None


def _load_llm():
    global _llm
    if _llm is not None:
        return _llm
    try:
        sys.path.insert(0, os.path.join(_HERE, "../uc-mcp"))
        from llm_adapter import call_llm

        _llm = call_llm
    except Exception:
        _llm = None
    return _llm


def _norm(s: str) -> str:
    return s.lower()


def check_leave_without_pay(result: dict) -> tuple[bool, str]:
    a = _norm(result.get("answer", ""))
    if result.get("refused"):
        return False, "expected answer paths, got refusal"
    ok = "department head" in a and "hr director" in a
    return ok, "need Department Head + HR Director in answer" if not ok else "ok"


def check_personal_phone(result: dict) -> tuple[bool, str]:
    a = _norm(result.get("answer", ""))
    cites = result.get("cited_chunks") or []
    it_touch = any("policy_it" in _norm(str(c.get("doc_name", ""))) for c in cites)
    hr_touch = any("policy_hr" in _norm(str(c.get("doc_name", ""))) for c in cites)
    portal_ok = "email" in a and ("self-service" in a or "self service" in a or "portal" in a)
    no_hr_blend = not hr_touch  # retrieval must not lean on HR for this IT question
    if result.get("refused"):
        return False, "expected grounded IT answer, got refusal (try UC_RAG_SIMILARITY_THRESHOLD=0.35)"
    ok = portal_ok and it_touch and no_hr_blend
    if not ok:
        parts = []
        if not portal_ok:
            parts.append("mention email + self-service/portal")
        if not it_touch:
            parts.append("cite policy_it chunk in sources")
        if not no_hr_blend:
            parts.append("avoid HR-only retrieval for IT question")
        return False, "; ".join(parts) or "check answer"
    return True, "ok"


def check_flexible_culture(result: dict) -> tuple[bool, str]:
    a = _norm(result.get("answer", ""))
    refused = result.get("refused")
    template_ok = "not covered" in a or "retrieved policy" in a
    if refused or template_ok:
        return True, "ok (refusal/template)"
    return False, "expected refusal or not-covered template"


def check_home_office_allowance(result: dict) -> tuple[bool, str]:
    a = result.get("answer", "")
    an = _norm(a)
    if result.get("refused"):
        return False, "expected finance-backed answer, got refusal"
    # Match "8000", "8,000", "8 000", "Rs 8,000", etc.
    money_ok = bool(re.search(r"8[\s,]*000", a)) or "8000" in an
    fin = "finance" in an or "reimbursement" in an or "policy_finance" in an
    wfh_ok = (
        "wfh" in an
        or "work from home" in an
        or "permanent" in an
        or "home office" in an
    )
    cites = result.get("cited_chunks") or []
    finance_in_sources = any(
        "finance" in _norm(str(c.get("doc_name", ""))) for c in cites
    )
    # Rubric: amount + (wording OR finance policy appears in retrieval sources)
    ok = money_ok and (fin or wfh_ok or finance_in_sources)
    return ok, "ok" if ok else "expect Rs 8,000 + finance/WFH cues (or finance doc in cited_chunks)"


CASES = [
    ("Who approves leave without pay?", check_leave_without_pay),
    ("Can I use my personal phone for work files?", check_personal_phone),
    ("What is the flexible working culture?", check_flexible_culture),
    ("What is the home office equipment allowance?", check_home_office_allowance),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="README reference_verification checks")
    parser.add_argument(
        "--db-path",
        default=None,
        help="Chroma path (default: rag_server DEFAULT_CHROMA_PATH)",
    )
    args = parser.parse_args()

    db = args.db_path or DEFAULT_CHROMA_PATH
    llm = _load_llm()
    if llm and os.environ.get("GEMINI_API_KEY"):
        print("[verify] Using llm_adapter + GEMINI_API_KEY")
    else:
        print("[verify] No GEMINI_API_KEY — checks may fail (answers won't be policy-grounded LLM text).")

    all_ok = True
    for q, checker in CASES:
        print("\n" + "=" * 60)
        print("Q:", q)
        r = query(q, llm_call=llm, db_path=db)
        passed, note = checker(r)
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_ok = False
        print(f"[{status}] {note}")
        print("--- answer (excerpt) ---")
        print((r.get("answer") or "")[:800])
        if len(r.get("answer") or "") > 800:
            print("...")
    print("\n" + "=" * 60)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
