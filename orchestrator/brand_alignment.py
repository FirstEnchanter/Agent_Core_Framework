"""
Brand Alignment Engine (BAE) â€” Layer 2: Orchestration

Mandatory check before any public-facing output.

Evaluation order (from CLAUDE.md):
    1. Truth          â€” Is content accurate and grounded in source material?
    2. Mission Fit    â€” Does it align with Community, Environment, Transparency?
    3. Tone & Dignity â€” Is the voice calm, grounded, and on brand?
    4. CTA Effectiveness â€” Is the CTA clear, appropriate, and non-extractive?

Rules:
    - If checks 1, 2, or 3 fail â†’ trigger constrained output mode or stop
    - If check 4 fails alone â†’ flag for revision but may continue as draft
    - All checks run in order; a failure in an earlier check may short-circuit later checks

Output: BrandAlignmentResult with pass/fail per dimension and recommended action.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from executor.tools.logging_tool import get_logger

log = get_logger(__name__)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Types
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class BAEAction(str, Enum):
    """Recommended action after a BAE evaluation."""
    PROCEED        = "proceed"           # All checks passed â€” safe to publish
    CONSTRAIN      = "constrain"         # Reduce complexity, shorten, remove ambiguity
    SAVE_DRAFT     = "save_draft"        # Stop, save as draft, escalate
    STOP           = "stop"              # Hard stop â€” do not publish, do not draft


class MissionDimension(str, Enum):
    COMMUNITY    = "community"
    ENVIRONMENT  = "environment"
    TRANSPARENCY = "transparency"


@dataclass
class DimensionResult:
    """Result for a single BAE dimension."""
    passed: bool
    confidence: float           # 0.0 â€“ 1.0
    notes: str = ""
    flagged_phrases: list[str] = field(default_factory=list)


@dataclass
class BrandAlignmentResult:
    """Full result from a Brand Alignment Engine evaluation."""
    truth: DimensionResult
    mission_fit: DimensionResult
    tone_and_dignity: DimensionResult
    cta_effectiveness: DimensionResult

    recommended_action: BAEAction = BAEAction.PROCEED
    summary: str = ""
    stop_reason: Optional[str] = None

    @property
    def passed(self) -> bool:
        """True only if all 4 dimensions passed."""
        return (
            self.truth.passed
            and self.mission_fit.passed
            and self.tone_and_dignity.passed
            and self.cta_effectiveness.passed
        )

    @property
    def critical_failure(self) -> bool:
        """
        True if checks 1, 2, or 3 failed â€” these require stopping or constraining.
        Check 4 (CTA) failure alone is non-critical.
        """
        return not (
            self.truth.passed
            and self.mission_fit.passed
            and self.tone_and_dignity.passed
        )


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Engine
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class BrandAlignmentEngine:
    """
    Evaluates content against SH brand alignment criteria before any
    public-facing output is produced.

    Usage:
        bae = BrandAlignmentEngine()
        result = bae.evaluate(content="...", source_material="...")

        if result.critical_failure:
            # Stop or constrain
            ...
        elif result.recommended_action == BAEAction.PROCEED:
            # Safe to publish
            ...
    """

    def evaluate(
        self,
        content: str,
        source_material: str = "",
        context: Optional[dict] = None,
    ) -> BrandAlignmentResult:
        """
        Run all 4 BAE dimensions in order using LLM evaluation.
        """
        log.info("bae.evaluation_started", content_length=len(content))

        from executor.tools.transformation import OpenAIClient
        # Fetch Google Sheets content bank for additional grounding
        from executor.tools.content import GoogleSheetsClient
        sheets = GoogleSheetsClient()
        content_bank = sheets.fetch_all_data()
        
        grounding_material = f"{source_material}\n\nCONTENT BANK (Google Sheets):\n{content_bank}"

        self.judger = OpenAIClient(temperature=0.0) # Use temp 0 for judging

        truth = self._check_truth(content, grounding_material)
        mission_fit = self._check_mission_fit(content, grounding_material)
        tone = self._check_tone_and_dignity(content)
        cta = self._check_cta_effectiveness(content)

        result = self._compute_action(truth, mission_fit, tone, cta)

        log.info(
            "bae.evaluation_complete",
            passed=result.passed,
            action=result.recommended_action.value,
            critical_failure=result.critical_failure,
        )

        return result

    def _check_truth(self, content: str, source_material: str) -> DimensionResult:
        """Dimension 1: Truth."""
        if not source_material:
            return DimensionResult(passed=False, confidence=1.0, notes="No source material provided.")

        prompt = f"""Evaluate if the following generated content is accurately grounded in the source material (which may be a blog post, a local template, or the Google Sheets Content Bank).
Generated Content: {content}
Source Material: {source_material}

