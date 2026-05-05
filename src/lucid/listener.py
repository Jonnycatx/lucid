"""Lucid Listener — Layer 1 of the fluency pipeline.

The Listener turns a raw user request into a structured spec the Translator
can consume. It does this by:

  1. Looking at the matched vertical's question schema.
  2. For each question, attempting to extract the answer from the user's
     intent text (using Claude Haiku for structured extraction).
  3. Merging any answers the caller already supplied (these always win over
     extracted answers).
  4. Applying defaults for optional questions left unanswered.
  5. Reporting any *required* questions still unanswered as
     `missing_required` — the caller (typically an MCP client) is expected
     to surface these to the user and call back with answers.

Design choices:
  - LLM client is injected, not constructed internally. This keeps the module
    testable without API access and lets callers control model selection,
    timeouts, and retries.
  - The structured-extraction call uses Anthropic tool-use to force a
    well-shaped response. Loose JSON parsing has been a source of bugs in
    other prompt-engineering systems we want to avoid.
  - The Listener never invents answers. If the model is uncertain, the
    answer is omitted, which surfaces it as a clarification request to the
    user. This is the "interactive" listener mode chosen in Phase 0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, TYPE_CHECKING

from lucid.verticals._schema import Question, Vertical

if TYPE_CHECKING:
    from anthropic import Anthropic


# Default model for intent extraction. Cheap and fast — extraction is
# structured classification, not generation.
LISTENER_MODEL = "claude-haiku-4-5-20251001"

# Cap how long Haiku is allowed to think. Extraction should be quick.
LISTENER_MAX_TOKENS = 512


@dataclass
class ListenerResult:
    """Outcome of running the Listener for one user request."""

    answers: dict[str, Any] = field(default_factory=dict)
    """Question id → extracted or provided answer."""

    missing_required: list[str] = field(default_factory=list)
    """Ids of *required* questions still unanswered after extraction + defaults."""

    extracted_from_intent: list[str] = field(default_factory=list)
    """Ids whose answer came from LLM extraction (not pre-provided, not default)."""

    error: Optional[str] = None
    """If the extraction API call failed, the error message. The Listener
    degrades gracefully on extraction errors: extracted answers are empty,
    so any unprovided required answers surface as missing_required. The
    server may choose to fail the request or proceed depending on whether
    required answers are still recoverable from caller-provided answers."""

    @property
    def needs_clarification(self) -> bool:
        return bool(self.missing_required)


def run_listener(
    intent: str,
    vertical: Vertical,
    answers_provided: Optional[dict[str, Any]] = None,
    *,
    client: Optional["Anthropic"] = None,
) -> ListenerResult:
    """Run the Listener over an intent and a vertical.

    Args:
      intent: The user's raw request.
      vertical: The matched vertical (from triage).
      answers_provided: Answers the caller already collected from the user
        (e.g. a prior turn surfaced clarifying questions; this turn passes
        the answers back). These always override anything the LLM extracts.
      client: An Anthropic client. If None, no LLM call is made; the Listener
        relies entirely on `answers_provided` plus defaults. This is the
        mode used in unit tests.

    Returns:
      A ListenerResult. If `needs_clarification` is True, the caller should
      surface `missing_required` to the user and call back with the answers.
    """
    answers_provided = dict(answers_provided or {})

    # Step 1: Try to extract answers we don't already have.
    extracted: dict[str, Any] = {}
    extraction_error: Optional[str] = None
    if client is not None:
        unresolved = [q for q in vertical.questions if q.id not in answers_provided]
        if unresolved:
            try:
                extracted = _extract_via_llm(intent, vertical, unresolved, client)
            except Exception as exc:  # noqa: BLE001 — Anthropic raises several classes
                # Don't crash the pipeline on extraction failure. Treat it as
                # "no answers extracted": required answers will surface as
                # clarification requests, which is the safe degradation.
                extracted = {}
                extraction_error = f"{type(exc).__name__}: {exc}"

    # Step 2: Merge — caller-provided wins over LLM-extracted.
    answers: dict[str, Any] = {**extracted, **answers_provided}

    # Step 3: Apply defaults for optional questions still unanswered.
    for q in vertical.questions:
        if q.id in answers:
            continue
        if not q.required and q.default is not None:
            answers[q.id] = q.default

    # Step 4: Find required questions still missing.
    missing_required = [q.id for q in vertical.questions if q.required and q.id not in answers]

    return ListenerResult(
        answers=answers,
        missing_required=missing_required,
        extracted_from_intent=[k for k in extracted if k not in answers_provided],
        error=extraction_error,
    )


# ----- Internals ----------------------------------------------------------


def _extract_via_llm(
    intent: str,
    vertical: Vertical,
    questions: list[Question],
    client: "Anthropic",
) -> dict[str, Any]:
    """Call Haiku with structured tool-use to extract any answers present in
    the intent. Returns only answers the model is confident about; omitted
    answers will surface as clarification requests."""

    properties: dict[str, dict[str, Any]] = {}
    for q in questions:
        prop: dict[str, Any] = {
            "type": _json_schema_type_for(q),
            "description": f"{q.prompt} (why it matters: {q.why_it_matters})",
        }
        if q.options:
            prop["enum"] = list(q.options)
        properties[q.id] = prop

    # The tool definition is identical across all Listener calls for the same
    # vertical, so we mark it cacheable. The cache hit lands when the same
    # vertical is invoked twice within the 5-minute TTL window — common in
    # multi-turn clarification flows and during eval runs.
    extract_tool = {
        "name": "record_answers",
        "description": (
            "Record only the answers that are clearly stated or strongly implied "
            "by the user's request. Omit any field you would be guessing at — "
            "leaving it out is the correct behavior when the user did not say."
        ),
        "input_schema": {
            "type": "object",
            "properties": properties,
            # Nothing is required: the Listener prefers a missing answer
            # (which surfaces as a clarification request) over a guessed one.
            "required": [],
        },
        "cache_control": {"type": "ephemeral"},
    }

    questions_text = "\n".join(
        f"- {q.id}: {q.prompt}"
        + (f" (one of: {', '.join(q.options)})" if q.options else "")
        for q in questions
    )

    user_message = (
        "Extract answers to the following questions from the user's request. "
        "Only include answers that are clearly stated or strongly implied. "
        "Omit anything you would be guessing at — leave the field out instead.\n\n"
        f"User request:\n{intent}\n\n"
        f"Questions:\n{questions_text}"
    )

    response = client.messages.create(
        model=LISTENER_MODEL,
        max_tokens=LISTENER_MAX_TOKENS,
        tools=[extract_tool],
        tool_choice={"type": "tool", "name": "record_answers"},
        messages=[{"role": "user", "content": user_message}],
    )

    for block in response.content:
        # Anthropic SDK returns content blocks; the tool_use block carries .input.
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "record_answers":
            raw = getattr(block, "input", {}) or {}
            # Filter out empty / None values — those are "the model declined to fill it".
            return {k: v for k, v in raw.items() if v not in (None, "", [])}

    # Defensive fallback: model didn't use the tool. Treat as nothing extracted.
    return {}


def _json_schema_type_for(q: Question) -> str:
    """Map a vertical Question type to a JSON Schema type."""
    from lucid.verticals._schema import QuestionType

    return {
        QuestionType.TEXT: "string",
        QuestionType.CHOICE: "string",
        QuestionType.MULTI: "array",
        QuestionType.NUMBER: "number",
        QuestionType.BOOLEAN: "boolean",
    }[q.type]
