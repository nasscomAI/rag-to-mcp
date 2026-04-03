# RAG-to-MCP — Submission PR

**Name:**
**City / Group:**
**Date:**
**AI tool(s) used:**

---

## Submission Checklist

- [ ] `uc-0a/agents.md` — present and updated
- [ ] `uc-0a/skills.md` — present and updated
- [ ] `uc-0a/classifier.py` — runs without crash
- [ ] `uc-0a/results_[city].csv` — output present
- [ ] `uc-rag/agents.md` — present and updated
- [ ] `uc-rag/skills.md` — present and updated
- [ ] `uc-rag/rag_server.py` — not the stub, your implementation
- [ ] `uc-mcp/agents.md` — present and updated
- [ ] `uc-mcp/skills.md` — present and updated
- [ ] `uc-mcp/mcp_server.py` — passes at least one test_client.py test
- [ ] 3+ commits with meaningful messages, one per UC
- [ ] All sections below filled

---

## UC-0A — Complaint Classifier

**Which failure mode did you encounter first?**

>

**Which enforcement rule fixed it? Quote from your agents.md:**

>

**Your commit message for UC-0A:**

>

**Verification checkpoints:**
- [ ] All severity-signal rows (injury/child/school/hospital keywords) classified as Urgent
- [ ] No invented categories outside the defined taxonomy
- [ ] Justification column present and non-empty for every row

---

## UC-RAG — RAG Server

**Which failure mode did you encounter?**
*(chunk boundary / wrong retrieval / answer outside context)*

>

**What chunking strategy did you use and why?**

>

**Did your system correctly refuse "What is the flexible working culture?"?**
*(Should return refusal template — not in any document)*

> Yes / No —

**Did your system retrieve the correct document for "Can I use my personal phone for work files?"?**
*(Should retrieve IT policy, not HR leave policy)*

> Yes / No —

**Which enforcement rule in agents.md prevented answers outside retrieved context?**

>

**Your commit message for UC-RAG:**

>

**Verification checkpoints:**
- [ ] At least 3 test queries return grounded answers (cited from retrieved context)
- [ ] "What is the flexible working culture?" returns the refusal template (not a hallucinated answer)
- [ ] "Can I use my personal phone for work files?" retrieves IT policy, not HR leave policy
- [ ] Chunking produces more than 1 chunk per document (not whole-document embedding)

---

## UC-MCP — MCP Server

**Paste your tool description from mcp_server.py TOOL_DEFINITION:**

>

**Does it state the document scope explicitly?**

> Yes / No —

**Run result: `python3 test_client.py --run-all`**
*(Paste the summary output)*

>

**Did the budget forecast question return isError: true?**

> Yes / No —

**In one sentence — why is the tool description the enforcement?**

>

**Your commit message for UC-MCP:**

>

**Verification checkpoints:**
- [ ] Tool description explicitly states document scope (which policies are covered)
- [ ] Tool description states refusal behavior for out-of-scope queries
- [ ] `python3 test_client.py --run-all` executes without connection error
- [ ] Budget forecast question returns `isError: true` (out of scope)

---

## CRAFT Reflection

**Which step of the CRAFT loop was hardest across all three UCs?**

>

**What did you add to agents.md manually that the AI did not generate?**

>

**One specific task in your real work where you will use R.I.C.E in the next 7 days:**

>
