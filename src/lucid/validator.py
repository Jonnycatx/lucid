"""Lucid Validator — Layer 4 of the fluency pipeline.

The Validator grades a Translator-produced output against the matched
vertical's rubric. It does this by:

  1. Building a structured grading task from the rubric criteria.
  2. Sending the original intent, the rendered prompt, and the output to
     a grader model via Anthropic tool-use, asking for a 0.0-1.0 score
     per criterion plus a one-sentence justification.
  3. Computing the weighted average over criteria (divided by sum of
     weights) and comparing against the vertical's pass_threshold.
  4. Returning a structured verdict with per-criterion scores, the
     weighted total, and pass/fail.

Design choices:
  - Uses a different model from the Translator by default, to reduce
    self-preference bias. Default grader is Sonnet 4.6; the Translator
    also defaults to Sonnet 4.6, so callers should consider passing
    `model="claude-opus-4-6"` to validate() or running an A/B with a
    deliberately stronger judge.
  - LLM client is injected. Without a client, the Validator returns a
    stub verdict (all criteria pass with a marker score) so server
    integration tests don't need API access.
  - Errors in the grading call don't crash the pipeline. Instead, the
    Validator returns a verdict with `error` populated and `passed=None`
    so the caller can decide whether to surface the failure or treat it
    as a "skip validation" event.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from lucid.verticals._schema import Vertical

if TYPE_CHECKING:
    from anthropic import Anthropic


# Default grader model. Strong enough to evaluate craft criteria; the
# pipeline budget is 5–15s end-to-end, so we keep this on Sonnet rather
# than Opus to stay within budget. Callers wanting more rigor can pass
# model="claude-opus-4-6".
VALIDATOR_MODEL = "claude-sonnet-4-6"
VALIDATOR_MAX_TOKENS = 1024


@dataclass
class CriterionScore:
    """One graded rubric criterion."""

    id: str
    score: float          # 0.0 - 1.0
    weight: float         # carried over from the vertical for transparency
    reasoning: str        # one-sentence justification


@dataclass
class ValidatorResult:
    """Outcome of grading one output against one vertical's rubric."""

    scores: list[CriterionScore] = field(default_factory=list)
    """Per-criterion grades, in the order the rubric declares them."""

    weighted_score: float = 0.0
    """Sum(score * weight) / sum(weight). 0.0 if no scores."""

    passed: Optional[bool] = None
    """True if weighted_score >= pass_threshold. None if grading failed
    or was skipped (stub mode without a client)."""

    pass_threshold: float = 0.0
    """The threshold used, copied from the vertical for transparency."""

    model_used: str = "(stub)"
    """The grader model id, or '(stub)' when no client was provided."""

    error: Optional[str] = None
    """If the grading call failed, the error message. Other fields will
    be empty/zero in this case."""


def run_validator(
    intent: str,
    vertical: Vertical,
    rendered_prompt: str,
    output: str,
    *,
    client: Optional["Anthropic"] = None,
    model: str = VALIDATOR_MODEL,
    max_tokens: int = VALIDATOR_MAX_TOKENS,
) -> ValidatorResult:
    """Grade `output` against `vertical.rubric`.

    Args:
      intent: The user's verbatim request (provides grading context).
      vertical: The matched vertical, used for rubric and threshold.
      rendered_prompt: The full prompt the Translator sent to the model
        (so the grader can fairly evaluate against the spec).
      output: The Translator's output, the thing being graded.
      client: Anthropic client. If None, returns a neutral stub verdict
        (all criteria score 1.0, passed=None) so server integration code
        can be tested without API access.
      model: Grader model id.
      max_tokens: Cap on the grader's response length.
    """

    if not vertical.rubric:
        # Defensive: a vertical with no rubric can't be validated. Surface
        # this as a skipped verdict rather than a 0-score failure.
        return ValidatorResult(
            scores=[],
            weighted_score=0.0,
            passed=None,
            pass_threshold=vertical.pass_threshold,
            model_used="(skipped)",
            error="Vertical has no rubric; cannot validate.",
        )

    if client is None:
        # Stub: synthesize a perfect-score verdict so the pipeline can be
        # exercised end-to-end without an API key. passed=None signals
        # "not really validated."
        stub_scores = [
            CriterionScore(id=c.id, score=1.0, weight=c.weight, reasoning="(stub)")
            for c in vertical.rubric
        ]
        total_weight = sum(c.weight for c in vertical.rubric) or 1.0
        weighted = sum(s.score * s.weight for s in stub_scores) / total_weight
        return ValidatorResult(
            scores=stub_scores,
            weighted_score=weighted,
            passed=None,
            pass_threshold=vertical.pass_threshold,
            model_used="(stub)",
        )

    try:
        graded = _grade_via_llm(
            intent=intent,
            vertical=vertical,
            rendered_prompt=rendered_prompt,
            output=output,
            client=client,
            model=model,
            max_tokens=max_tokens,
        )
    except Exception as exc:  # noqa: BLE001 — Anthropic raises several classes
        return ValidatorResult(
            scores=[],
            weighted_score=0.0,
            passed=None,
            pass_threshold=vertical.pass_threshold,
            model_used=model,
            error=f"{type(exc).__name__}: {exc}",
        )

    total_weight = sum(c.weight for c in vertical.rubric) or 1.0
    weighted = sum(s.score * s.weight for s in graded) / total_weight
    return ValidatorResult(
        scores=graded,
        weighted_score=weighted,
        passed=weighted >= vertical.pass_threshold,
        pass_threshold=vertical.pass_threshold,
        model_used=model,
    )


