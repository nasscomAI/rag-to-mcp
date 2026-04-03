# RAG-to-MCP
**Nasscom AI-Code Sarathi · Developer Workshop**
**R.I.C.E · CRAFT · sentence-transformers · ChromaDB · MCP**

**New here? Start with the [FAQ](./FAQ.md) and [Prerequisites](./PREREQUISITES.md).**

---

## What You Will Build

Three use cases. One developer path. No branching.

| UC | What you build | Core skill taught |
|---|---|---|
| **UC-0A** | Complaint Classifier | R.I.C.E prompt engineering + CRAFT loop |
| **UC-RAG** | Retrieval-Augmented Generation server | Chunking · Embedding · Retrieval · Grounded generation |
| **UC-MCP** | MCP tool server wrapping your RAG server | Tool contract design · JSON-RPC · Agent tool interface |

Each UC builds on the previous. UC-MCP calls UC-RAG. UC-RAG uses the same
policy documents that test UC-0A's edge cases.

---

## The Stack

| Component | Tool | Why |
|---|---|---|
| Embedder | sentence-transformers `all-MiniLM-L6-v2` | Local, no API key, ~80MB one-time download |
| Vector store | ChromaDB | pip install, no binary deps, works offline |
| LLM | Gemini free tier (swappable) | Free API key, no credit card, fast |
| MCP transport | Plain HTTP + JSON-RPC | No SDK — you see the raw protocol |
| Framework | R.I.C.E + CRAFT | Prompt discipline applied at every layer |

---

## Prerequisites

**Install before the session — not during:**

```bash
pip3 install sentence-transformers chromadb google-generativeai
```

**Get a Gemini API key (free, no credit card):**
1. Go to https://aistudio.google.com/app/apikey
2. Click "Create API key"
3. Set it: `export GEMINI_API_KEY="your-key-here"`

**Verify setup:**
```bash
python3 --version                    # Must be 3.9+
python3 -c "import chromadb; print('ChromaDB OK')"
python3 -c "from sentence_transformers import SentenceTransformer; print('ST OK')"
```

See `docs/pre-session-install.md` for the full setup checklist.

---

## Repo Structure

```
RAG-to-MCP/
├── uc-0a/              Complaint Classifier — done with facilitator
│   ├── README.md
│   ├── agents.md       generate from README using AI
│   ├── skills.md       generate from README using AI
│   └── classifier.py   build using AI
│
├── uc-rag/             RAG Server — main developer UC
│   ├── README.md
│   ├── agents.md       generate from README using AI
│   ├── skills.md       generate from README using AI
│   ├── rag_server.py   build using AI
│   └── stub_rag.py     working fallback — used by UC-MCP
│
├── uc-mcp/             MCP Server — wraps your RAG server
│   ├── README.md
│   ├── agents.md       generate from README using AI
│   ├── skills.md       generate from README using AI
│   ├── mcp_server.py   build using AI
│   ├── test_client.py  pre-built — do not modify
│   └── llm_adapter.py  Gemini default — swap to Claude/OpenAI here
│
├── data/
│   ├── city-test-files/    test_pune.csv · test_hyderabad.csv · etc.
│   └── policy-documents/   policy_hr_leave.txt · policy_it_acceptable_use.txt
│                           policy_finance_reimbursement.txt
│
└── docs/
    ├── guide.md                 Step-by-step participant guide
    └── pre-session-install.md   Night-before install checklist
```

---

## How to Submit

1. Fork this repo
2. Create branch: `participant/[your-name]-[city]`
3. Complete UC-0A, UC-RAG, UC-MCP
4. Commit after each UC using the formula:
   ```
   UC-RAG Fix [failure mode]: [why] → [what you changed]
   ```
5. Push and open a Pull Request against `main`

Your PR must contain `agents.md`, `skills.md`, and the `.py` file for all three UCs.

See `docs/guide.md` for the complete step-by-step guide.

---

## Minimum Pass Requirements

- [ ] `agents.md` + `skills.md` committed for all 3 UCs
- [ ] `uc-0a/classifier.py` runs on `test_[city].csv`, produces `results_[city].csv`
- [ ] `uc-rag/rag_server.py` is your implementation (not `stub_rag.py`)
- [ ] `uc-mcp/mcp_server.py` passes at least one `test_client.py` test
- [ ] 3+ commits with meaningful messages, one per UC
- [ ] PR template fully filled — every section complete

---

## Resources

Check out the [resources/](./resources) directory for curated reading and tools:
- [Coding Tools](./resources/coding-tools.md)
- [Books](./resources/books.md)
- [Courses](./resources/courses.md)
- [AI & Vector DB Platforms](./resources/platforms.md)
- [Code Review Tools](./resources/code-review-tools.md)

**Blocked for more than 5 minutes? Flag your tutor. Do not debug alone.**
