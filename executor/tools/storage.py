"""
Storage / Archive Tools — Layer 3: Execution

Tool Class 5: Storage / Archive Tools (from CLAUDE.md)

Approved storage:
    - Google Sheets (append / update rows)
    - Local file archive (directive versions, drafts)
    - Databases (future)

Data Integrity Rule (strict):
    - Never overwrite critical records without a trace
    - Always preserve historical versions
    - Ensure auditability

All write operations must leave an audit trail.
"""

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from executor.tools.logging_tool import get_logger, log_action

log = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Directive Archiver
# ──────────────────────────────────────────────────────────────────────────────

class DirectiveArchiver:
    """
    Archives previous versions of directives before they are revised.

    SH Rule: Agents may revise directives, but must:
    - Archive the previous version automatically
    - Log timestamp, reason for change, and agent ID
    - Never delete — only supersede

    Usage:
        archiver = DirectiveArchiver()
        archiver.archive(
            directive_path=Path("directives/publish-bluesky.md"),
            reason="Updated source approval criteria",
            agent_id="agent-001",
        )
    """

    ARCHIVE_DIR = Path("directives/_archive")

    def __init__(self, archive_dir: Optional[Path] = None) -> None:
        self.archive_dir = archive_dir or self.ARCHIVE_DIR
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def archive(
        self,
        directive_path: Path,
        reason: str,
        agent_id: str,
        version: Optional[str] = None,
    ) -> Path:
        """
        Archive the current version of a directive before revision.

        Args:
            directive_path: The directive file to archive.
            reason:         Why the directive is being revised.
            agent_id:       ID of agent or human making the revision.
            version:        Version string, e.g. "1.0". If None, auto-detect.

        Returns:
            Path to the created archive file.

        Raises:
            FileNotFoundError: If directive_path does not exist.
        """
        if not directive_path.exists():
            raise FileNotFoundError(f"Directive not found: {directive_path}")

        timestamp = datetime.now(timezone.utc).isoformat()
        version_str = version or self._detect_version(directive_path)
        archive_name = f"{directive_path.stem}-v{version_str}.md"
        archive_path = self.archive_dir / archive_name

        # Prevent overwriting an existing archive
        if archive_path.exists():
            safe_ts = timestamp.replace(":", "-").replace(".", "-")
            archive_name = f"{directive_path.stem}-v{version_str}-{safe_ts}.md"
            archive_path = self.archive_dir / archive_name

        shutil.copy2(directive_path, archive_path)

        log_action(
            log,
            what=f"Archived directive: {directive_path.name} → {archive_name}",
            when=timestamp,
            why=reason,
            changed=f"Created archive: {archive_path}",
            agent_id=agent_id,
        )

        return archive_path

    def _detect_version(self, directive_path: Path) -> str:
        """
        Extract version from the directive's front matter.
        Falls back to '1.0' if not found.
        """
        try:
            content = directive_path.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("version:"):
                    return line.split(":", 1)[1].strip().strip('"')
        except Exception:
            pass
        return "1.0"

    def list_archives(self, directive_stem: Optional[str] = None) -> list[Path]:
        """
        List all archived directive versions, optionally filtered by name.
        """
        pattern = f"{directive_stem}-v*.md" if directive_stem else "*.md"
        return sorted(self.archive_dir.glob(pattern))


# ──────────────────────────────────────────────────────────────────────────────
# Generic File Storage
# ──────────────────────────────────────────────────────────────────────────────

class FileStorage:
    """
    General-purpose file storage with audit trail.

    Writes always append metadata headers to preserve traceability.
    Overwrites require an explicit reason to maintain data integrity.
    """

    def write(
        self,
        path: Path,
        content: str,
        agent_id: str,
        why: str,
        overwrite: bool = False,
    ) -> None:
        """
        Write content to a file with audit trail.

        Args:
            path:      Target file path.
            content:   Content to write.
            agent_id:  ID of the agent performing the write.
            why:       Reason for the write operation.
            overwrite: If False and file exists, raises FileExistsError.

        Raises:
            FileExistsError: If file exists and overwrite is False.
        """
        timestamp = datetime.now(timezone.utc).isoformat()

        if path.exists() and not overwrite:
            raise FileExistsError(
                f"File already exists: {path}. Pass overwrite=True to replace with trace."
            )

        if path.exists() and overwrite:
            # Move existing to .bak before overwriting (data integrity rule)
            backup = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, backup)
            log.info("file_storage.backup_created", original=str(path), backup=str(backup))

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        log_action(
            log,
            what=f"Wrote file: {path}",
            when=timestamp,
            why=why,
            changed=f"File written: {path} ({len(content)} bytes)",
            agent_id=agent_id,
        )

import json
import hashlib

class PostHistory:
    """
    Track published posts to enforce reuse rules (e.g. 60-day rule).
    Stores history in a local JSON file.
    """

    HISTORY_FILE = Path("logs/post_history.json")

    def __init__(self, history_file: Optional[Path] = None) -> None:
        self.history_file = history_file or self.HISTORY_FILE
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self._save_history([])

    def _load_history(self) -> dict:
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list): # Migration from old format
                    return {"posts": data, "rotation_index": 0}
                return data
        except (Exception, json.JSONDecodeError):
            return {"posts": [], "rotation_index": 0}

    def _save_history(self, history: dict) -> None:
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)

    def add_post(self, content: str, source_id: str, platform: str = "bluesky") -> None:
        """Record a successful publication and advance rotation."""
        history = self._load_history()
        history["posts"].append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_hash": hashlib.md5(content.strip().encode('utf-8')).hexdigest(),
            "source_id": source_id,
            "platform": platform
        })
        # Advance rotation index
        rotation_list = os.environ.get("POSTING_ROTATION", "Substack,Service,Podcast,Service,Evergreen").split(",")
        history["rotation_index"] = (history.get("rotation_index", 0) + 1) % len(rotation_list)
        
        self._save_history(history)

    def get_current_category(self) -> str:
        """Determine what category we should post next based on index."""
        history = self._load_history()
        rotation_list = os.environ.get("POSTING_ROTATION", "Substack,Service,Podcast,Service,Evergreen").split(",")
        idx = history.get("rotation_index", 0)
        return rotation_list[idx]

    def is_duplicate(self, content: str, days: int = 60) -> bool:
        """Check if similar content was published in the last N days."""
        history = self._load_history()
        now = datetime.now(timezone.utc)
        content_hash = hashlib.md5(content.strip().encode('utf-8')).hexdigest()

        for entry in history.get("posts", []):
            ts = datetime.fromisoformat(entry["timestamp"])
            if (now - ts).days < days:
                if entry["content_hash"] == content_hash:
                    return True
        return False


