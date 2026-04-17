# Executor  Layer 3

This package performs **deterministic actions**.

> *"It is not responsible for reasoning. It executes reliably using tools, scripts, and systems."*

---

## Tool Classes

| Module | Tool Class | Approved Sources / Systems |
|---|---|---|
| `tools/content.py` | Content / Source | Google Sheets, Substack, OneDrive, Bluesky (read) |
| `tools/transformation.py` | Transformation / Generation | OpenAI, text formatters |
| `tools/publishing.py` | Publishing / Distribution | Bluesky (post), SMTP email |
| `tools/logging_tool.py` | Logging / Monitoring | structlog  console + rotating file |
| `tools/storage.py` | Storage / Archive | File system, directive archive |

---

## Execution Principles

- **Prefer tools over manual logic**  don't re-invent what a library does
- **Keep actions deterministic**  same input  same output
- **Avoid improvisation**  the directive defines what to do, the executor just does it
- **Ensure repeatability**  log inputs/outputs so any action can be replicated

---

## Logging Requirements

All meaningful actions must log (use `log_action()`):
| Field | Description |
|---|---|
| `what` | What was done |
| `when` | Timestamp (ISO 8601) |
| `why` | Directive ID or reason |
| `changed` | What changed as a result |

All errors must log (use `log_error()`):
| Field | Description |
|---|---|
| `failure_type` | Classification |
| `attempted_fix` | What the system tried |
| `final_state` | State after the error |

---

## Data Integrity

- **Never overwrite** critical records without creating a `.bak` trace first
- **Never delete** directive files  use `DirectiveArchiver` to supersede them
- All auditability is handled automatically by the storage tools