# ----- Internals ----------------------------------------------------------


def _grade_via_llm(
    intent: str,
    vertical: Vertical,
    rendered_prompt: str,
    output: str,
    client: "Anthropic",
    model: str,
    max_tokens: int,
) -> list[CriterionScore]:
    """Call the grader model with structured tool-use and return per-criterion
    scores in the order of the vertical's rubric."""

    properties: dict[str, dict[str, Any]] = {}
    for c in vertical.rubric:
        properties[c.id] = {
            "type": "object",
            "properties": {
                "score": {
                    "type": "number",
                    "description": (
                        f"Score from 0.0 to 1.0 for the criterion: {c.name}. "
                        f"Description: {c.description}"
                    ),
                    "minimum": 0.0,
                    "maximum": 1.0,
                },
                "reasoning": {
                    "type": "string",
                    "description": "One sentence explaining the score.",
                },
            },
            "required": ["score", "reasoning"],
        }

    grade_tool = {
        "name": "grade_output",
        "description": (
            "Score the output along each rubric criterion from 0.0 to 1.0. "
            "Be honest: 1.0 means the criterion is met excellently; 0.5 "
            "means partially; 0.0 means not met. Each score requires a "
            "one-sentence reasoning."
        ),
        "input_schema": {
            "type": "object",
            "properties": properties,
            "required": [c.id for c in vertical.rubric],
        },
        "cache_control": {"type": "ephemeral"},
    }

    rubric_text = "\n".join(
        f"- {c.id} ({c.name}, weight {c.weight}): {c.description}"
        for c in vertical.rubric
    )

    user_message = (
        "Grade the output below against the rubric. Be honest and "
        "discriminating — partial credit is appropriate when a criterion "
        "is partially met. Use the original intent and the rendered prompt "
        "as context for what the user actually wanted.\n\n"
        f"Original user intent:\n{intent}\n\n"
        f"Rendered prompt sent to the model:\n{rendered_prompt}\n\n"
        f"Output produced:\n{output}\n\n"
        f"Rubric:\n{rubric_text}"
    )

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        tools=[grade_tool],
        tool_choice={"type": "tool", "name": "grade_output"},
        messages=[{"role": "user", "content": user_message}],
    )

    raw: dict[str, Any] = {}
    for block in response.content:
        if (
            getattr(block, "type", None) == "tool_use"
            and getattr(block, "name", None) == "grade_output"
        ):
            raw = getattr(block, "input", {}) or {}
            break

    out: list[CriterionScore] = []
    for c in vertical.rubric:
        entry = raw.get(c.id) or {}
        score = float(entry.get("score", 0.0))
        # Clamp to valid range — defensive.
        score = max(0.0, min(1.0, score))
        out.append(
            CriterionScore(
                id=c.id,
                score=score,
                weight=c.weight,
                reasoning=str(entry.get("reasoning", "")),
            )
        )
    return out
