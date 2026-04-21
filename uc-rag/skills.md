# skills.md — UC-RAG RAG Server

# Implements: agents.md · stack: sentence-transformers · ChromaDB · LLM (swappable)

skills:
  - name: chunk_documents
    description: >
      Loads all policy text files from the policy-documents directory, splits each
      document into chunks of at most 400 tokens on sentence boundaries (never
      mid-sentence) so clauses are not split across chunks, and returns every chunk
      with stable metadata for citation and retrieval.
    input: >
      Path to the directory containing policy files (per agents.md io_contract:
      data/policy-documents/ with policy_hr_leave.txt, policy_it_acceptable_use.txt,
      policy_finance_reimbursement.txt). UTF-8 text files; implementation may accept
      equivalent absolute or relative paths.
    output: >
      A list of chunk records, each with: doc_name (source filename or logical id),
      chunk_index (0-based order within that document), text (chunk body). Chunks must
      respect the 400-token ceiling and sentence-boundary rule from agents.md enforcement.
    error_handling: >
      If the directory is missing or unreadable, fail fast with a clear error. If a
      single file is missing or not UTF-8 readable, log the path and either skip with
      a warning or fail according to server policy—never emit empty chunks silently.
      Empty files yield no chunks. Chunking must never split mid-sentence (guards against
      chunk boundary failure in agents.md failure_modes_to_guard).

  - name: retrieve_and_answer
    description: >
      Embeds the user query with sentence-transformers, retrieves the top candidates
      from ChromaDB by cosine similarity, drops any chunk below 0.6 similarity, then
      calls the LLM with only the remaining retrieved chunks as context. The answer
      must cite source document name and chunk index for every substantive claim, use
      only information in those chunks, and if the query genuinely requires two
      documents, run retrieval per document separately and never merge chunks from
      different documents into one synthesized answer. If no chunk scores above 0.6,
      return only the agents.md refusal_template with listed chunk sources (if any).
    input: >
      A query string (natural-language staff question). Optional: routing hints or
      document scope if the server implements multi-document queries—retrieval must still
      honor separate per-document retrieval when the query spans policies (agents.md
      enforcement).
    output: >
      A structured result: answer text (or refusal text only), plus a list of cited
      chunks each identified by doc_name and chunk_index and tied to the answer;
      similarity scores may be included for debugging. Citations must satisfy agents.md
      enforcement (document name + chunk index on every answer path that is not refusal-only).
    error_handling: >
      If embedding or ChromaDB fails, surface a clear error; do not hallucinate policy
      text. If no retrieved chunk has similarity ≥ 0.6, output exactly the refusal
      template from agents.md (with retrieved chunk sources listed as applicable) and
      do not call the LLM for a substantive answer—addresses wrong retrieval and
      context-breach risk by refusing instead of guessing. If top-3 retrieval pulls
      wrong-policy chunks, mitigate with metadata filtering and threshold 0.6 per
      agents.md. The LLM prompt must forbid facts outside retrieved chunks to guard
      answer-outside-context failure.

alignment:
  agent_spec: "agents.md"
  enforcement: >
    chunk_documents must never exceed 400 tokens per chunk or split mid-sentence.
    retrieve_and_answer must enforce similarity 0.6, citations (doc_name + chunk_index),
    retrieved-chunks-only answers, refusal when below threshold, and separate retrieval
    for multi-document queries without merging cross-document chunks into one answer.
