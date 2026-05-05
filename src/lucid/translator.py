"""Lucid Translator — Layer 2 of the fluency pipeline.

The Translator turns a Listener-produced spec (intent + filled answers) into
the actual model output. It does this by:

  1. Rendering the vertical's prompt_template with the answers, with the
     user's verbatim request available as {original_intent}.
  2. Sending the rendered prompt + the vertical's system_prompt to the
     execution model (default: Sonnet 4.6).
  3. Returning the output along with debug context (rendered prompt, model
     used) so callers can inspect, log, or grade.

If no Anthropic client is provided, the Translator returns the rendered
prompt as a stub instead of calling the API. Useful for tests and for
running Lucid without an API key (you can see exactly what *would* be sent).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

from lucid.verticals._schema import Question, Vertical

if TYPE_CHECKING:
    from anthropic import Anthropic


# Default execution model. Strong on writing, fast enough for the 5-15s
# pipeline budget, sensible cost. Configurable per call.
TRANSLATOR_MODEL = "claude-sonnet-4-6"

TRANSLATOR_MAX_TOKENS = 4096

STUB_OUTPUT_PREFIX = "[stub: no Anthropic client provided. Rendered prompt below:]\n\n"


@dataclass
class TranslatorResult:
    """Outcome of running the Translator for one spec."""

    output: str
    """The model's output (or the stub when no client was provided)."""

    rendered_prompt: str
    """The fully-filled prompt sent to the model, useful for debugging and evals."""

    rendered_system: Optional[str]
    """The system prompt sent to the model (or None if the vertical has none)."""

    model_used: str
    """The model id used. '(stub)' if no client was provided."""

    error: Optional[str] = None
    """If the API call failed, the error message. Output will be empty in this case."""


def run_translator(
    intent: str,
    vertical: Vertical,
    answers: dict[str, Any],
    *,
    client: Optional["Anthropic"] = None,
    model: str = TRANSLATOR_MODEL,
    max_tokens: int = TRANSLATOR_MAX_TOKENS,
) -> TranslatorResult:
    """Run the Translator over a Listener-filled spec.

    Args:
      intent: The user's verbatim request (becomes {original_intent}).
      vertical: The matched vertical.
      answers: Question id → answer, as produced by the Listener.
      client: An Anthropic client. If None, the Translator returns the
        rendered prompt as a stub without calling the API.
      model: The model id to use for execution. Defaults to Sonnet 4.6.
      max_tokens: Cap on the model's response length.
    """

    rendered_prompt = _render_prompt(
        template=vertical.prompt_template,
        intent=intent,
        answers=answers,
        questions=vertical.questions,
    )
    rendered_system = vertical.system_prompt

    if client is None:
        return TranslatorResult(
            output=STUB_OUTPUT_PREFIX + rendered_prompt,
            rendered_prompt=rendered_prompt,
            rendered_system=rendered_system,
            model_used="(stub)",
        )

    request_kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": rendered_prompt}],
    }
    if rendered_system is not None:
        # Use content-block form so we can mark the system prompt cacheable.
        # The system prompt is identical across all calls for a given vertical,
        # so caching it removes 5–15% of cost on repeated calls within the
        # 5-minute TTL window.
        request_kwargs["system"] = [
            {
                "type": "text",
                "text": rendered_system,
                "cache_control": {"type": "ephemeral"},
            }
        ]

    try:
        response = client.messages.create(**request_kwargs)
    except Exception as exc:  # noqa: BLE001 — Anthropic raises several classes
        return TranslatorResult(
            output="",
            rendered_prompt=rendered_prompt,
            rendered_system=rendered_system,
            model_used=model,
            error=f"{type(exc).__name__}: {exc}",
        )

    # Concatenate text blocks (typical case is a single text block).
    text_parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_parts.append(block.text)
    output = "\n".join(text_parts).strip()

    return TranslatorResult(
        output=output,
        rendered_prompt=rendered_prompt,
        rendered_system=rendered_system,
        model_used=model,
    )


# ----- Internals ----------------------------------------------------------


def _render_prompt(
    template: str,
    intent: str,
    answers: dict[str, Any],
    questions: list[Question],
) -> str:
    """Fill the template with answers and the verbatim intent.

    Missing answers default to an empty string rather than raising, since
    the schema validator already guarantees every placeholder corresponds
    to either a question id or {original_intent}, and the Listener fills
    all required answers. Optional unanswered questions without a default
    render as empty strings.
    """
    values: dict[str, Any] = {"original_intent": intent}
    for q in questions:
        raw = answers.get(q.id, "")
        if isinstance(raw, list):
            raw = ", ".join(str(x) for x in raw)
        values[q.id] = "" if raw is None else raw
    return template.format(**values)
