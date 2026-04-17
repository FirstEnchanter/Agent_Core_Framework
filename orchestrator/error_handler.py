"""
Error Handler & Escalation  Layer 2: Orchestration

Handles errors, self-correction attempts, and escalation when
the system cannot resolve an issue autonomously.

Self-correction sequence (from CLAUDE.md):
    1. Identify the issue
    2. Attempt correction
    3. Retry if safe
    4. If unresolved: downgrade output OR stop and save draft
    Then: log error, update directive if needed, improve future behavior

Escalation triggers:
    - Truth cannot be verified
    - Mission fit is unclear
    - Failure cannot be resolved
    - System risks fabricating or misrepresenting

Default escalation action: save draft  log issue  notify user
"""

from __future__ import annotations

import os
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from executor.tools.logging_tool import get_logger

log = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


# 
# Types
# 

class FailureType(str, Enum):
    TRUTH_UNVERIFIABLE   = "truth_unverifiable"
    MISSION_FIT_UNCLEAR  = "mission_fit_unclear"
    TOOL_ERROR           = "tool_error"
    DIRECTIVE_INVALID    = "directive_invalid"
    BAE_FAILURE          = "bae_failure"
    UNEXPECTED           = "unexpected"


class ResolutionState(str, Enum):
    RESOLVED          = "resolved"
    DOWNGRADED        = "downgraded"    # Output class lowered, operation continued
    DRAFT_SAVED       = "draft_saved"   # Stopped, saved draft for human review
    ESCALATED         = "escalated"     # Sent to human for decision
    UNRESOLVED        = "unresolved"    # Could not self-correct


@dataclass
class EscalationPayload:
    """Structured payload sent when the system must escalate."""
    failure_type: FailureType
    directive_id: str
    agent_id: str
    timestamp: str
    error_message: str
    attempted_fix: str
    final_state: ResolutionState
    draft_path: Optional[str] = None
    context: dict = field(default_factory=dict)
    traceback: str = ""


# 
# Handler
# 

class ErrorHandler:
    """
    Handles errors and escalation within the orchestration layer.

    Usage:
        handler = ErrorHandler(directive_id="publish-bluesky-post")

        with handler.guard():
            # risky operation
            ...

        # Or manually:
        handler.attempt_correction(lambda: retry_operation(), context={...})
    """

    ESCALATION_TRIGGERS = {
        FailureType.TRUTH_UNVERIFIABLE,
        FailureType.MISSION_FIT_UNCLEAR,
    }

    MAX_RETRIES = 2

    def __init__(
        self,
        directive_id: str = "unknown",
        agent_id: Optional[str] = None,
        drafts_dir: Optional[Path] = None,
    ) -> None:
        self.directive_id = directive_id
        self.agent_id = agent_id or os.environ.get("AGENT_ID", "agent-unknown")
        self.drafts_dir = drafts_dir or Path(os.environ.get("DRAFTS_DIR", "drafts"))

    def handle(
        self,
        exc: Exception,
        failure_type: FailureType = FailureType.UNEXPECTED,
        context: Optional[dict] = None,
        draft_content: Optional[str] = None,
    ) -> EscalationPayload:
        """
        Standard error handling entry point.

        1. Identify the issue
        2. Determine if it is an escalation trigger
        3. Save draft if content exists
        4. Log full error state
        5. Return EscalationPayload for caller to act on

        Args:
            exc:           The exception that was raised.
            failure_type:  Classified failure type.
            context:       Optional metadata about the operation.
            draft_content: If provided, saved to drafts/ before escalating.

        Returns:
            EscalationPayload describing the final state.
        """
        tb = traceback.format_exc()
        timestamp = datetime.now(timezone.utc).isoformat()
        draft_path: Optional[str] = None

        log.error(
            "error_handler.failure_detected",
            directive_id=self.directive_id,
            failure_type=failure_type.value,
            error=str(exc),
        )

        # Save draft if we have content
        if draft_content:
            draft_path = self._save_draft(draft_content, failure_type, timestamp)

        # Determine resolution state
        if failure_type in self.ESCALATION_TRIGGERS:
            final_state = ResolutionState.ESCALATED
        else:
            final_state = ResolutionState.DRAFT_SAVED if draft_path else ResolutionState.UNRESOLVED

        payload = EscalationPayload(
            failure_type=failure_type,
            directive_id=self.directive_id,
            agent_id=self.agent_id,
            timestamp=timestamp,
            error_message=str(exc),
            attempted_fix="",
            final_state=final_state,
            draft_path=draft_path,
            context=context or {},
            traceback=tb,
        )

        log.error(
            "error_handler.escalation_payload_created",
            final_state=final_state.value,
            draft_path=draft_path,
        )

        # TODO: Notify user/steward (email, webhook) when escalated
        if final_state == ResolutionState.ESCALATED:
            self._notify(payload)

        return payload

    def attempt_correction(
        self,
        operation: Callable[[], Any],
        failure_type: FailureType = FailureType.UNEXPECTED,
        context: Optional[dict] = None,
        draft_content: Optional[str] = None,
    ) -> tuple[bool, Any, Optional[EscalationPayload]]:
        """
        Attempt an operation with automatic retry and self-correction.

        Returns:
            (success, result, escalation_payload)
            If successful: (True, result, None)
            If failed after retries: (False, None, EscalationPayload)
        """
        last_exc: Optional[Exception] = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                log.info(
                    "error_handler.attempt",
                    attempt=attempt,
                    max_retries=self.MAX_RETRIES,
                    directive_id=self.directive_id,
                )
                result = operation()
                log.info("error_handler.attempt_succeeded", attempt=attempt)
                return True, result, None

            except Exception as exc:
                last_exc = exc
                log.warning(
                    "error_handler.attempt_failed",
                    attempt=attempt,
                    error=str(exc),
                )

        # All retries exhausted
        payload = self.handle(
            exc=last_exc or RuntimeError("Unknown failure"),
            failure_type=failure_type,
            context=context,
            draft_content=draft_content,
        )
        return False, None, payload

    def _save_draft(
        self, content: str, failure_type: FailureType, timestamp: str
    ) -> str:
        """Save content to the drafts directory with error annotation."""
        self.drafts_dir.mkdir(parents=True, exist_ok=True)
        safe_ts = timestamp.replace(":", "-").replace(".", "-")
        filename = f"draft_{self.directive_id}_{failure_type.value}_{safe_ts}.md"
        path = self.drafts_dir / filename

        annotated = (
            f"<!-- DRAFT  Saved by ErrorHandler -->\n"
            f"<!-- Directive: {self.directive_id} -->\n"
            f"<!-- Failure: {failure_type.value} -->\n"
            f"<!-- Timestamp: {timestamp} -->\n"
            f"<!-- Agent: {self.agent_id} -->\n\n"
            f"{content}"
        )

        path.write_text(annotated, encoding="utf-8")
        log.info("error_handler.draft_saved", path=str(path))
        return str(path)

    def _notify(self, payload: EscalationPayload) -> None:
        """
        Notify the steward of an escalation event.

        TODO: Implement email/webhook notification using SMTP or webhook config.
        Currently logs only.
        """
        log.warning(
            "error_handler.escalation_required",
            directive_id=payload.directive_id,
            failure_type=payload.failure_type.value,
            message="[STUB] Escalation notification not yet implemented. "
                    "Operator must review logs and drafts manually.",
        )
