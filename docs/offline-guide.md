# Offline Guide — AI-Code Sarathi
**RAG-to-MCP · Self-Study Edition**

Use this guide to complete or repeat any part of the workshop on your own, without a tutor or internet connection (except for LLM API calls).

---

## Contents

1. [Setup](#1-setup)
2. [The R.I.C.E Framework](#2-the-rice-framework)
3. [UC-0A — Complaint Classifier](#3-uc-0a--complaint-classifier)
4. [RAG — Build a Retrieval Pipeline](#4-rag--build-a-retrieval-pipeline)
5. [UC-MCP — Expose RAG as an MCP Tool](#5-uc-mcp--expose-rag-as-an-mcp-tool)
6. [What Comes Next](#6-what-comes-next)

---

## 1. Setup

### Install dependencies

```bash
pip3 install sentence-transformers chromadb google-generativeai
```

### Pre-download the embedding model (one time, ~80MB)

```bash
python3 -c "
from sentence_transformers import SentenceTransformer
m = SentenceTransformer('all-MiniLM-L6-v2')
print('Model ready. Vector size:', m.encode(['test']).shape[1])
"
```

### Get a free LLM API key

**Gemini (recommended):**
1. Go to https://aistudio.google.com/app/apikey
2. Sign in with your Google account
3. Click Create API key
4. Set it:

```bash
# Mac / Linux
export GEMINI_API_KEY="your-key-here"

# Windows CMD
set GEMINI_API_KEY=your-key-here

# Windows PowerShell
$env:GEMINI_API_KEY="your-key-here"
```

**Grok (alternative, also free):**
1. Go to https://console.x.ai
2. Create an account and generate an API key
3. Set it:

```bash
export XAI_API_KEY="your-key-here"
```

### Clone the repo

```bash
git clone https://github.com/nasscomAI/RAG-to-MCP.git
cd RAG-to-MCP
```

### Build the stub RAG index

```bash
python3 uc-rag/stub_rag.py --build-index
```

Must print: `Index built at ./stub_chroma_db`

Test it:

```bash
python3 uc-rag/stub_rag.py --query "Who approves leave without pay?"
```

Must return a cited answer from `policy_hr_leave.txt`.

### Create your branch

```bash
git checkout -b participant/[your-name]-[city]
# Example: participant/arshdeep-pune
```

---

## 2. The R.I.C.E Framework

R.I.C.E is the framework you use before writing any prompt, generating any agents.md, or building any code.

### The four elements

| Element | Question it answers | Without it |
|---|---|---|
| **R — Role** | Who is the AI acting as? | AI picks a generic default persona |
| **I — Intent** | What does correct output look like, verifiably? | AI optimises for plausibility not correctness |
| **C — Context** | What is allowed? What is excluded? | AI uses anything, including wrong assumptions |
| **E — Enforcement** | What specific conditions must never be violated? | AI makes decisions you did not know it was making |

### The critical point about Enforcement

Enforcement is the only element the AI will never self-correct. For Role, Intent, and Context, the AI makes reasonable guesses when you are vague. For Enforcement, where you leave a gap, it makes a decision. You did not know it was making a decision. That is the failure.

**Wish vs Rule:**

| Wish — not enforceable | Rule — testable |
|---|---|
| Be accurate | category must be exactly one of: [fixed list] |
| Do not hallucinate | If no chunk scores above 0.6 — return refusal template |
| Try to be consistent | Priority must be Urgent if description contains: child, school, injury |

A rule names a condition and a required output. If you cannot write a test that fails when the rule is broken — it is not a rule.

### How to generate agents.md using Gemini CLI

```bash
gemini
```

Then paste this prompt followed by the full UC README:

```
Read the following UC README. Using the R.I.C.E framework,
generate an agents.md YAML with four fields:
role, intent, context, enforcement.

Enforcement must include every rule listed under
"Enforcement Rules Your agents.md Must Include".
Output only valid YAML. No explanation, no code fences.

README:
[paste README content here]
```

**Always update the output manually.** Check every enforcement rule against the README failure modes. The AI generates from what you wrote — it cannot generate what you forgot to write.

### agents.md structure

```yaml
role: >
  [Who the agent is and its operational boundary]

intent: >
  [What correct output looks like — verifiable]

context: >
  [Allowed sources. Exclusions stated explicitly.]

enforcement:
  - "[Specific testable rule 1]"
  - "[Specific testable rule 2]"
  - "[Refusal condition — if X, output Y, never guess]"
```

### How to generate skills.md using Gemini CLI

```
Read the following UC README. Generate a skills.md YAML
defining the skills described. Each skill needs:
name, description, input, output, error_handling.
error_handling must address the failure modes in the README.
Output only valid YAML.

README:
[paste README content here]
```

### Commit message formula

```
[UC-ID] Fix [what]: [why it failed] → [what you changed]
```

Examples:
```
UC-0A  Fix severity blindness: no keywords → added injury/child/school/hospital triggers
UC-RAG Fix chunk boundary: fixed-size split → sentence-aware chunking
UC-MCP Fix vague tool description: no scope → added CMC policy scope + refusal note
```

---

## 3. UC-0A — Complaint Classifier

**What you build:** A classifier that reads city complaint CSVs and outputs category, priority, reason, and flag.

**Input:** `data/city-test-files/test_[city].csv`
**Output:** `uc-0a/results_[city].csv`

### Step 1 — Run the naive prompt first

Open your AI tool and paste:

```
Classify this citizen complaint by category and priority.

Complaint: Deep pothole near bus stop. School children at risk during morning hours.
```

Record what comes back. Note:
- Does the category name change if you run it again?
- Is priority Urgent given the school children mention?
- Is there a reason field?

This is the failure you are fixing.

### Step 2 — Read the README

Open `uc-0a/README.md`. Read the five failure modes and the classification schema before writing anything.

### Step 3 — Generate agents.md and skills.md

Use the Gemini CLI prompts from Section 2 with `uc-0a/README.md`.

Update agents.md — the enforcement section must explicitly list:
- The exact category enum (all 9 values)
- The severity keywords that trigger Urgent: injury, child, school, hospital, ambulance, fire, hazard, fell, collapse
- The reason field requirement
- The NEEDS_REVIEW refusal condition

### Step 4 — Build classifier.py using TRAE

Open TRAE. Share your agents.md, skills.md, and the UC README. Ask TRAE to implement `uc-0a/classifier.py` following the enforcement rules exactly.

### Step 5 — Run it

```bash
cd uc-0a
python3 classifier.py \
  --input ../data/city-test-files/test_pune.csv \
  --output results_pune.csv
```

### Step 6 — Check the output

Open `results_pune.csv`. For every row where the description contains child, school, injury, hospital, ambulance, fire, hazard, fell, or collapse — priority must be Urgent. If any are not — your enforcement rule is missing a keyword.

### Step 7 — Fix and commit

Fix one thing. Re-run. Verify. Then:

```bash
git add uc-0a/agents.md uc-0a/skills.md uc-0a/classifier.py uc-0a/results_pune.csv
git commit -m "UC-0A Fix [failure mode]: [why] → [what you changed]"
```

---

## 4. RAG — Build a Retrieval Pipeline

You watched this built live in the session. This section lets you build it yourself from scratch.

**What you build:** A server that chunks policy documents, embeds them, stores vectors in ChromaDB, retrieves relevant chunks per query, and answers using only retrieved context.

**Input:** `data/policy-documents/` (3 policy .txt files)
**Run:** `python3 uc-rag/rag_server.py --build-index`

### The three failure modes to fix

| Failure | Cause | Fix |
|---|---|---|
| Chunk boundary | Fixed-size split cuts clause 5.2 across two chunks | Sentence-aware chunking, max 400 tokens |
| Wrong retrieval | No similarity threshold — wrong document retrieved | Filter chunks below score 0.6 |
| Context breach | LLM adds training knowledge to answer | Enforcement: answer from retrieved chunks only |

### Step 1 — Read the README

Open `uc-rag/README.md`. Read all enforcement rules and both skill definitions before writing anything.

### Step 2 — Generate agents.md and skills.md

Use Gemini CLI with `uc-rag/README.md`. After generating:
- Check enforcement includes the similarity threshold value (0.6)
- Check error_handling for `retrieve_and_answer` includes the exact refusal template wording

### Step 3 — Implement chunk_documents

Open TRAE with agents.md, skills.md, and README. Ask TRAE to implement `chunk_documents` only:

```
Implement chunk_documents in uc-rag/rag_server.py.
Split on sentence boundaries using regex on ". " and ".\n".
Maximum 400 tokens per chunk. Never split mid-sentence.
Return list of dicts: {doc_name, chunk_index, text, id}
Do not implement any other functions yet.
```

Verify immediately:

```bash
python3 -c "
from uc_rag.rag_server import chunk_documents
chunks = chunk_documents('data/policy-documents')
print(len(chunks), 'chunks from', len(set(c['doc_name'] for c in chunks)), 'documents')
for c in chunks[:2]:
    print(f'  [{c[\"doc_name\"]}, chunk {c[\"chunk_index\"]}]: {c[\"text\"][:80]}')
"
```

Check that clause 5.2 ("LWP requires approval from the Department Head AND the HR Director") appears in a single chunk — not split across two.

### Step 4 — Implement build_index

Ask TRAE:

```
Implement build_index in uc-rag/rag_server.py.
Use SentenceTransformer('all-MiniLM-L6-v2') to embed chunks.
Use ChromaDB PersistentClient at db_path.
Delete and recreate the collection 'policy_docs' before adding.
Print progress and final count.
Do not implement any other functions yet.
```

Run it:

```bash
cd uc-rag
python3 rag_server.py --build-index
```

The progress bar shows embeddings being computed. When complete you should see the chunk count and db path.

### Step 5 — Implement retrieve_and_answer

Ask TRAE:

```
Implement retrieve_and_answer in uc-rag/rag_server.py.
Embed the query, retrieve top 3 chunks from ChromaDB.
Convert L2 distance to similarity: similarity = 1 - (distance / 2)
Filter out chunks where similarity < 0.6.
If no chunks pass: return the refusal template exactly.
Build prompt with retrieved chunks as context only.
Call call_llm from uc-mcp/llm_adapter.py.
Return dict: {answer, cited_chunks, refused}
```

### Step 6 — Run naive mode first, then RAG mode

```bash
# Naive — no retrieval, see the failure
python3 rag_server.py --naive \
  --query "Can I use my personal phone to access work files from home?"

# RAG — with retrieval, see the fix
python3 rag_server.py \
  --query "Can I use my personal phone to access work files from home?"
```

The naive answer blends IT and HR policies. The RAG answer cites one source from the IT policy only.

### Step 7 — Verify the four reference queries

```bash
python3 rag_server.py --query "Who approves leave without pay?"
# Must cite HR policy section 5.2. Must name BOTH Department Head AND HR Director.

python3 rag_server.py --query "Can I use my personal phone to access work files from home?"
# Must cite IT policy only. Must NOT blend HR policy.

python3 rag_server.py --query "What is the home office equipment allowance?"
# Must cite Finance policy section 3.1. Amount: Rs 8,000.

python3 rag_server.py --query "What is the flexible working culture?"
# Must return refusal template. This is not in any document.
```

### Step 8 — Fix and commit

```bash
git add uc-rag/agents.md uc-rag/skills.md uc-rag/rag_server.py
git commit -m "UC-RAG Fix [failure mode]: [why] → [what you changed]"
```

---

## 5. UC-MCP — Expose RAG as an MCP Tool

**What you build:** A plain HTTP server implementing JSON-RPC 2.0 that exposes one tool: `query_policy_documents`. Any MCP-compatible agent can discover and call this tool.

**Run:** `python3 uc-mcp/mcp_server.py --port 8765`
**Test:** `python3 uc-mcp/test_client.py --run-all`

### The failure mode

A vague tool description gives agents permission to call the tool for questions outside its scope. The tool description IS the Enforcement rule — at the tool interface layer.

| Vague | Specific |
|---|---|
| "Answers questions about company policies." | "Answers questions about CMC HR Leave Policy, IT Acceptable Use Policy, and Finance Reimbursement Policy ONLY. Returns refusal for questions outside these three documents." |

### The MCP protocol — two methods

**tools/list** — discovery. The agent calls this to find out what tools exist.

```json
Request:  {"jsonrpc": "2.0", "method": "tools/list", "id": 1}
Response: {"result": {"tools": [{"name": "query_policy_documents", "description": "...", "inputSchema": {...}}]}}
```

**tools/call** — execution. The agent calls this to invoke a tool.

```json
Request:  {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query_policy_documents", "arguments": {"question": "Who approves LWP?"}}, "id": 2}
Response: {"result": {"content": [{"type": "text", "text": "..."}], "isError": false}}
```

All responses return HTTP 200. Application errors use `isError: true` in the JSON body — not HTTP error codes.

### Step 1 — Set up your LLM

Edit `uc-mcp/llm_adapter.py`. For Gemini (default):

```bash
export GEMINI_API_KEY="your-key-here"
python3 uc-mcp/llm_adapter.py
# Must print a response
```

For Grok — uncomment the Grok section and comment out the Gemini section.

### Step 2 — Generate agents.md and skills.md

Use Gemini CLI with `uc-mcp/README.md`. The enforcement section must include:
- Tool description must name the three documents explicitly
- Tool description must state what it refuses
- inputSchema must require question as a non-empty string
- isError must be true on refusal

### Step 3 — Write TOOL_DEFINITION description first

Before asking TRAE to implement the server, write the tool description yourself. This is your Enforcement rule. Do not delegate it to the AI.

Open `uc-mcp/mcp_server.py` and fill in:

```python
TOOL_DEFINITION = {
    "name": "query_policy_documents",
    "description": (
        "Answers questions about CMC HR Leave Policy, IT Acceptable Use Policy, "
        "and Finance Reimbursement Policy ONLY. Returns cited answers grounded in "
        "retrieved document chunks. Returns a refusal for questions outside these "
        "three documents. Do not send budget, procurement, or general policy "
        "questions to this tool."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "The policy question to answer"}
        },
        "required": ["question"]
    }
}
```

### Step 4 — Implement mcp_server.py using TRAE

Share agents.md, skills.md, README, and your TOOL_DEFINITION with TRAE. Ask it to implement `MCPHandler.do_POST` to handle `tools/list` and `tools/call`.

### Step 5 — Start the server

```bash
cd uc-mcp
python3 mcp_server.py --port 8765
```

### Step 6 — Run the test client in a second terminal

```bash
python3 test_client.py --run-all
```

Four tests run:
1. tools/list — check description names the three documents
2. In-scope question — must return a cited answer
3. Cross-document question — must not blend IT and HR policies
4. Out-of-scope question (budget forecast) — must return isError: true

### Step 7 — Fix and commit

If the budget forecast question does not return `isError: true` — your tool description is too vague. Update `TOOL_DEFINITION["description"]` to explicitly state the three documents and the refusal condition. Restart the server and re-run the tests.

```bash
git add uc-mcp/agents.md uc-mcp/skills.md uc-mcp/mcp_server.py
git commit -m "UC-MCP Fix [failure mode]: [why] → [what you changed]"
```

---

## 6. What Comes Next

### Extend the RAG pipeline

**Better chunking:** Try recursive chunking — split on paragraph first, then sentence, then word. Preserves document structure better than flat sentence splitting.

**Hybrid search:** Combine dense retrieval (embeddings) with sparse retrieval (BM25 keyword search). Better results on queries with specific technical terms.

**Reranking:** After retrieving top-k chunks, use a cross-encoder to rerank them. More accurate but slower.

**Multiple collections:** Separate ChromaDB collections per document type. Use metadata routing to decide which collection to query.

### Extend UC-MCP

**Multiple tools:** Add a second tool — for example `list_policy_sections` that returns the table of contents for a given document. Agents can discover both tools via tools/list.

**Tool chaining:** Build an agent that calls `list_policy_sections` first to find the right section, then calls `query_policy_documents` with a more targeted question.

**Authentication:** Add an API key check in `MCPHandler.do_POST` before processing any request.

### Build your own use case

Take any document corpus you work with — internal wikis, runbooks, API documentation, compliance policies — and apply the same pipeline:

1. Write a RICE prompt for your use case
2. Generate agents.md and skills.md from a README you write
3. Chunk and index your documents
4. Build retrieve_and_answer with your enforcement rules
5. Expose it as an MCP tool
6. Connect it to any MCP-compatible agent

### Agents and multi-step workflows

The next natural step after MCP is building agents that call multiple MCP tools in sequence. Frameworks to explore:

- **LangGraph** — stateful multi-step agents with explicit graph structure
- **CrewAI** — multi-agent systems with role-based task delegation
- **Anthropic Claude tool use** — native MCP client in Claude API

### Fine-tuning

If retrieval quality is not enough — the documents use domain-specific vocabulary that the embedding model does not handle well — consider fine-tuning a smaller embedding model on your domain data. This is a separate track and requires labelled query-document pairs.

---

## Quick Reference

### R.I.C.E at every layer

| Layer | Where RICE applies | Enforcement example |
|---|---|---|
| Prompt | Complaint classifier | Priority Urgent if: child, school, injury |
| Retrieval | RAG pipeline | Chunks scoring below 0.6 are excluded |
| Tool interface | MCP server | Tool description names three documents + refusal |

### Run commands

```bash
# UC-0A
python3 uc-0a/classifier.py --input data/city-test-files/test_pune.csv --output uc-0a/results_pune.csv

# UC-RAG — build index
python3 uc-rag/rag_server.py --build-index

# UC-RAG — query
python3 uc-rag/rag_server.py --query "your question here"

# UC-RAG — naive mode (see failures)
python3 uc-rag/rag_server.py --naive --query "your question here"

# UC-RAG — stub fallback
python3 uc-rag/stub_rag.py --query "your question here"

# UC-MCP — start server
python3 uc-mcp/mcp_server.py --port 8765

# UC-MCP — test
python3 uc-mcp/test_client.py --run-all
```

### Commit formula

```
[UC-ID] Fix [what]: [why it failed] → [what you changed]
```

### Getting help

- Repo issues: github.com/nasscomAI/RAG-to-MCP/issues
- Session materials: docs/ folder in the repo
- Nasscom AI-Code Sarathi: nasscom.in/nasscom-ai
