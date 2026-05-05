"""Tests for the Lucid MCP server's pipeline.

Tests run with `client=None` to skip real API calls. The Listener uses only
defaults + caller-provided answers; the Translator returns stub output. This
exercises every branch of the pipeline without needing an API key.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lucid.server import run_lucid
from lucid.translator import STUB_OUTPUT_PREFIX
from lucid.verticals._loader import reset_registry_cache


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    reset_registry_cache()
    yield
    reset_registry_cache()


# ----- needs_clarification path -------------------------------------------


def test_run_lucid_returns_clarification_when_required_answers_missing():
    """No client + no answers → Listener can't fill required questions."""
    out = run_lucid(
        "write a one-pager about our Q3 roadmap",
        client=None,
    )
    assert out["status"] == "needs_clarification"
    qids = {q["id"] for q in out["questions_to_ask"]}
    # `audience` and `purpose` are required and have no defaults
    assert qids == {"audience", "purpose"}
    # Optional questions with defaults are already filled in answers_so_far
    assert out["answers_so_far"]["stakes"] == "medium"


def test_clarification_questions_carry_why_it_matters():
    """The 'why it matters' field is surfaced so the client can ask well."""
    out = run_lucid("write a one-pager", client=None)
    for q in out["questions_to_ask"]:
        assert "why_it_matters" in q
        assert len(q["why_it_matters"]) > 0


# ----- complete path ------------------------------------------------------


def test_run_lucid_completes_when_all_required_answers_provided():
    """With required answers provided, the pipeline runs end-to-end (stub Translator)."""
    out = run_lucid(
        "should we sunset product X?",
        vertical_hint="document.one_pager",
        answers={"audience": "executive team", "purpose": "decision"},
        client=None,
    )
    assert out["status"] == "complete"
    assert out["vertical"]["id"] == "document.one_pager"
    assert out["answers_used"]["audience"] == "executive team"
    assert out["answers_used"]["purpose"] == "decision"
    # Optional question default is applied
    assert out["answers_used"]["stakes"] == "medium"
    # Translator is in stub mode (no client)
    assert out["result"].startswith(STUB_OUTPUT_PREFIX)
    assert out["model_used"] == "(stub)"


def test_complete_response_includes_rendered_prompt():
    """The rendered prompt is returned for debugging / eval purposes."""
    out = run_lucid(
        "should we sunset product X?",
        vertical_hint="document.one_pager",
        answers={"audience": "executive team", "purpose": "decision"},
        client=None,
    )
    assert "should we sunset product X?" in out["rendered_prompt"]
    assert "executive team" in out["rendered_prompt"]


def test_run_lucid_calls_real_models_when_client_provided():
    """With a mocked Anthropic client, both Listener and Translator are invoked."""
    # Listener mock — extracts both required answers from the intent.
    listener_tool_use = MagicMock(type="tool_use")
    listener_tool_use.name = "record_answers"
    listener_tool_use.input = {"audience": "the board", "purpose": "decision"}
    listener_response = MagicMock()
    listener_response.content = [listener_tool_use]

    # Translator mock — returns the document text.
    translator_text = MagicMock(type="text")
    translator_text.text = "## Recommendation\n\nProceed."
    translator_response = MagicMock()
    translator_response.content = [translator_text]

    client = MagicMock()
    # First call is Listener (uses tools=); second is Translator (no tools).
    client.messages.create.side_effect = [listener_response, translator_response]

    out = run_lucid(
        "draft a brief recommending we sunset product X for the board",
        client=client,
    )
    assert out["status"] == "complete"
    assert out["result"] == "## Recommendation\n\nProceed."
    assert out["answers_used"]["audience"] == "the board"
    assert out["answers_used"]["purpose"] == "decision"
    assert client.messages.create.call_count == 2


# ----- fallback / unknown_hint paths --------------------------------------


def test_run_lucid_unrelated_intent_falls_back_to_general_fluency():
    """When triage finds no specialized match, the universal fallback runs."""
    out = run_lucid("what time is it in Tokyo", client=None)
    assert out["status"] == "complete"
    assert out["vertical"]["id"] == "general.fluency"


def test_run_lucid_with_explicit_hint_skips_triage():
    """vertical_hint forces the vertical even when triage wouldn't match."""
    out = run_lucid(
        "this has no keywords at all",
        vertical_hint="document.one_pager",
        answers={"audience": "team", "purpose": "update"},
        client=None,
    )
    assert out["status"] == "complete"
    assert out["vertical"]["id"] == "document.one_pager"


def test_run_lucid_with_unknown_hint():
    out = run_lucid("anything", vertical_hint="not.a.real.vertical", client=None)
    assert out["status"] == "unknown_hint"
    assert "document.one_pager" in out["available_verticals"]


# ----- validator integration ---------------------------------------------


def test_run_lucid_with_validate_false_omits_validation_block():
    """validate=False (default) means no validation block in the response."""
    out = run_lucid(
        "should we sunset product X?",
        vertical_hint="document.one_pager",
        answers={"audience": "execs", "purpose": "decision"},
        client=None,
    )
    assert out["status"] == "complete"
    assert "validation" not in out
    assert "rerolled" not in out


