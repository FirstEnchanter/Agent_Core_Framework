"""
State Memory Tool  Layer 3: Tracking
Ensures the agent doesn't repeat work on the same items.
"""

import json
import os
from typing import List, Set
from executor.tools.logging_tool import get_logger

log = get_logger(__name__)

class TriageHistory:
    """
    Persistent store for seen email IDs.
    """
    def __init__(self, filename: str = "data/triage_history.json"):
        self.filename = filename
        self.seen_ids: Set[str] = set()
        self._load()

    def _load(self):
        """Loads seen IDs from disk."""
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    data = json.load(f)
                    self.seen_ids = set(data)
                log.info("history.loaded", count=len(self.seen_ids))
            except Exception as e:
                log.error("history.load_failed", error=str(e))

    def _save(self):
        """Saves current memory to disk."""
        try:
            os.makedirs(os.path.dirname(self.filename), exist_ok=True)
            with open(self.filename, 'w') as f:
                json.dump(list(self.seen_ids), f)
        except Exception as e:
            log.error("history.save_failed", error=str(e))

    def is_new(self, email_id: str) -> bool:
        """Checks if an ID is new and tracks it if so."""
        if email_id in self.seen_ids:
            return False
        
        self.seen_ids.add(email_id)
        self._save()
        return True

    def clear(self):
        """Reset the memory."""
        self.seen_ids = set()
        self._save()
