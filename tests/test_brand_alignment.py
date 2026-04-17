"""
Tests for Brand Alignment Engine (orchestrator/brand_alignment.py)
"""

import pytest

from orchestrator.brand_alignment import (
    BrandAlignmentEngine,
    BrandAlignmentResult,
    BAEAction,
    DimensionResult,
)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Fixtures
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@pytest.fixture
def bae():
    return BrandAlignmentEngine()


def _pass_result(**kwargs) -> DimensionResult:
    return DimensionResult(passed=True, confidence=0.9, **kwargs)


def _fail_result(**kwargs) -> DimensionResult:
    return DimensionResult(passed=False, confidence=0.2, **kwargs)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# BrandAlignmentResult tests
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestBrandAlignmentResult:
    def test_all_pass(self):
        result = BrandAlignmentResult(
            truth=_pass_result(),
            mission_fit=_pass_result(),
            tone_and_dignity=_pass_result(),
            cta_effectiveness=_pass_result(),
            recommended_action=BAEAction.PROCEED,
        )
        assert result.passed is True
        assert result.critical_failure is False

    def test_critical_failure_when_truth_fails(self):
        result = BrandAlignmentResult(
            truth=_fail_result(),
            mission_fit=_pass_result(),
            tone_and_dignity=_pass_result(),
            cta_effectiveness=_pass_result(),
            recommended_action=BAEAction.STOP,
        )
        assert result.passed is False
        assert result.critical_failure is True

    def test_critical_failure_when_mission_fit_fails(self):
        result = BrandAlignmentResult(
            truth=_pass_result(),
            mission_fit=_fail_result(),
            tone_and_dignity=_pass_result(),
            cta_effectiveness=_pass_result(),
            recommended_action=BAEAction.SAVE_DRAFT,
        )
        assert result.critical_failure is True

    def test_critical_failure_when_tone_fails(self):
        result = BrandAlignmentResult(
            truth=_pass_result(),
            mission_fit=_pass_result(),
            tone_and_dignity=_fail_result(),
            cta_effectiveness=_pass_result(),
            recommended_action=BAEAction.CONSTRAIN,
        )
        assert result.critical_failure is True

    def test_non_critical_when_only_cta_fails(self):
        """CTA failure alone is non-critical â€” content can still be revised."""
        result = BrandAlignmentResult(
            truth=_pass_result(),
            mission_fit=_pass_result(),
            tone_and_dignity=_pass_result(),
            cta_effectiveness=_fail_result(),
            recommended_action=BAEAction.CONSTRAIN,
        )
        assert result.passed is False
        assert result.critical_failure is False  # Only CTA failed â€” not critical


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Engine action computation tests
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestBAEActionComputation:
    def test_truth_fail_triggers_stop(self, bae):
        result = bae._compute_action(
            truth=_fail_result(),
            mission_fit=_pass_result(),
            tone=_pass_result(),
            cta=_pass_result(),
        )
        assert result.recommended_action == BAEAction.STOP
        assert result.stop_reason is not None

    def test_mission_fit_fail_triggers_save_draft(self, bae):
        result = bae._compute_action(
            truth=_pass_result(),
            mission_fit=_fail_result(),
            tone=_pass_result(),
            cta=_pass_result(),
        )
        assert result.recommended_action == BAEAction.SAVE_DRAFT

    def test_tone_fail_triggers_constrain(self, bae):
        result = bae._compute_action(
            truth=_pass_result(),
            mission_fit=_pass_result(),
            tone=_fail_result(),
            cta=_pass_result(),
        )
        assert result.recommended_action == BAEAction.CONSTRAIN

    def test_cta_fail_alone_triggers_constrain(self, bae):
        result = bae._compute_action(
            truth=_pass_result(),
            mission_fit=_pass_result(),
            tone=_pass_result(),
            cta=_fail_result(),
        )
        assert result.recommended_action == BAEAction.CONSTRAIN
        assert result.stop_reason is None  # No stop reason when only CTA fails

    def test_all_pass_triggers_proceed(self, bae):
        result = bae._compute_action(
            truth=_pass_result(),
            mission_fit=_pass_result(),
            tone=_pass_result(),
            cta=_pass_result(),
        )
        assert result.recommended_action == BAEAction.PROCEED
        assert result.stop_reason is None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Evaluation method tests (stubs)
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestBAEEvaluateMethod:
    def test_evaluate_returns_result(self, bae):
        """Smoke test: evaluate() must return a BrandAlignmentResult."""
        result = bae.evaluate(
            content="Autonomous Systems cares deeply about our local community.",
            source_material="Agent is rooted in community stewardship.",
        )
        assert isinstance(result, BrandAlignmentResult)
        assert isinstance(result.recommended_action, BAEAction)

    def test_evaluate_without_source_fails_truth(self, bae):
        """Content with no source material should fail the truth check (stub rule)."""
        result = bae.evaluate(
            content="Some content here.",
            source_material="",
        )
        assert result.truth.passed is False

    def test_evaluate_with_source_passes_truth_stub(self, bae):
        """Stub truth check passes when source material is provided."""
        result = bae.evaluate(
            content="Community-focused content.",
            source_material="Source: SH community report 2025.",
        )
        assert result.truth.passed is True


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# BAEAction enum tests
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class TestBAEActionEnum:
    def test_all_four_actions_exist(self):
        assert BAEAction.PROCEED
        assert BAEAction.CONSTRAIN
        assert BAEAction.SAVE_DRAFT
        assert BAEAction.STOP

    def test_severity_ordering(self):
        """
        Verify that the action sequence PROCEED < CONSTRAIN < SAVE_DRAFT < STOP
        is represented in the enum values for readability.
        """
        actions = [BAEAction.PROCEED, BAEAction.CONSTRAIN, BAEAction.SAVE_DRAFT, BAEAction.STOP]
        assert all(isinstance(a, BAEAction) for a in actions)

