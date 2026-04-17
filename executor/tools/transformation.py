"""
Transformation / Generation Tools — Layer 3: Execution

Tool Class 2: Transformation / Generation Tools (from CLAUDE.md)

Approved tools:
    - OpenAI (text generation, summarization, rewriting)
    - Formatting utilities
    - Text processors

Execution principles:
    - Keep actions deterministic (use temperature carefully)
    - Avoid improvisation — trust the directive for prompting
    - Ensure repeatability — log inputs and outputs
"""

from __future__ import annotations

import os
from typing import Optional

from executor.tools.logging_tool import get_logger

log = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# OpenAI Client
# ──────────────────────────────────────────────────────────────────────────────

class OpenAIClient:
    """
    Wrapper for OpenAI text generation.

    Enforces:
    - Logging of all prompts and responses (for auditability)
    - Temperature respected from config
    - Source material passed as system context to ground responses

    TODO: Implement using the openai Python SDK.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> None:
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("OPENAI_DEFAULT_MODEL", "gpt-4o")
        self.temperature = float(os.environ.get("OPENAI_TEMPERATURE", str(temperature)))

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        source_material: str = "",
        max_tokens: int = 2000,
    ) -> str:
        """
        Run a completion with an optional source material context.
        """
        log.info(
            "openai.complete",
            model=self.model,
            temperature=self.temperature,
            user_prompt_length=len(user_prompt),
        )

        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        
        source_context = f"\n\nSOURCE MATERIAL:\n{source_material}" if source_material else ""
        
        messages = [
            {"role": "system", "content": system_prompt + source_context},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=max_tokens,
            )
            
            # Extract token details and log tracking
            if hasattr(response, 'usage') and response.usage:
                prompt_tokens = response.usage.prompt_tokens
                completion_tokens = response.usage.completion_tokens
                
                # Import logger dynamically
                import sys, os
                ag_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
                if ag_root not in sys.path:
                    sys.path.append(ag_root)
                try:
                    from scripts.token_logger import log_openai_usage
                    log_openai_usage(prompt_tokens, completion_tokens, self.model)
                except ImportError as ie:
                    log.error("Failed to import token logger", error=str(ie))
            
            content = response.choices[0].message.content
            return content or ""
        except Exception as e:
            # Handle standard OpenAI exceptions for better visibility
            err_msg = str(e)
            if "auth" in err_msg.lower() or "401" in err_msg:
                log.error("openai.auth_failed", error="Invalid/Expired API Key")
                return "ERROR_AUTH_FAILED: Please check your OPENAI_API_KEY in the .env file."
            
            log.error("openai.complete_failed", error=err_msg)
            raise

    def summarize(self, text: str, max_words: int = 150) -> str:
        """
        Summarize text to a target word count.
        """
        system_prompt = f"Summarize the following text concisely in under {max_words} words. Maintain a professional, grounded tone."
        return self.complete(system_prompt, text)


# ──────────────────────────────────────────────────────────────────────────────
# Text Formatting Utilities
# ──────────────────────────────────────────────────────────────────────────────

class TextFormatter:
    """
    Deterministic text formatting utilities.
    """

    @staticmethod
    def markdown_to_plain(text: str) -> str:
        """
        Strip Markdown formatting to produce plain text.
        """
        import re
        # Basic markdown stripping (headers, bold, italic, links)
        text = re.sub(r'#+\s+', '', text)
        text = re.sub(r'\*+(.*?)\*+', r'\1', text)
        text = re.sub(r'_+(.*?)_+', r'\1', text)
        text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)
        text = re.sub(r'`+(.*?)`+', r'\1', text)
        return text

    @staticmethod
    def truncate_to_chars(text: str, max_chars: int, ellipsis: str = "…") -> str:
        """
        Truncate text to max_chars, breaking at word boundary.
        """
        if len(text) <= max_chars:
            return text
        # Find the last space before max_chars
        space_idx = text.rfind(" ", 0, max_chars - len(ellipsis))
        if space_idx == -1:
            truncated = text[: max_chars - len(ellipsis)]
        else:
            truncated = text[:space_idx]
        return truncated + ellipsis

    @staticmethod
    def strip_html(html: str) -> str:
        """
        Remove HTML tags from a string.
        """
        import re
        clean = re.compile('<.*?>')
        return re.sub(clean, '', html)


    @staticmethod
    def word_count(text: str) -> int:
        """Return the word count of a string."""
        return len(text.split())
