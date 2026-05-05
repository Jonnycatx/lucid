"""Tests for the Validator (Phase 4)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lucid.validator import (
    VALIDATOR_MODEL,
    CriterionScore,
    ValidatorResult,
    run_validator,
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


# ----- Stub mode (no client) ----------------------------------------------


def test_validator_stub_returns_perfect_scores_with_passed_none(document_vertical):
    """Without a client, the Validator returns all-1.0 scores and passed=None
    so callers can tell the verdict was synthesized, not measured."""
    result = run_validator(
        intent="x",
        vertical=document_vertical,
        rendered_prompt="rp",
        output="out",
        client=None,
    )
    assert isinstance(result, ValidatorResult)
    assert result.model_used == "(stub)"
    # passed=None signals "stub, not real."
    assert result.passed is None
    assert result.weighted_score == pytest.approx(1.0)
    assert len(result.scores) == len(document_vertical.rubric)
    for s in result.scores:
        assert s.score == 1.0
        assert s.reasoning == "(stub)"


def test_validator_skips_when_no_rubric():
    """A vertical with no rubric returns a skipped verdict, not a 0-score fail."""
    from lucid.verticals._schema import Vertical

    no_rubric = Vertical(
        id="x.no_rubric",
        name="x",
        description="x",
        questions=[
            {"id": "q", "prompt": "p", "type": "text", "why_it_matters": "w"}
        ],
        prompt_template="{q}",
        rubric=[],
    )
    result = run_validator(
        intent="x",
        vertical=no_rubric,
        rendered_prompt="rp",
        output="out",
        client=None,
    )
    assert result.passed is None
    assert result.model_used == "(skipped)"
    assert "no rubric" in (result.error or "").lower()


# ----- Mocked LLM grading ------------------------------------------------


def _make_grader_client(per_criterion: dict[str, dict]):
    """Build a mock client that returns a tool_use block with the given
    per-criterion grades. Keys must match the rubric ids."""
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.name = "grade_output"
    tool_use_block.input = per_criterion

    response = MagicMock()
    response.content = [tool_use_block]

    client = MagicMock()
    client.messages.create.return_value = response
    return client


def test_validator_aggregates_weighted_scores(document_vertical):
    """The weighted average = sum(score*weight)/sum(weight) and decides pass/fail."""
    # document.one_pager rubric weights: structure 1.0, length 0.5, tone_match 1.0,
    # action_clarity 1.0, evidence_quality 1.0 → sum 4.5
    grades = {
        "structure":         {"score": 1.0, "reasoning": "perfect"},
        "length":            {"score": 0.0, "reasoning": "too long"},
        "tone_match":        {"score": 1.0, "reasoning": "exec tone"},
        "action_clarity":    {"score": 1.0, "reasoning": "clear"},
        "evidence_quality":  {"score": 1.0, "reasoning": "specific"},
    }
    # weighted = (1*1 + 0*0.5 + 1*1 + 1*1 + 1*1) / 4.5 = 4 / 4.5 = 0.888...
    client = _make_grader_client(grades)
    result = run_validator(
        intent="x",
        vertical=document_vertical,
        rendered_prompt="rp",
        output="out",
        client=client,
    )
    assert result.error is None
    assert result.weighted_score == pytest.approx(4.0 / 4.5, rel=1e-3)
    assert result.passed is True  # 0.888 > 0.7 threshold
    assert result.model_used == VALIDATOR_MODEL
    # All criteria graded.
    by_id = {s.id: s for s in result.scores}
    assert by_id["length"].score == 0.0
    assert by_id["length"].reasoning == "too long"


def test_validator_fails_when_below_threshold(document_vertical):
    """When the weighted score is below pass_threshold, passed=False."""
    grades = {c.id: {"score": 0.3, "reasoning": "weak"} for c in document_vertical.rubric}
    client = _make_grader_client(grades)
    result = run_validator(
        intent="x",
        vertical=document_vertical,
        rendered_prompt="rp",
        output="out",
        client=client,
    )
    assert result.weighted_score == pytest.approx(0.3, rel=1e-3)
    assert result.passed is False


def test_validator_clamps_out_of_range_scores(document_vertical):
    """Scores outside [0,1] from the grader are clamped (defensive)."""
    grades = {
        "structure":         {"score": 1.7, "reasoning": "model overshot"},
        "length":            {"score": -0.2, "reasoning": "model undershot"},
        "tone_match":        {"score": 0.5, "reasoning": "ok"},
        "action_clarity":    {"score": 0.5, "reasoning": "ok"},
        "evidence_quality":  {"score": 0.5, "reasoning": "ok"},
    }
    client = _make_grader_client(grades)
    result = run_validator(
        intent="x",
        vertical=document_vertical,
        rendered_prompt="rp",
        output="out",
        client=client,
    )
    by_id = {s.id: s for s in result.scores}
    assert by_id["structure"].score == 1.0
    assert by_id["length"].score == 0.0


def test_validator_handles_grading_api_error(document_vertical):
    """A grading API exception surfaces via .error without crashing."""
    client = MagicMock()
    client.messages.create.side_effect = RuntimeError("rate limited")
    result = run_validator(
        intent="x",
        vertical=document_vertical,
        rendered_prompt="rp",
        output="out",
        client=client,
    )
    assert result.error is not None
    assert "rate limited" in result.error
    assert result.passed is None
    assert result.scores == []


def test_validator_marks_tool_definition_cacheable(document_vertical):
    """The grading tool definition is sent with cache_control."""
    grades = {c.id: {"score": 1.0, "reasoning": "ok"} for c in document_vertical.rubric}
    client = _make_grader_client(grades)
    run_validator(
        intent="x",
        vertical=document_vertical,
        rendered_prompt="rp",
        output="out",
        client=client,
    )
    tools = client.messages.create.call_args.kwargs["tools"]
    assert tools[0]["cache_control"] == {"type": "ephemeral"}