def test_run_lucid_with_validate_true_includes_validation_block_in_stub_mode():
    """validate=True with no client returns a stub validation block (passed=None)."""
    out = run_lucid(
        "should we sunset product X?",
        vertical_hint="document.one_pager",
        answers={"audience": "execs", "purpose": "decision"},
        validate=True,
        client=None,
    )
    assert out["status"] == "complete"
    assert "validation" in out
    assert out["validation"]["passed"] is None  # stub mode
    assert out["validation"]["model_used"] == "(stub)"
    assert out["validation"]["pass_threshold"] == 0.7
    # Stub re-roll is not triggered (passed is None, not False).
    assert out["rerolled"] is False


def test_run_lucid_validator_triggers_reroll_when_first_attempt_fails():
    """When validate=True and the first output scores below threshold, the
    Translator runs again. If the re-roll scores higher, it replaces the
    original; rerolled=True is reported."""
    # Mock client where:
    #   - Translator calls return text outputs in sequence
    #   - Validator calls return: first score 0.3 (below 0.7), then 0.9 (above)
    client = MagicMock()
    call_log: list[dict] = []

    def fake_create(**kwargs):
        call_log.append(kwargs)
        # If a tool named grade_output is requested, return a grading.
        tools = kwargs.get("tools") or []
        is_grade = any(t.get("name") == "grade_output" for t in tools)
        if is_grade:
            grade_call_index = sum(
                1 for c in call_log[:-1]
                if any((t.get("name") == "grade_output") for t in (c.get("tools") or []))
            )
            score = 0.3 if grade_call_index == 0 else 0.9
            tool_use = MagicMock()
            tool_use.type = "tool_use"
            tool_use.name = "grade_output"
            tool_use.input = {
                "structure":         {"score": score, "reasoning": "x"},
                "length":            {"score": score, "reasoning": "x"},
                "tone_match":        {"score": score, "reasoning": "x"},
                "action_clarity":    {"score": score, "reasoning": "x"},
                "evidence_quality":  {"score": score, "reasoning": "x"},
            }
            resp = MagicMock()
            resp.content = [tool_use]
            return resp
        # Otherwise it's a Translator (or Listener) call — return a text block.
        text_block = MagicMock(type="text")
        translator_call_index = sum(
            1 for c in call_log[:-1]
            if not any((t.get("name") in ("grade_output", "record_answers"))
                       for t in (c.get("tools") or []))
        )
        text_block.text = f"output v{translator_call_index + 1}"
        resp = MagicMock()
        resp.content = [text_block]
        return resp

    client.messages.create.side_effect = fake_create

    out = run_lucid(
        "should we sunset product X?",
        vertical_hint="document.one_pager",
        answers={"audience": "execs", "purpose": "decision"},
        validate=True,
        client=client,
    )
    assert out["status"] == "complete"
    assert out["rerolled"] is True
    assert out["result"] == "output v2"
    assert out["validation"]["passed"] is True
    assert out["validation"]["weighted_score"] == pytest.approx(0.9)


# ----- error path (Translator API failure) --------------------------------


def test_run_lucid_returns_error_when_translator_api_fails():
    """A Translator API exception surfaces as status='error' with the message
    and the rendered prompt (so a client can retry or display it)."""
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("upstream timeout")
    out = run_lucid(
        "should we sunset product X?",
        vertical_hint="document.one_pager",
        answers={"audience": "execs", "purpose": "decision"},
        client=client,
    )
    assert out["status"] == "error"
    assert "upstream timeout" in out["error"]
    assert out["rendered_prompt"]
    assert out["vertical"]["id"] == "document.one_pager"


# ----- multi-turn clarification loop --------------------------------------


def test_clarification_then_completion_two_turns():
    """The classic flow: first call asks for missing info; second call with
    answers completes the pipeline."""
    intent = "draft a memo for the board"
    # Turn 1: ambiguous request, no answers.
    turn1 = run_lucid(intent, client=None)
    assert turn1["status"] == "needs_clarification"

    missing = {q["id"] for q in turn1["questions_to_ask"]}
    # User provides what was missing
    user_answers = {qid: "team" if qid == "audience" else "decision" for qid in missing}

    # Turn 2: same intent, answers supplied.
    turn2 = run_lucid(intent, answers=user_answers, client=None)
    assert turn2["status"] == "complete"


# ----- serialization & decorator pass-through ------------------------------


def test_response_is_json_serializable_for_complete():
    import json

    out = run_lucid(
        "draft a one-pager",
        answers={"audience": "team", "purpose": "update"},
        client=None,
    )
    json.dumps(out)


def test_response_is_json_serializable_for_clarification():
    import json

    out = run_lucid("write a one-pager", client=None)
    json.dumps(out)


def test_lucid_run_mcp_tool_is_directly_callable():
    """The @mcp.tool-decorated function still works as a regular Python function."""
    from lucid.server import lucid_run

    out = lucid_run(
        "draft a one-pager about sunsetting product X",
        answers={"audience": "execs", "purpose": "decision"},
    )
    # Without ANTHROPIC_API_KEY in env, the default client is None, so this
    # falls through to the stub translator and returns 'complete' with stub output.
    assert out["status"] == "complete"
