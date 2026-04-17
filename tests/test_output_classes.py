"""
Tests for Output Classes (orchestrator/output_classes.py)
"""

import pytest

from orchestrator.output_classes import (
    OutputClass,
    OutputClassMeta,
    OUTPUT_CLASS_REGISTRY,
    get_meta,
    requires_bae,
    is_publishable,
)


class TestOutputClassEnum:
    def test_all_four_classes_exist(self):
        assert OutputClass.INTERNAL_REASONING
        assert OutputClass.INTERNAL_OPERATIONAL
        assert OutputClass.CLIENT_FACING_DRAFT
        assert OutputClass.PUBLIC_FACING_PUBLISHED

    def test_enum_values_are_strings(self):
        for cls in OutputClass:
            assert isinstance(cls.value, str)

    def test_all_classes_in_registry(self):
        for cls in OutputClass:
            assert cls in OUTPUT_CLASS_REGISTRY, f"Missing registry entry: {cls}"


class TestOutputClassMeta:
    def test_registry_has_correct_types(self):
        for cls, meta in OUTPUT_CLASS_REGISTRY.items():
            assert isinstance(meta, OutputClassMeta)
            assert isinstance(meta.risk_tolerance, str)
            assert isinstance(meta.bae_required, bool)
            assert isinstance(meta.human_review_required, bool)
            assert isinstance(meta.may_be_published, bool)

    def test_get_meta_returns_correct_type(self):
        meta = get_meta(OutputClass.INTERNAL_REASONING)
        assert isinstance(meta, OutputClassMeta)
        assert meta.output_class == OutputClass.INTERNAL_REASONING

    def test_get_meta_all_classes(self):
        for cls in OutputClass:
            meta = get_meta(cls)
            assert meta.output_class == cls


class TestBAERequirements:
    def test_internal_reasoning_does_not_require_bae(self):
        assert requires_bae(OutputClass.INTERNAL_REASONING) is False

    def test_internal_operational_does_not_require_bae(self):
        assert requires_bae(OutputClass.INTERNAL_OPERATIONAL) is False

    def test_client_facing_draft_requires_bae(self):
        assert requires_bae(OutputClass.CLIENT_FACING_DRAFT) is True

    def test_public_facing_published_requires_bae(self):
        assert requires_bae(OutputClass.PUBLIC_FACING_PUBLISHED) is True


class TestPublishability:
    def test_only_public_facing_is_publishable(self):
        assert is_publishable(OutputClass.PUBLIC_FACING_PUBLISHED) is True

    def test_internal_reasoning_not_publishable(self):
        assert is_publishable(OutputClass.INTERNAL_REASONING) is False

    def test_internal_operational_not_publishable(self):
        assert is_publishable(OutputClass.INTERNAL_OPERATIONAL) is False

    def test_client_facing_draft_not_publishable(self):
        assert is_publishable(OutputClass.CLIENT_FACING_DRAFT) is False


class TestRiskTolerance:
    def test_risk_tolerances_in_order(self):
        """
        INTERNAL_REASONING should have highest tolerance,
        PUBLIC_FACING_PUBLISHED should have minimal tolerance.
        """
        tolerances = [
            get_meta(OutputClass.INTERNAL_REASONING).risk_tolerance,
            get_meta(OutputClass.INTERNAL_OPERATIONAL).risk_tolerance,
            get_meta(OutputClass.CLIENT_FACING_DRAFT).risk_tolerance,
            get_meta(OutputClass.PUBLIC_FACING_PUBLISHED).risk_tolerance,
        ]
        # All should be set (non-empty)
        assert all(t for t in tolerances)
        # Highest risk tolerance is 'high' (internal reasoning)
        assert tolerances[0] == "high"
        # Minimal risk tolerance is 'minimal' (public published)
        assert tolerances[3] == "minimal"
