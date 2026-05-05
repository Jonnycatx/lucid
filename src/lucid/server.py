"""Lucid MCP server.

Exposes Lucid's fluency layer as a Model Context Protocol server. Any
MCP-compatible client (Claude, Cursor, Zed, others) can use it.

v0.2 surface:
  - lucid_run(intent, vertical_hint=None, answers=None)
    Runs the pipeline: triage → Listener → (clarify or Translator) → result.

    If the Listener needs more info, returns status='needs_clarification'
    with the missing questions. The client surfaces those to the user, gets
    answers, and calls back with the answers parameter populated.

    If the Listener completes (all required answers known, defaults applied
    for optional ones), the Translator runs the configured execution model
    and returns status='complete' with the output.

Run as a stdio MCP server:
    lucid                       # via the console script defined in pyproject.toml
    python -m lucid.server      # equivalent direct invocation

Set ANTHROPIC_API_KEY in the environment for the pipeline to call models.
Without the key, the Translator returns the rendered prompt as a stub so
you can still see what would be sent.
"""

from __future__ import annotations

import os
from typing import Any, Optional, TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

from lucid.listener import run_listener
from lucid.translator import run_translator
from lucid.verticals._loader import load_registry, triage
from lucid.verticals._schema import Vertical

if TYPE_CHECKING:
    from anthropic import Anthropic


mcp = FastMCP("lucid")


# ----- Internal helpers ---------------------------------------------------


def _vertical_summary(v: Vertical) -> dict[str, Any]:
    return {
        "id": v.id,
        "name": v.name,
        "version": v.version,
        "output_format": v.output_format.value,
    }


def _question_lookup(v: Vertical, qid: str) -> dict[str, Any]:
    q = next(q for q in v.questions if q.id == qid)
    return {
        "id": q.id,
        "prompt": q.prompt,
        "type": q.type.value,
        "required": q.required,
        "options": list(q.options),
        "why_it_matters": q.why_it_matters,
    }


def _make_default_client() -> Optional["Anthropic"]:
    """Construct an Anthropic client from ANTHROPIC_API_KEY, or return None
    if the env var is unset. Returning None puts the pipeline in stub mode."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    from anthropic import Anthropic

    return Anthropic()


# ----- Pipeline (testable Python entry) -----------------------------------


def run_lucid(
    intent: str,
    vertical_hint: Optional[str] = None,
    answers: Optional[dict[str, Any]] = None,
    *,
    client: Optional["Anthropic"] = None,
) -> dict[str, Any]:
    """Run the full Lucid pipeline.

    The MCP-decorated `lucid_run` tool delegates to this function, supplying
    a default client built from ANTHROPIC_API_KEY. Tests bypass the env var
    by passing client= directly.
    """
    registry = load_registry()

    # Vertical resolution: explicit hint wins over triage.
    if vertical_hint:
        vertical = registry.get(vertical_hint)
        if vertical is None:
            return {
                "status": "unknown_hint",
                "message": (
                    f"vertical_hint '{vertical_hint}' is not in the registry. "
                    f"Available: {sorted(registry.keys())}"
                ),
                "intent": intent,
                "available_verticals": sorted(registry.keys()),
            }
    else:
        vertical = triage(intent, registry)

    if vertical is None:
        return {
            "status": "no_match",
            "message": (
                "No vertical matched the request. Later phases will fall through "
                "to a generic baseline pipeline."
            ),
            "intent": intent,
            "available_verticals": sorted(registry.keys()),
        }

    # Listener
    listener = run_listener(
        intent=intent,
        vertical=vertical,
        answers_provided=answers,
        client=client,
    )

    # An extraction error is non-fatal *if* clarification can still recover
    # the missing answers — the user supplies them in the next turn. If both
    # an error happened AND no required answers remain missing (caller already
    # provided them), we proceed silently. If both an error happened AND we'd
    # need clarification anyway, surface the clarification path normally.
    # The only case we surface as 'error' is a Translator API failure, where
    # there is no fallback path.

    if listener.needs_clarification:
        return {
            "status": "needs_clarification",
            "message": (
                "Lucid needs more information before producing the output. "
                "Surface the questions below to the user and call lucid_run "
                "again with their answers in the `answers` parameter."
            ),
            "intent": intent,
            "vertical": _vertical_summary(vertical),
            "answers_so_far": listener.answers,
            "questions_to_ask": [
                _question_lookup(vertical, qid) for qid in listener.missing_required
            ],
            "listener_error": listener.error,
        }

    # Translator
    translator = run_translator(
        intent=intent,
        vertical=vertical,
        answers=listener.answers,
        client=client,
    )

    if translator.error is not None:
        return {
            "status": "error",
            "message": (
                "The execution model call failed. The original intent and "
                "rendered prompt are included so the client can retry, "
                "diagnose, or surface a useful message to the user."
            ),
            "intent": intent,
            "vertical": _vertical_summary(vertical),
            "answers_used": listener.answers,
            "rendered_prompt": translator.rendered_prompt,
            "error": translator.error,
            "listener_error": listener.error,
        }

    return {
        "status": "complete",
        "intent": intent,
        "vertical": _vertical_summary(vertical),
        "answers_used": listener.answers,
        "extracted_from_intent": listener.extracted_from_intent,
        "result": translator.output,
        "model_used": translator.model_used,
        "rendered_prompt": translator.rendered_prompt,
        "listener_error": listener.error,
    }


# ----- MCP-exposed tool ---------------------------------------------------


@mcp.tool()
def lucid_run(
    intent: str,
    vertical_hint: Optional[str] = None,
    answers: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    """Run the Lucid fluency layer on a user request.

    Args:
      intent: The user's raw request.
      vertical_hint: Optional vertical id to use directly, bypassing triage.
      answers: Optional pre-filled answers (used after a prior call returned
        status='needs_clarification' and the user supplied the missing info).

    Returns:
      A structured dict with one of these statuses:
        - 'complete': pipeline ran end-to-end; .result holds the output
        - 'needs_clarification': Listener needs more info; .questions_to_ask
          holds what to ask the user
        - 'no_match': triage found no fitting vertical
        - 'unknown_hint': vertical_hint did not match a known vertical
    """
    return run_lucid(
        intent=intent,
        vertical_hint=vertical_hint,
        answers=answers,
        client=_make_default_client(),
    )


# ----- Entry point --------------------------------------------------------


def main() -> None:
    """Console-script entry. Runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
