# Session Prerequisites

To participate in this session and build three use cases (UC-0A, UC-RAG, UC-MCP), ensure the following.

For step-by-step install instructions, see [docs/pre-session-install.md](./docs/pre-session-install.md).

---

## Hardware Prerequisites

**Laptop Specifications**
- **RAM**: **16GB minimum** (Highly Recommended). Modern AI-powered IDEs are memory-intensive.
- **Processor (CPU)**:
    - Intel Core i5 / AMD Ryzen 5 (11th Gen or newer) or better.
    - Apple Silicon (M1/M2/M3) for macOS users.
- **Storage**: At least **10GB of free space** for the workshop repository and model downloads.

---

## Software Prerequisites

**Core Environment**
- **Python**: Version **3.9 or higher**. Use the `python3` command.
    - Verify: `python3 --version`
- **Git**: Must be installed.
    - Verify: `git --version`
- **Python Packages**: `sentence-transformers`, `chromadb`, `google-generativeai`
    - Install: `pip3 install sentence-transformers chromadb google-generativeai`
    - Verify: `python3 -c "import chromadb; print('ChromaDB OK')"`
    - Verify: `python3 -c "from sentence_transformers import SentenceTransformer; print('ST OK')"`
- **Gemini API Key** (free, no credit card):
    1. Go to https://aistudio.google.com/app/apikey
    2. Click "Create API key"
    3. Set it: `export GEMINI_API_KEY="your-key-here"`

**Operating System & Tools**
- **IDEs**: Antigravity, Trae, Cursor, or VS Code.
- **CLIs**:
    - **Windows**: Use PowerShell or Command Prompt.
    - **macOS/Linux**: Use Terminal.
- **AI Tools**: Claude Code, Gemini CLI, Aider, or Mentat are also compatible.

---

## Project Data Verification

Confirm the following files are present in your local environment:

- **City Test Files**: `data/city-test-files/` (4 CSV files)
- **Policy Documents**: `data/policy-documents/` (3 TXT files)

---

## Quick Start Commands

```bash
# Verify Python
python3 --version

# Verify Git
git --version

# Verify packages
python3 -c "import chromadb; from sentence_transformers import SentenceTransformer; print('All OK')"

# Check data
ls data/city-test-files/
ls data/policy-documents/
```

For the full setup checklist, see [docs/pre-session-install.md](./docs/pre-session-install.md).
For troubleshooting, see [FAQ.md](./FAQ.md).
