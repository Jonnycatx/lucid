"""Data structures for a Lucid vertical.

A vertical defines a domain Lucid is fluent in. It declares:
  - Listener: the questions whose answers determine output success.
  - Translator: the prompt template that turns answers into the optimal model input.
  - Validator: the rubric that grades output against intent.
  - Triage: the keywords, examples, and priority used to detect this vertical
            from a raw user request.

Verticals live as YAML files under `src/lucid/verticals/<vertical_id>/config.yaml`.
This module defines the schema those YAML files must satisfy.

Notes on design choices:
  - Memory integration is deferred to Phase 5 by plan. No memory fields in v0.1.
  - Rubric weights are *relative*. They are NOT auto-normalized at load time.
    The Validator computes the weighted average and divides by sum(weights).
    This keeps the YAML readable as written.
  - The `original_intent` placeholder is reserved and always available in
    prompt_template. It carries the user's verbatim request through the pipeline.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# Placeholders allowed in prompt_template that are not question ids.
RESERVED_PLACEHOLDERS: frozenset[str] = frozenset({"original_intent"})


class QuestionType(str, Enum):
    """How a Listener question is answered."""

    TEXT = "text"
    CHOICE = "choice"
    MULTI = "multi"
    NUMBER = "number"
    BOOLEAN = "boolean"


class OutputFormat(str, Enum):
    """The expected shape of model output for a vertical.

    Used by the Validator and downstream clients to render or parse the result.
    """

    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    CODE = "code"
    STRUCTURED = "structured"  # mixed prose + structured fields


class Question(BaseModel):
    """A single piece of information the Listener needs to extract from the user.

    Required questions must be answered (or inferred) before execution.
    Optional questions fall back to `default` if unanswered.
    """

    id: str = Field(..., description="Stable identifier; used as a {variable} in prompt_template.")
    prompt: str = Field(..., description="What the Listener asks the user, or attempts to infer.")
    type: QuestionType
    options: list[str] = Field(
        default_factory=list,
        description="Allowed values for CHOICE / MULTI types. Ignored for other types.",
    )
    required: bool = Field(default=True)
    default: Optional[str | int | float | bool] = Field(
        default=None,
        description="Fallback value when the question is optional and unanswered. "
        "Type should align with `type`: str for TEXT/CHOICE/MULTI, int|float for NUMBER, "
        "bool for BOOLEAN.",
    )
    why_it_matters: str = Field(
        ...,
        description="What changes about the output if this answer is wrong or missing. "
        "Used by the Listener to decide how aggressively to surface this question.",
    )

    @field_validator("options")
    @classmethod
    def _options_required_for_choice(cls, v, info):
        qtype = info.data.get("type")
        if qtype in (QuestionType.CHOICE, QuestionType.MULTI) and not v:
            raise ValueError(f"options must be provided when type is {qtype.value}")
        return v


class RubricCriterion(BaseModel):
    """One dimension along which the Validator grades output.

    Weights are relative within a vertical. The Validator computes the weighted
    average over criteria and divides by the sum of weights at compute time.
    """

    id: str
    name: str
    description: str = Field(
        ..., description="Plain-language statement of what this criterion measures."
    )
    weight: float = Field(default=1.0, ge=0.0)


class Vertical(BaseModel):
    """Full definition of a Lucid vertical.

    Loaded from YAML at startup and validated against this schema.
    """

    # Identity
    id: str = Field(
        ..., description="Stable, dot-namespaced identifier, e.g. 'document.one_pager'."
    )
    name: str
    description: str
    version: str = Field(default="0.1.0")

    # Listener
    questions: list[Question]

    # Translator
    prompt_template: str = Field(
        ...,
        description="Prompt template with {placeholders}. Allowed placeholders are "
        "Question.id values plus the reserved {original_intent}.",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional system prompt sent alongside prompt_template at execution.",
    )
    output_format: OutputFormat = Field(
        default=OutputFormat.MARKDOWN,
        description="Expected shape of model output. Helps the Validator and clients.",
    )

    # Validator
    rubric: list[RubricCriterion]
    pass_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weighted-average rubric score required for the output to pass.",
    )

    # Triage
    keywords: list[str] = Field(
        default_factory=list,
        description="Lowercase tokens used to detect this vertical from a raw request.",
    )
    examples: list[str] = Field(
        default_factory=list,
        description="Example user requests that fit this vertical. Used for few-shot triage.",
    )
    priority: int = Field(
        default=0,
        description="Triage tiebreaker. Higher wins when multiple verticals match. "
        "Default 0; reserve higher values for narrow, well-defined verticals.",
    )
    is_fallback: bool = Field(
        default=False,
        description="If True, this vertical is selected by triage when no other "
        "vertical's keywords match. At most one vertical may be marked fallback.",
    )

    @field_validator("questions")
    @classmethod
    def _question_ids_unique(cls, v):
        ids = [q.id for q in v]
        if len(ids) != len(set(ids)):
            raise ValueError("question ids must be unique within a vertical")
        return v

    @field_validator("rubric")
    @classmethod
    def _rubric_ids_unique(cls, v):
        ids = [c.id for c in v]
        if len(ids) != len(set(ids)):
            raise ValueError("rubric criterion ids must be unique within a vertical")
        return v

    @model_validator(mode="after")
    def _prompt_template_placeholders_valid(self) -> "Vertical":
        """Every {placeholder} in prompt_template must be a valid question id
        or a reserved placeholder. The reverse is not required: questions may
        exist that inform the Listener but do not appear in the template."""
        used = set(re.findall(r"\{(\w+)\}", self.prompt_template))
        question_ids = {q.id for q in self.questions}
        allowed = question_ids | RESERVED_PLACEHOLDERS
        unknown = used - allowed
        if unknown:
            raise ValueError(
                f"prompt_template references unknown placeholders: {sorted(unknown)}. "
                f"Allowed: question ids {sorted(question_ids)} or "
                f"reserved {sorted(RESERVED_PLACEHOLDERS)}."
            )
        return self
