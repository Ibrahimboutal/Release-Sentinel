"""
Semantic failure triage using LLM models with heuristic fallback.

Provides optional LLM-based classification of test failures when heuristic
patterns don't match. Falls back gracefully to heuristic-only mode if LLM
is not configured or available.
"""

from __future__ import annotations

import logging
import os
from typing import Literal

log = logging.getLogger(__name__)


class LLMClient:
    """Lightweight LLM client for semantic failure classification."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        provider: Literal["openai", "anthropic"] = "openai",
    ) -> None:
        """
        Initialize LLM client.

        Args:
            model: Model identifier (e.g., 'gpt-4', 'claude-3-opus')
            api_key: API key for the model provider
            provider: LLM provider ('openai' or 'anthropic')
        """
        self.model = model or os.getenv("RELEASE_SENTINEL_LLM_MODEL", "")
        self.api_key = api_key or os.getenv("RELEASE_SENTINEL_LLM_API_KEY", "")
        self.provider = provider
        self.is_available = bool(self.model and self.api_key)

        if self.is_available:
            log.info("LLM semantic triage enabled (model=%s, provider=%s)", self.model, self.provider)
        else:
            log.info("LLM semantic triage disabled; will use heuristic-only classification")

    def classify_failure(
        self,
        error_message: str,
        test_case_name: str,
        context: str = "",
    ) -> dict[str, str | float] | None:
        """
        Semantically classify a test failure using LLM.

        Args:
            error_message: The error/log message to classify
            test_case_name: Name of the test case
            context: Additional context about the change

        Returns:
            Dictionary with 'category', 'confidence', 'reasoning' or None if LLM unavailable
        """
        if not self.is_available:
            return None

        try:
            if self.provider == "openai":
                return self._classify_with_openai(error_message, test_case_name, context)
            elif self.provider == "anthropic":
                return self._classify_with_anthropic(error_message, test_case_name, context)
        except Exception as e:
            log.warning("LLM classification failed, falling back to heuristics: %s", e)
            return None

        return None

    def _classify_with_openai(
        self,
        error_message: str,
        test_case_name: str,
        context: str,
    ) -> dict[str, str | float] | None:
        """Classify failure using OpenAI API."""
        try:
            import httpx
        except ImportError:
            log.warning("httpx not installed; LLM classification requires httpx")
            return None

        prompt = self._build_prompt(error_message, test_case_name, context)

        try:
            with httpx.Client() as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"******",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 500,
                        "temperature": 0.2,
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                return self._parse_classification(content)
        except Exception as e:
            log.warning("OpenAI API call failed: %s", e)
            return None

    def _classify_with_anthropic(
        self,
        error_message: str,
        test_case_name: str,
        context: str,
    ) -> dict[str, str | float] | None:
        """Classify failure using Anthropic API."""
        try:
            import httpx
        except ImportError:
            log.warning("httpx not installed; LLM classification requires httpx")
            return None

        prompt = self._build_prompt(error_message, test_case_name, context)

        try:
            with httpx.Client() as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 500,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=10.0,
                )
                response.raise_for_status()
                result = response.json()
                content = result["content"][0]["text"]
                return self._parse_classification(content)
        except Exception as e:
            log.warning("Anthropic API call failed: %s", e)
            return None

    @staticmethod
    def _build_prompt(error_message: str, test_case_name: str, context: str) -> str:
        """Build prompt for LLM classification."""
        return f"""Classify this test failure into one of these categories:
- product_bug: The error indicates a defect in the product code
- test_fragility: The error is due to brittle/flaky test (e.g., UI selectors)
- test_data_issue: The error is due to missing or stale test data
- environment_issue: The error is due to environment/infrastructure (timeouts, resource limits)
- needs_human_review: Cannot confidently classify; requires human review

Test Case: {test_case_name}
Error Message: {error_message}
{f'Additional Context: {context}' if context else ''}

Respond with a JSON object: {{"category": "<category>", "confidence": <0.0-1.0>, "reasoning": "<brief explanation>"}}
"""

    @staticmethod
    def _parse_classification(response_text: str) -> dict[str, str | float] | None:
        """Parse LLM response into classification dict."""
        try:
            import json

            # Try to extract JSON from the response
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response_text[start:end]
                parsed = json.loads(json_str)
                # Validate the response has required fields
                if "category" in parsed and "confidence" in parsed:
                    return parsed
        except Exception as e:
            log.debug("Failed to parse LLM response: %s", e)

        return None


def get_llm_client(
    model: str | None = None,
    api_key: str | None = None,
    provider: Literal["openai", "anthropic"] = "openai",
) -> LLMClient:
    """Create an LLM client for semantic failure classification."""
    return LLMClient(model=model, api_key=api_key, provider=provider)
