"""
Thin model wrappers for the IBD scRNA eval suite.

Supported backends:
- claude   : Anthropic Claude via anthropic SDK
- openai   : OpenAI GPT via openai SDK
- mock     : Deterministic offline model for CI (returns correct answer for even-indexed
             tasks, wrong answer for odd-indexed tasks — enough to verify grading machinery)

Usage::

    from evals.harness.models import get_model
    model = get_model("mock")
    response = model.complete(prompt="What is 2+2?")
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseModel:
    def complete(self, prompt: str, **kwargs) -> str:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Anthropic Claude
# ---------------------------------------------------------------------------

class ClaudeModel(BaseModel):
    """
    Wrapper around the Anthropic Python SDK.

    Requires ANTHROPIC_API_KEY environment variable.
    Default model: claude-opus-4-5 (override via model_name argument or
    ANTHROPIC_MODEL env var).
    """

    def __init__(self, model_name: Optional[str] = None):
        try:
            import anthropic  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "anthropic package is required for the Claude model: pip install anthropic"
            ) from exc

        self._client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self._model = (
            model_name
            or os.environ.get("ANTHROPIC_MODEL")
            or "claude-opus-4-5"
        )

    def complete(self, prompt: str, max_tokens: int = 512, **kwargs) -> str:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text


# ---------------------------------------------------------------------------
# OpenAI
# ---------------------------------------------------------------------------

class OpenAIModel(BaseModel):
    """
    Wrapper around the OpenAI Python SDK.

    Requires OPENAI_API_KEY environment variable.
    Default model: gpt-4o (override via model_name argument or OPENAI_MODEL env var).
    """

    def __init__(self, model_name: Optional[str] = None):
        try:
            import openai  # type: ignore
        except ImportError as exc:
            raise ImportError(
                "openai package is required for the OpenAI model: pip install openai"
            ) from exc

        self._client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self._model = (
            model_name
            or os.environ.get("OPENAI_MODEL")
            or "gpt-4o"
        )

    def complete(self, prompt: str, max_tokens: int = 512, **kwargs) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""


# ---------------------------------------------------------------------------
# Mock model (offline, deterministic, no API keys required)
# ---------------------------------------------------------------------------

_WRONG_ANSWERS = {
    "mc_match": "A",        # Will be replaced with a wrong letter
    "numeric_tolerance": "0.00",
    "set_match": "none",
    "exact_match": "incorrect answer xyz",
}

_WRONG_MC_MAP = {"A": "D", "B": "A", "C": "B", "D": "C"}


class MockModel(BaseModel):
    """
    Deterministic mock model for CI without API keys.

    Strategy:
    - Tasks at even indices (0-based) → return the correct answer verbatim.
    - Tasks at odd indices             → return a deliberately wrong answer.

    This ensures ~50% pass rate and exercises both pass and fail paths in the
    grading machinery.

    Call `reset()` before each run to restart the counter.
    """

    def __init__(self):
        self._call_count = 0

    def reset(self):
        self._call_count = 0

    def complete_for_task(self, task) -> str:
        """Return canned answer based on task metadata and call index."""
        correct = task.correct
        grader = task.grader
        idx = self._call_count
        self._call_count += 1

        if idx % 2 == 0:
            # Even index → return correct answer
            return self._format_correct(correct, grader)
        else:
            # Odd index → return wrong answer
            return self._format_wrong(correct, grader)

    def complete(self, prompt: str, **kwargs) -> str:
        """Fallback for generic prompts — just echoes a placeholder."""
        return "mock_response"

    @staticmethod
    def _format_correct(correct, grader: str) -> str:
        from .schema import NumericCorrect, RubricSpec
        if grader == "mc_match":
            if isinstance(correct, str):
                return f"The answer is {correct}."
        if grader == "numeric_tolerance":
            if isinstance(correct, NumericCorrect):
                return f"The AUROC is {correct.value}."
            if isinstance(correct, dict):
                return f"The AUROC is {correct['value']}."
        if grader == "set_match":
            if isinstance(correct, list):
                return ", ".join(correct)
        if grader == "exact_match":
            return str(correct)
        if grader == "rubric_match":
            # Return a response that mentions the first keyword from each group
            if isinstance(correct, RubricSpec):
                keywords = [group[0] for group in correct.keyword_groups]
            elif isinstance(correct, dict):
                keywords = [group[0] for group in correct["keyword_groups"]]
            else:
                keywords = []
            return "The design has issues: " + "; ".join(keywords) + "."
        return str(correct)

    @staticmethod
    def _format_wrong(correct, grader: str) -> str:
        from .schema import NumericCorrect
        if grader == "mc_match":
            if isinstance(correct, str):
                letter = correct.upper().strip()
                wrong = _WRONG_MC_MAP.get(letter, "D")
                return f"The answer is {wrong}."
        if grader == "numeric_tolerance":
            return "The AUROC is 0.10."
        if grader == "set_match":
            return "stromal only"
        if grader == "exact_match":
            return "incorrect_placeholder_xyz"
        if grader == "rubric_match":
            return "The experiment looks fine, no issues identified."
        return "wrong answer"


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_model(name: str, model_name: Optional[str] = None) -> BaseModel:
    """
    Factory function.

    Args:
        name: one of 'claude', 'openai', 'mock'
        model_name: optional override for the specific model checkpoint

    Returns:
        A BaseModel instance
    """
    name = name.lower()
    if name == "claude":
        return ClaudeModel(model_name=model_name)
    elif name in ("openai", "gpt"):
        return OpenAIModel(model_name=model_name)
    elif name == "mock":
        return MockModel()
    else:
        raise ValueError(
            f"Unknown model backend {name!r}. Choose from: claude, openai, mock"
        )
