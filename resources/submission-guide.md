# How to Submit Your Assignment
**AI-Code Sarathi · RAG-to-MCP**

This guide walks you through submitting your work as a GitHub Pull Request.
Follow every step in order.

---

## Before You Submit

Check that you have completed at least these files for each UC you worked on:

**UC-0A (done in session with facilitator):**
- [ ] `uc-0a/agents.md` — generated and updated
- [ ] `uc-0a/skills.md` — generated and updated
- [ ] `uc-0a/classifier.py` — runs without errors
- [ ] `uc-0a/results_[city].csv` — output file present

**UC-RAG (if you built it):**
- [ ] `uc-rag/agents.md` — generated and updated
- [ ] `uc-rag/skills.md` — generated and updated
- [ ] `uc-rag/rag_server.py` — your implementation, not stub_rag.py

**UC-MCP (done in session or at home):**
- [ ] `uc-mcp/agents.md` — generated and updated
- [ ] `uc-mcp/skills.md` — generated and updated
- [ ] `uc-mcp/mcp_server.py` — passes at least one test_client.py test

You do not need all three UCs to submit. Submit whatever you completed.

---

## Step 1 — Make Sure Everything is Saved

Open your code editor. Save all open files.

---

## Step 2 — Commit Your Work

### Using GitHub Desktop (recommended)

1. Open **GitHub Desktop**
2. In the left panel under **Changes** — verify the files shown are the ones you want to submit
3. At the bottom of the left panel, in the **Summary** field, type your commit message:

```
[UC-IDs] Session submission — [your name]
```

Examples:
```
UC-0A UC-MCP Session submission — Arshdeep Singh
UC-0A UC-RAG UC-MCP Session submission — Priya Sharma
```

4. Click **Commit to participant/[your-name]-[city]**

### Using Terminal (alternative)

```bash
# Check which files have changed
git status

# Stage all your files
git add .

# Commit with your message
git commit -m "UC-0A UC-MCP Session submission — [your name]"
```

---

## Step 3 — Push to GitHub

### Using GitHub Desktop

Click **Push origin** in the top bar.

When complete the button changes to **Fetch origin**.

### Using Terminal

```bash
git push origin participant/[your-name]-[city]
```

---

## Step 4 — Verify the Push Worked

1. Open your browser
2. Go to your fork:
   ```
   https://github.com/[your-username]/RAG-to-MCP
   ```
3. Click the **branches** dropdown — it shows `main` by default
4. Find your branch `participant/[your-name]-[city]` in the list
5. Click it — your files should be visible

If your branch is not there — the push did not work. Go back to Step 3.

---

## Step 5 — Open a Pull Request

1. Go to the **original** repository:
   ```
   https://github.com/nasscomAI/RAG-to-MCP
   ```

2. GitHub will show a yellow banner:
   **"[your-branch] had recent pushes — Compare & pull request"**
   Click **Compare & pull request**

   If the banner does not appear:
   - Click the **Pull requests** tab
   - Click **New pull request**
   - Set **base** to `main`
   - Set **compare** to your branch name

3. Set the **title** exactly as:
   ```
   [City] [Name] — AI-Code Sarathi Submission
   ```
   Example:
   ```
   [Pune] Arshdeep Singh — AI-Code Sarathi Submission
   ```

---

## Step 6 — Fill the PR Template

The description box will be pre-filled with the submission template. Fill in every section for the UCs you completed.

For UCs you did not complete — write `Not completed in this submission`.

Do not leave sections blank.

---

## Step 7 — Submit

Click **Create pull request**.

Your submission is now complete. Note the PR URL — it will look like:
```
https://github.com/nasscomAI/RAG-to-MCP/pull/[number]
```

---

## If You Want to Update Your Submission Later

You do not need to open a new PR. Just commit more changes and push again — the PR updates automatically.

```bash
# Make your changes, then:
git add .
git commit -m "UC-MCP Updated: fixed vague tool description"
git push origin participant/[your-name]-[city]
```

The PR will show the new commits automatically.

---

## Common Problems

**"Your branch is behind main"**
This means the original repo has been updated since you forked it. You can safely ignore this for submission purposes — your PR will still work.

**"Nothing to commit"**
Your files are already committed. Skip to Step 3 — Push.

**The yellow banner does not appear on GitHub**
Go to Pull requests → New pull request → set compare to your branch manually.

**GitHub Desktop says "No local changes"**
Your changes are already committed. Go to Step 3 — Push.

**Push is rejected with "non-fast-forward"**

```bash
git pull origin participant/[your-name]-[city] --rebase
git push origin participant/[your-name]-[city]
```

**You committed to main by mistake**

```bash
# Move your commit to your branch
git branch participant/[your-name]-[city]
git reset HEAD~1 --soft
git checkout participant/[your-name]-[city]
git add .
git commit -m "your message"
```

---

## Checklist Before You Close Your Laptop

- [ ] All files saved in your code editor
- [ ] Committed with a meaningful message
- [ ] Pushed to GitHub — branch visible in your fork
- [ ] Pull Request opened on the original repo
- [ ] PR title follows the format: [City] [Name] — AI-Code Sarathi Submission
- [ ] PR template filled for all UCs you completed
- [ ] PR URL noted

---

## Questions

Raise an issue on the repo:
```
https://github.com/nasscomAI/RAG-to-MCP/issues
```

Or contact the session organiser directly.
