"""
Deterministic graders for the IBD scRNA eval suite.

All graders accept (response: str, correct: ...) and return bool.
No LLM-as-judge anywhere.
"""

from __future__ import annotations

import re
import unicodedata
from typing import List, Union

from .schema import NumericCorrect


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip, collapse whitespace, remove punctuation."""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text


def _extract_mc_letter(response: str) -> str | None:
    """
    Extract the first A/B/C/D letter from a model response.
    Handles formats like:
      - "B"
      - "Answer: B"
      - "(B)"
      - "The answer is B."
      - "B. Some explanation"
    Returns the uppercase letter or None if not found.
    """
    # First try: look for a standalone letter at the start (after optional whitespace/punctuation)
    m = re.search(r"\b([A-Da-d])\b", response)
    if m:
        return m.group(1).upper()
    return None


# ---------------------------------------------------------------------------
# Public graders
# ---------------------------------------------------------------------------

def mc_match(response: str, correct: str) -> bool:
    """
    Multiple-choice grader.
    Extracts a single letter A/B/C/D from the response and compares to correct.
    correct should be a single uppercase letter, e.g. "B".
    """
    extracted = _extract_mc_letter(response)
    if extracted is None:
        return False
    return extracted == correct.upper().strip()


def numeric_tolerance(response: str, correct: Union[NumericCorrect, dict]) -> bool:
    """
    Numeric grader.
    Passes if |parsed_number - target.value| <= target.tol.
    Extracts the first float-like substring from the response.
    correct is a NumericCorrect or dict with keys 'value' and 'tol'.
    """
    if isinstance(correct, dict):
        target_value = float(correct["value"])
        target_tol = float(correct["tol"])
    else:
        target_value = float(correct.value)
        target_tol = float(correct.tol)

    # Find all decimal numbers in the response (handles 0.96, .96, 96%, etc.)
    numbers = re.findall(r"\d+\.?\d*", response.replace(",", "."))
    for token in numbers:
        try:
            val = float(token)
            # Accept both ratio (0.96) and percent (96.0) representations
            if abs(val - target_value) <= target_tol:
                return True
            # Try percent → ratio conversion
            if val > 1.5 and abs(val / 100.0 - target_value) <= target_tol:
                return True
        except ValueError:
            continue
    return False


def set_match(response: str, correct: List[str]) -> bool:
    """
    Set-match grader.
    Case-insensitive, order-insensitive.
    All elements in `correct` must appear in the response.
    Matches on normalized word boundaries.
    correct is a list of strings.
    """
    resp_norm = _normalize(response)
    correct_norm = {_normalize(c) for c in correct}
    found = set()
    for item in correct_norm:
        # Check if item appears as a word/phrase in the normalized response
        if item in resp_norm:
            found.add(item)
    return found == correct_norm


def exact_match(response: str, correct: str) -> bool:
    """
    Exact-match grader (lenient).
    Passes if the normalized correct string is a substring of the normalized response.
    Also passes on full normalized equality.
    correct is a string.
    """
    resp_norm = _normalize(response)
    corr_norm = _normalize(correct)
    # Direct equality
    if resp_norm == corr_norm:
        return True
    # Substring containment (lenient for short_answer where model may elaborate)
    if corr_norm in resp_norm:
        return True
    return False


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def run_grader(grader_name: str, response: str, correct) -> bool:
    """
    Dispatch to the appropriate grader by name.

    Args:
        grader_name: one of 'mc_match', 'numeric_tolerance', 'set_match', 'exact_match'
        response: raw model response string
        correct: the correct answer (type depends on grader)

    Returns:
        bool — True if the response is graded as correct
    """
    if grader_name == "mc_match":
        return mc_match(response, correct)
    elif grader_name == "numeric_tolerance":
        return numeric_tolerance(response, correct)
    elif grader_name == "set_match":
        return set_match(response, correct)
    elif grader_name == "exact_match":
        return exact_match(response, correct)
    else:
        raise ValueError(f"Unknown grader: {grader_name!r}")
