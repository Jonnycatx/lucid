"""Tests for the Translator."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lucid.translator import (
    STUB_OUTPUT_PREFIX,
    TRANSLATOR_MODEL,
    TranslatorResult,
    run_translator,
)
from lucid.verticals._loader import load_registry, reset_registry_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_registry_cache()
    yield
    reset_registry_cache()


@pytest.fixture
def document_vertical():
    return load_registry()["document.one_pager"]


@pytest.fixture
def filled_answers():
    return {
        "audience": "the executive team",
        "purpose": "decision",
        "stakes": "high",
        "constraints": "must include Q3 revenue numbers",
    }


# ----- No-client mode (stub) ----------------------------------------------


def test_translator_returns_stub_without_client(document_vertical, filled_answers):
    """Without a client, the Translator returns the rendered prompt as a stub."""
    result = run_translator(
        intent="should we sunset product X?",
        vertical=document_vertical,
        answers=filled_answers,
        client=None,
    )
    assert isinstance(result, TranslatorResult)
    assert result.output.startswith(STUB_OUTPUT_PREFIX)
    assert result.model_used == "(stub)"


def test_translator_renders_all_placeholders(document_vertical, filled_answers):
    """Every placeholder in the template gets substituted; no leftover {braces}."""
    intent = "should we sunset product X?"
    result = run_translator(
        intent=intent,
        vertical=document_vertical,
        answers=filled_answers,
        client=None,
    )
    rp = result.rendered_prompt
    assert "the executive team" in rp
    assert "decision" in rp
    assert "high" in rp
    assert "must include Q3 revenue numbers" in rp
    assert intent in rp
    # No unsubstituted placeholders left.
    import re

    assert not re.search(r"\{[a-zA-Z_]+\}", rp), f"Unsubstituted placeholders in: {rp}"


def test_translator_carries_system_prompt(document_vertical, filled_answers):
    """The vertical's system_prompt is preserved on the result."""
    result = run_translator(
        intent="anything",
        vertical=document_vertical,
        answers=filled_answers,
        client=None,
    )
    assert result.rendered_system is not None
    assert "strategic communicator" in result.rendered_system


def test_translator_handles_missing_optional_answer(document_vertical):
    """An optional answer not in the dict renders as empty string, not KeyError."""
    answers = {"audience": "team", "purpose": "update"}  # stakes / constraints absent
    result = run_translator(
        intent="anything",
        vertical=document_vertical,
        answers=answers,
        client=None,
    )
    # No exception — missing optionals just render blank.
    assert result.output is not None


# ----- Client mode (mocked) -----------------------------------------------


def _make_mock_client(text: str):
    """Anthropic client that returns a single text block."""
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    response = MagicMock()
    response.content = [text_block]

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_translator_calls_client_and_returns_text(document_vertical, filled_answers):
    expected = "## Sunset product X\n\nRecommendation: yes. Three reasons follow."
    client = _make_mock_client(expected)
    result = run_translator(
        intent="should we sunset product X?",
        vertical=document_vertical,
        answers=filled_answers,
        client=client,
    )
    assert result.output == expected
    assert result.model_used == TRANSLATOR_MODEL


def test_translator_passes_system_prompt_to_client(document_vertical, filled_answers):
    client = _make_mock_client("output")
    run_translator(
        intent="anything",
        vertical=document_vertical,
        answers=filled_answers,
        client=client,
    )
    kwargs = client.messages.create.call_args.kwargs
    # system is sent as a list of content blocks so prompt caching can be applied
    assert "system" in kwargs
    assert isinstance(kwargs["system"], list)
    system_text = kwargs["system"][0]["text"]
    assert "strategic communicator" in system_text
    assert kwargs["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert kwargs["model"] == TRANSLATOR_MODEL


def test_translator_returns_error_on_api_failure(document_vertical, filled_answers):
    """Translator catches API exceptions and surfaces them via .error."""
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("rate limited")
    result = run_translator(
        intent="anything",
        vertical=document_vertical,
        answers=filled_answers,
        client=client,
    )
    assert result.error is not None
    assert "rate limited" in result.error
    assert result.output == ""
    # Rendered prompt is still populated for debugging.
    assert result.rendered_prompt


def test_translator_passes_rendered_prompt_to_client(document_vertical, filled_answers):
    client = _make_mock_client("output")
    intent = "should we sunset product X?"
    run_translator(
        intent=intent,
        vertical=document_vertical,
        answers=filled_answers,
        client=client,
    )
    kwargs = client.messages.create.call_args.kwargs
    user_message = kwargs["messages"][0]["content"]
    assert intent in user_message
    assert "the executive team" in user_message
    assert "decision" in user_message


def test_translator_concatenates_multiple_text_blocks(document_vertical, filled_answers):
    block_a = MagicMock(type="text")
    block_a.text = "Part one."
    block_b = MagicMock(type="text")
    block_b.text = "Part two."
    response = MagicMock()
    response.content = [block_a, block_b]
    client = MagicMock()
    client.messages.create.return_value = response

    result = run_translator(
        intent="x",
        vertical=document_vertical,
        answers=filled_answers,
        client=client,
    )
    assert "Part one." in result.output
    assert "Part two." in result.output


def test_translator_respects_custom_model(document_vertical, filled_answers):
    client = _make_mock_client("output")
    run_translator(
        intent="x",
        vertical=document_vertical,
        answers=filled_answers,
        client=client,
        model="claude-opus-4-6",
    )
    assert client.messages.create.call_args.kwargs["model"] == "claude-opus-4-6"
