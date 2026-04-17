#  Agent Core  Central Intelligence & Governance

The internal "Engine Room" of the Autonomous Systems ecosystem. This directory contains shared services, global configuration, and the system-wide security layer.

---

##  Core Services

- **`guardian.py`**: The real-time security monitor. Routes all system alerts and errors to your Discord webhook.
- **`dashboard_server.py`**: The backend API for the Agent Dashboard (UI).
- **`new_project.py`**: A standardization script to initialize new Agent projects with approved boilerplate (Remote Shutdown, logging, etc.).

---

##  Governance & Security
This folder is the "Zero-Trust" authority. It manages:
1. **Secret Scanning**: Ensuring API keys never leave the local environment.
2. **Standardized Logging**: Enforcing structured telemetry across all projects.
3. **Environment Sync**: Centralized `.env` loading for sub-projects.

---

##  Usage
Scripts in this directory generally run in the background or are imported by other project modules. To start the dashboard backend manually:
```bash
.venv\Scripts\python 04_Agent_Core/scripts/dashboard_server.py
```

---
 2026 Autonomous Intelligence Systems  Built for Automated Stewardship.
