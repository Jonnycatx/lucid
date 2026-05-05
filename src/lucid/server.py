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
from lucid.validator import run_validator
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


def _validator_summary(verdict: Any) -> dict[str, Any]:
    """JSON-serializable summary of a ValidatorResult."""
    return {
        "weighted_score": round(verdict.weighted_score, 3),
        "passed": verdict.passed,
        "pass_threshold": verdict.pass_threshold,
        "model_used": verdict.model_used,
        "scores": [
            {
                "id": s.id,
                "score": round(s.score, 3),
                "weight": s.weight,
                "reasoning": s.reasoning,
            }
            for s in verdict.scores
        ],
        "error": verdict.error,
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
    validate: bool = False,
    client: Optional["Anthropic"] = None,
) -> dict[str, Any]:
    """Run the full Lucid pipeline.

    The MCP-decorated `lucid_run` tool delegates to this function, supplying
    a default client built from ANTHROPIC_API_KEY. Tests bypass the env var
    by passing client= directly.

    If `validate=True`, the Validator grades the Translator's output against
    the vertical's rubric. If the weighted score is below the vertical's
    pass_threshold, the Translator is invoked once more (a single re-roll
    budget). The final result includes the Validator verdict either way so
    callers can surface scores or diagnose grader misses.
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

    # Validator (optional): grade the output and re-run on miss.
    validator_verdict = None
    rerolled = False
    if validate:
        validator_verdict = run_validator(
            intent=intent,
            vertical=vertical,
            rendered_prompt=translator.rendered_prompt,
            output=translator.output,
            client=client,
        )
        # Only re-roll on a *real* fail (passed=False). passed=None means
        # grading was skipped or errored — re-rolling on that wouldn't be
        # justified, since we have no actual signal.
        if validator_verdict.passed is False:
            rerun = run_translator(
                intent=intent,
                vertical=vertical,
                answers=listener.answers,
                client=client,
            )
            if rerun.error is None:
                # Re-grade the re-roll. The caller sees the better-of-two.
                rerun_verdict = run_validator(
                    intent=intent,
                    vertical=vertical,
                    rendered_prompt=rerun.rendered_prompt,
                    output=rerun.output,
                    client=client,
                )
                if rerun_verdict.weighted_score >= validator_verdict.weighted_score:
                    translator = rerun
                    validator_verdict = rerun_verdict
                    rerolled = True

    response: dict[str, Any] = {
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
    if validator_verdict is not None:
        response["validation"] = _validator_summary(validator_verdict)
        response["rerolled"] = rerolled
    return response


# ----- MCP-exposed tool ---------------------------------------------------


@mcp.tool()
def lucid_run(
    intent: str,
    vertical_hint: Optional[str] = None,
    answers: Optional[dict[str, str]] = None,
    validate: bool = False,
) -> dict[str, Any]:
    """Run the Lucid fluency layer on a user request.

    Args:
      intent: The user's raw request.
      vertical_hint: Optional vertical id to use directly, bypassing triage.
      answers: Optional pre-filled answers (used after a prior call returned
        status='needs_clarification' and the user supplied the missing info).
      validate: If True, grade the output against the vertical's rubric and
        re-run the Translator once if the score falls below the threshold.
        Adds latency and one extra model call (or two if the re-roll fires).

    Returns:
      A structured dict with one of these statuses:
        - 'complete': pipeline ran end-to-end; .result holds the output.
          When validate=True, also includes .validation with per-criterion
          scores and .rerolled (bool).
        - 'needs_clarification': Listener needs more info; .questions_to_ask
          holds what to ask the user
        - 'error': the Translator API call failed; .error holds the message
        - 'unknown_hint': vertical_hint did not match a known vertical
    """
    return run_lucid(
        intent=intent,
        vertical_hint=vertical_hint,
        answers=answers,
        validate=validate,
        client=_make_default_client(),
    )


# ----- Entry point --------------------------------------------------------


def main() -> None:
    """Console-script entry. Runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
