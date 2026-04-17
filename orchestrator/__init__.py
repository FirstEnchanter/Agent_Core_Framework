"""
Orchestrator — Layer 2: Decision-Making

This package is the bridge between intention (directives) and action (execution).

Responsibilities:
- Read and interpret directives
- Route execution to Layer 3 tools
- Enforce brand alignment before any public output
- Handle errors, escalation, and self-correction
- Maintain system alignment over time
"""

from orchestrator.brand_alignment import BrandAlignmentEngine, BrandAlignmentResult
from orchestrator.output_classes import OutputClass, OutputClassMeta
from orchestrator.router import Router, DirectiveValidationResult
from orchestrator.error_handler import ErrorHandler, EscalationPayload

__all__ = [
    "BrandAlignmentEngine",
    "BrandAlignmentResult",
    "OutputClass",
    "OutputClassMeta",
    "Router",
    "DirectiveValidationResult",
    "ErrorHandler",
    "EscalationPayload",
]
