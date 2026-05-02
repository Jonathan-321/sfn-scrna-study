"""
Pydantic models for task YAML validation.
Each task file must conform to the TaskSpec schema.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Sub-types for the `correct` field
# ---------------------------------------------------------------------------

class NumericCorrect(BaseModel):
    value: float
    tol: float


# `correct` can be:
#   - str            (multiple_choice letter or short_answer string)
#   - NumericCorrect  (numeric with tolerance)
#   - List[str]      (set match)
CorrectType = Union[str, NumericCorrect, List[str]]


# ---------------------------------------------------------------------------
# Choice entry for multiple-choice tasks
# ---------------------------------------------------------------------------

class Choice(BaseModel):
    """A single multiple-choice option, e.g. {'A': 'some text'}"""
    # We store choices as arbitrary dicts since keys are A/B/C/D
    model_config = {"extra": "allow"}

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> "Choice":
        return cls(**d)


# ---------------------------------------------------------------------------
# Main task schema
# ---------------------------------------------------------------------------

VALID_CATEGORIES = {
    "protocol_critique",
    "method_selection",
    "biology",
    "metrics",
    "failure_mode",
}

VALID_ANSWER_FORMATS = {
    "multiple_choice",
    "short_answer",
    "numeric",
    "set",
}

VALID_GRADERS = {
    "exact_match",
    "numeric_tolerance",
    "set_match",
    "mc_match",
}

VALID_DIFFICULTIES = {"easy", "medium", "hard"}


class TaskSpec(BaseModel):
    id: str
    title: str
    category: str
    context: str
    question: str
    answer_format: str
    choices: Optional[List[Dict[str, str]]] = None
    correct: CorrectType
    grader: str
    rationale: str
    sources: List[str]
    difficulty: str
    expected_failure: bool

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        if v not in VALID_CATEGORIES:
            raise ValueError(f"category must be one of {VALID_CATEGORIES}, got {v!r}")
        return v

    @field_validator("answer_format")
    @classmethod
    def validate_answer_format(cls, v: str) -> str:
        if v not in VALID_ANSWER_FORMATS:
            raise ValueError(
                f"answer_format must be one of {VALID_ANSWER_FORMATS}, got {v!r}"
            )
        return v

    @field_validator("grader")
    @classmethod
    def validate_grader(cls, v: str) -> str:
        if v not in VALID_GRADERS:
            raise ValueError(f"grader must be one of {VALID_GRADERS}, got {v!r}")
        return v

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        if v not in VALID_DIFFICULTIES:
            raise ValueError(
                f"difficulty must be one of {VALID_DIFFICULTIES}, got {v!r}"
            )
        return v

    @model_validator(mode="after")
    def check_choices_for_mc(self) -> "TaskSpec":
        if self.answer_format == "multiple_choice" and not self.choices:
            raise ValueError("multiple_choice tasks must have a 'choices' list")
        if self.answer_format == "numeric":
            if not isinstance(self.correct, dict) and not isinstance(
                self.correct, NumericCorrect
            ):
                raise ValueError(
                    "numeric tasks must have correct as {value: ..., tol: ...}"
                )
        if self.answer_format == "set":
            if not isinstance(self.correct, list):
                raise ValueError("set tasks must have correct as a list of strings")
        return self

    @classmethod
    def from_dict(cls, data: dict) -> "TaskSpec":
        """Parse from raw YAML-loaded dict, handling NumericCorrect sub-type."""
        correct = data.get("correct")
        if isinstance(correct, dict) and "value" in correct and "tol" in correct:
            data = {**data, "correct": NumericCorrect(**correct)}
        return cls(**data)
