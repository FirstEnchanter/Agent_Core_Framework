"""
Executor — Layer 3: Execution

This package performs deterministic actions.

It is NOT responsible for reasoning — that is the orchestrator's job.
It executes reliably using tools, scripts, and external systems.

Principles (from CLAUDE.md):
    - Prefer tools over manual logic
    - Keep actions deterministic
    - Avoid improvisation
    - Ensure repeatability
"""

from executor.tools.logging_tool import get_logger

__all__ = ["get_logger"]
