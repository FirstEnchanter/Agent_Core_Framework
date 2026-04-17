"""
Output Classes — Layer 2: Orchestration

Defines the 4 output classes that all agent outputs must belong to.
Each class carries an associated risk tolerance that governs what
checks are required before proceeding.

Output Classes (from CLAUDE.md):
    1. INTERNAL_REASONING       — Hidden logic, evaluations, intermediate thinking
    2. INTERNAL_OPERATIONAL     — System updates, logs, structured data
    3. CLIENT_FACING_DRAFT      — Content prepared but not yet public
    4. PUBLIC_FACING_PUBLISHED  — Final, visible content
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class OutputClass(str, Enum):
    """
    Canonical output class enumeration.

    Agents must classify every output before processing.
    The class determines which checks are mandatory.
    """

    INTERNAL_REASONING = "INTERNAL_REASONING"
    INTERNAL_OPERATIONAL = "INTERNAL_OPERATIONAL"
    CLIENT_FACING_DRAFT = "CLIENT_FACING_DRAFT"
    PUBLIC_FACING_PUBLISHED = "PUBLIC_FACING_PUBLISHED"


@dataclass(frozen=True)
class OutputClassMeta:
    """Metadata and risk profile for a given output class."""

    output_class: OutputClass
    description: str
    risk_tolerance: str          # "high" | "medium" | "low" | "minimal"
    bae_required: bool           # Brand Alignment Engine check required?
    human_review_required: bool  # Must escalate to human before proceeding?
    may_be_published: bool       # Can this class of output be made public?

    def __str__(self) -> str:
        return (
            f"OutputClass({self.output_class.value}, "
            f"risk={self.risk_tolerance}, "
            f"bae={self.bae_required})"
        )


# ──────────────────────────────────────────────────────────────────────────────
# Output class registry
# ──────────────────────────────────────────────────────────────────────────────

OUTPUT_CLASS_REGISTRY: dict[OutputClass, OutputClassMeta] = {
    OutputClass.INTERNAL_REASONING: OutputClassMeta(
        output_class=OutputClass.INTERNAL_REASONING,
        description="Hidden logic, evaluations, and intermediate thinking. Never surfaced externally.",
        risk_tolerance="high",
        bae_required=False,
        human_review_required=False,
        may_be_published=False,
    ),
    OutputClass.INTERNAL_OPERATIONAL: OutputClassMeta(
        output_class=OutputClass.INTERNAL_OPERATIONAL,
        description="System updates, logs, and structured data. Internal tooling only.",
        risk_tolerance="medium",
        bae_required=False,
        human_review_required=False,
        may_be_published=False,
    ),
    OutputClass.CLIENT_FACING_DRAFT: OutputClassMeta(
        output_class=OutputClass.CLIENT_FACING_DRAFT,
        description="Content prepared but not yet published. Requires review before going public.",
        risk_tolerance="low",
        bae_required=True,
        human_review_required=False,
        may_be_published=False,
    ),
    OutputClass.PUBLIC_FACING_PUBLISHED: OutputClassMeta(
        output_class=OutputClass.PUBLIC_FACING_PUBLISHED,
        description="Final, visible content. Full BAE check mandatory. Highest integrity standard.",
        risk_tolerance="minimal",
        bae_required=True,
        human_review_required=False,  # Set to True for sensitive campaigns
        may_be_published=True,
    ),
}


def get_meta(output_class: OutputClass) -> OutputClassMeta:
    """Return the metadata for the given output class."""
    return OUTPUT_CLASS_REGISTRY[output_class]


def requires_bae(output_class: OutputClass) -> bool:
    """Return True if the Brand Alignment Engine check is required for this class."""
    return OUTPUT_CLASS_REGISTRY[output_class].bae_required


def is_publishable(output_class: OutputClass) -> bool:
    """Return True if this output class can be made public."""
    return OUTPUT_CLASS_REGISTRY[output_class].may_be_published