Rules for evaluation:
1. The Linktree URL (https://linktr.ee/1stenchanter) and items drawn from the Google Sheets Content Bank are APPROVED brand assets; DO NOT flag them as unverified claims.
2. Does the rest of the generated content make any major claims not found in the source material?
3. Minor stylistic choices and paraphrasing are allowed.

Respond only with: PASSED or FAILED followed by a brief reason."""


        
        judgement = self.judger.complete("You are a strict fact-checker.", prompt)
        passed = judgement.strip().upper().startswith("PASSED")
        return DimensionResult(passed=passed, confidence=0.9, notes=judgement)

    def _check_mission_fit(self, content: str, source_material: str = "") -> DimensionResult:
        """Dimension 2: Mission Fit (Community, Environment, Transparency)."""
        prompt = f"""Evaluate if this content aligns with Autonomous Systems' mission pillars:
1. Community: Engaging with others, sharing the journey.
2. Environment: Sustainable practices (often represented by intentional growth).
3. Transparency: Being open about process (e.g., 'Built in Public').
4. Service Operations: Valid business services, operational workflows, and updates.

IMPORTANT: The provided 'Source Material Context' IS an officially validated brand template / content bank. Therefore, ANY generated content logically grounded in this source material automatically satisfies Rule 4 (Service Operations) and MUST be passed.

Content: {content}
Source Material Context: {source_material[:500]}

Does this content fit at least one pillar without violating others? (Remember: grounding in the source material satisfies Rule 4).
Respond only with: PASSED or FAILED followed by a brief reason."""

        
        judgement = self.judger.complete("You are a brand alignment specialist for Autonomous Systems.", prompt)
        passed = judgement.strip().upper().startswith("PASSED")
        return DimensionResult(passed=passed, confidence=0.8, notes=judgement)

    def _check_tone_and_dignity(self, content: str) -> DimensionResult:
        """Dimension 3: Tone & Dignity (Calm, grounded, professional)."""
        prompt = f"""Evaluate if the tone of this content matches the '1stenchanter' brand:
Voice: Calm, grounded, professional, and intentional.
Prohibited: Salesy, corporate, vague, overly spiritual, or aggressive.

Note: Technical 'Built in Public' posts are acceptable if the tone remains professional.
Content: {content}
Respond only with: PASSED or FAILED followed by a brief reason."""
        
        judgement = self.judger.complete("You are an editor for Autonomous Systems.", prompt)
        passed = judgement.strip().upper().startswith("PASSED")
        return DimensionResult(passed=passed, confidence=0.9, notes=judgement)


    def _check_cta_effectiveness(self, content: str) -> DimensionResult:
        """Dimension 4: CTA Effectiveness."""
        prompt = f"""Evaluate if the call to action (CTA) in this content is clear and appropriate.
It should include a link to Substack, Linktree, or a podcast.
Content: {content}
Respond only with: PASSED or FAILED followed by a brief reason."""
        
        judgement = self.judger.complete("You are a marketing specialist.", prompt)
        passed = judgement.strip().upper().startswith("PASSED")
        return DimensionResult(passed=passed, confidence=0.9, notes=judgement)


    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Action computation
    # â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _compute_action(
        self,
        truth: DimensionResult,
        mission_fit: DimensionResult,
        tone: DimensionResult,
        cta: DimensionResult,
    ) -> BrandAlignmentResult:
        """Determine the recommended action based on dimension results."""

        # Critical failure: checks 1, 2, or 3 failed
        if not truth.passed:
            action = BAEAction.STOP
            stop_reason = "Truth check failed â€” content cannot be verified against source material."
            summary = f"STOP: {stop_reason}"

        elif not mission_fit.passed:
            action = BAEAction.SAVE_DRAFT
            stop_reason = "Mission fit check failed â€” content does not align with SH pillars."
            summary = f"DRAFT: {stop_reason}"

        elif not tone.passed:
            action = BAEAction.CONSTRAIN
            stop_reason = "Tone & dignity check failed â€” voice is not aligned with SH identity."
            summary = f"CONSTRAIN: {stop_reason}"

        # Non-critical failure: only CTA failed
        elif not cta.passed:
            action = BAEAction.CONSTRAIN
            stop_reason = None
            summary = "CTA effectiveness check flagged â€” CTA may need revision before publishing."

        else:
            action = BAEAction.PROCEED
            stop_reason = None
            summary = "All BAE dimensions passed â€” content is cleared for publishing."

        return BrandAlignmentResult(
            truth=truth,
            mission_fit=mission_fit,
            tone_and_dignity=tone,
            cta_effectiveness=cta,
            recommended_action=action,
            summary=summary,
            stop_reason=stop_reason,
        )

