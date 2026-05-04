"""Tests for the Listener.

These tests run without the Anthropic API by using `client=None`, plus
mocked-client tests to verify the LLM-extraction path's contract without
making real calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lucid.listener import ListenerResult, run_listener
from lucid.verticals._loader import load_registry, reset_registry_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_registry_cache()
    yield
    reset_registry_cache()


@pytest.fixture
def document_vertical():
    return load_registry()["document.one_pager"]


# ----- No-LLM mode: caller pre-provides answers ---------------------------


def test_listener_with_all_required_answers_provided(document_vertical):
    """When the caller hands us all required answers, no clarification needed."""
    result = run_listener(
        intent="anything",
        vertical=document_vertical,
        answers_provided={"audience": "leadership team", "purpose": "decision"},
        client=None,
    )
    assert isinstance(result, ListenerResult)
    assert not result.needs_clarification
    assert result.missing_required == []
    assert result.answers["audience"] == "leadership team"
    assert result.answers["purpose"] == "decision"


def test_listener_surfaces_missing_required(document_vertical):
    """When required answers are missing, missing_required lists them."""
    result = run_listener(
        intent="anything",
        vertical=document_vertical,
        answers_provided={"audience": "the board"},  # purpose is required, missing
        client=None,
    )
    assert result.needs_clarification
    assert "purpose" in result.missing_required
    assert "audience" not in result.missing_required


def test_listener_applies_defaults_for_optional_questions(document_vertical):
    """Optional questions with a default get the default applied."""
    result = run_listener(
        intent="anything",
        vertical=document_vertical,
        answers_provided={"audience": "execs", "purpose": "update"},
        client=None,
    )
    # `stakes` is optional with default 'medium'; `constraints` is optional
    # with default "" (empty string).
    assert result.answers["stakes"] == "medium"
    assert result.answers["constraints"] == ""


def test_listener_provided_answers_override_defaults(document_vertical):
    """Caller-provided answers override defaults for optional questions."""
    result = run_listener(
        intent="anything",
        vertical=document_vertical,
        answers_provided={
            "audience": "team",
            "purpose": "briefing",
            "stakes": "high",
        },
        client=None,
    )
    assert result.answers["stakes"] == "high"


def test_listener_with_no_client_and_no_answers_misses_everything(document_vertical):
    """Without an LLM and without provided answers, all required fields are missing."""
    result = run_listener(
        intent="write a one pager about Q3",
        vertical=document_vertical,
        client=None,
    )
    # `audience` and `purpose` are required and have no defaults
    assert result.needs_clarification
    assert set(result.missing_required) == {"audience", "purpose"}


# ----- LLM mode: client is mocked ----------------------------------------


def _make_mock_client_returning(extracted: dict):
    """Build a mock Anthropic client that returns a tool_use block with the
    given extracted answers."""
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "record_answers"
    tool_use_block.input = extracted

    response = MagicMock()
    response.content = [tool_use_block]

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_listener_uses_llm_extraction_when_client_provided(document_vertical):
    """LLM-extracted answers populate the result."""
    client = _make_mock_client_returning(
        {"audience": "the leadership team", "purpose": "recommendation"}
    )
    result = run_listener(
        intent="recommend killing product X to leadership",
        vertical=document_vertical,
        client=client,
    )
    assert not result.needs_clarification
    assert result.answers["audience"] == "the leadership team"
    assert result.answers["purpose"] == "recommendation"
    assert "audience" in result.extracted_from_intent
    assert "purpose" in result.extracted_from_intent


def test_listener_provided_answers_beat_llm_extraction(document_vertical):
    """If the caller provides an answer, the LLM's value is ignored."""
    client = _make_mock_client_returning(
        {"audience": "wrong answer from LLM", "purpose": "decision"}
    )
    result = run_listener(
        intent="anything",
        vertical=document_vertical,
        answers_provided={"audience": "correct answer from caller"},
        client=client,
    )
    assert result.answers["audience"] == "correct answer from caller"
    # The LLM value gets overridden, so it's not in extracted_from_intent.
    assert "audience" not in result.extracted_from_intent
    # purpose came from the LLM though
    assert result.answers["purpose"] == "decision"
    assert "purpose" in result.extracted_from_intent


def test_listener_skips_llm_call_for_already_provided_questions(document_vertical):
    """The LLM should only be asked about unresolved questions."""
    client = _make_mock_client_returning({})
    run_listener(
        intent="anything",
        vertical=document_vertical,
        answers_provided={"audience": "execs", "purpose": "update"},
        client=client,
    )
    # The mock was called once. Inspect what questions were sent.
    call_args = client.messages.create.call_args
    user_message = call_args.kwargs["messages"][0]["content"]
    # Resolved questions should not appear in the prompt; unresolved ones should.
    assert "stakes" in user_message
    assert "constraints" in user_message
    assert "audience:" not in user_message  # already provided
    assert "purpose:" not in user_message  # already provided


def test_listener_handles_empty_extraction(document_vertical):
    """If the LLM returns empty, we still surface missing required questions."""
    client = _make_mock_client_returning({})
    result = run_listener(
        intent="totally ambiguous request",
        vertical=document_vertical,
        client=client,
    )
    assert result.needs_clarification
    assert set(result.missing_required) == {"audience", "purpose"}


def test_listener_filters_empty_string_values(document_vertical):
    """Empty-string answers from the LLM are treated as 'declined to answer'."""
    client = _make_mock_client_returning(
        {"audience": "execs", "purpose": ""}  # purpose left blank
    )
    result = run_listener(
        intent="anything",
        vertical=document_vertical,
        client=client,
    )
    assert result.answers["audience"] == "execs"
    assert "purpose" in result.missing_required
