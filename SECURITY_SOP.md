# Autonomous Systems  Security SOP & Protocol

This document establishes the "Zero-Trust" security protocol for all development and deployment within the Agent ecosystem.

---

##  Core Security Principles

1.  **Strict Environment Isolation**: Never hardcode API keys, tokens, or passwords. All sensitive values must reside in a `.env` file that is NEVER committed to Git.
2.  **Privacy First**: Personal identifying information (PII) or local data snapshots (like Lead sheets, logs, or triage history) must be excluded from public repositories.
3.  **Review Before Push**: Always perform a `git status` and a manual scan before pushing code to a public domain.
4.  **Instant Rotation**: If a secret is ever accidentally pushed, it must be considered compromised. Rotate the key immediately on the provider side (Google, Discord, OpenAI, etc.).

---

##  Standard File Handling

| File Category | Protocol | Examples |
|---|---|---|
| **Hard Secrets** | **EXCLUDE** | `.env`, `credentials.json`, `token.json` |
| **Local Data** | **EXCLUDE** | `logs/`, `drafts/`, `triage_history.json` |
| **Metadata** | **INCLUDE** | `pyproject.toml`, `requirements.txt`, `README.md` |
| **Templates** | **INCLUDE** | `.env.example`, `credentials.json.example` |

---

##  Automated Safeguards

### 1. The Protection Script
Run `python scripts/check_secrets.py` before every push. This script scans the entire codebase for common secret patterns (Discord tokens, Google IDs, etc.).

### 2. Git Pre-Commit Hook
We have installed a pre-commit hook that automatically runs the secret scanner whenever you attempt a `git commit`. If a secret is found, the commit will be blocked.

---

##  Preparation Checklist for New Projects

1.  Initialize Git: `git init`
2.  Copy global `.gitignore` patterns.
3.  Create `.env.example` with necessary keys (empty values).
4.  Run a manual secret sweep: `python scripts/check_secrets.py`
5.  Push to a new GitHub repository.

---

##  Incident Response
If you suspect an exposure:
1.  **Revoke**: Revoke the key in the service provider dashboard.
2.  **Clean**: Use `git filter-repo` or `BFG Repo-Cleaner` to scrub the history (standard `git rm` is not enough as secrets remain in history).
3.  **Redeploy**: Deploy new keys and update your local `.env`.
