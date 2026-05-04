"""Tests for the vertical schema.

Run with: pytest tests/test_schema.py
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from lucid.verticals._schema import (
    OutputFormat,
    Question,
    QuestionType,
    Vertical,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DOCUMENT_VERTICAL_YAML = REPO_ROOT / "src" / "lucid" / "verticals" / "document" / "config.yaml"


@pytest.fixture
def document_raw() -> dict:
    """Raw YAML for the document.one_pager vertical."""
    with open(DOCUMENT_VERTICAL_YAML) as f:
        return yaml.safe_load(f)


def test_document_vertical_loads(document_raw):
    """The shipped document vertical must validate against the schema."""
    v = Vertical(**document_raw)
    assert v.id == "document.one_pager"
    assert v.version == "0.1.0"
    assert v.output_format == OutputFormat.MARKDOWN
    assert {q.id for q in v.questions} == {"audience", "purpose", "stakes", "constraints"}
    assert len(v.rubric) == 5
    assert 0.0 <= v.pass_threshold <= 1.0


def test_unknown_placeholder_in_template_is_caught(document_raw):
    """prompt_template referencing an unknown placeholder must raise."""
    bad = dict(document_raw)
    bad["prompt_template"] = bad["prompt_template"] + "\n{nonexistent_field}"
    with pytest.raises(ValueError, match="unknown placeholders"):
        Vertical(**bad)


def test_question_not_in_template_is_allowed(document_raw):
    """Questions may exist that don't appear in the template; the Listener
    can still use them. The reverse direction (placeholder without question)
    is what's forbidden."""
    extra = dict(document_raw)
    extra["questions"] = list(document_raw["questions"]) + [
        {
            "id": "internal_only",
            "prompt": "Used by Listener but not surfaced in output prompt.",
            "type": "text",
            "required": False,
            "default": "",
            "why_it_matters": "Listener uses it for context only.",
        }
    ]
    v = Vertical(**extra)
    assert "internal_only" in {q.id for q in v.questions}


def test_duplicate_question_ids_rejected(document_raw):
    """Two questions with the same id must be rejected."""
    dup = dict(document_raw)
    dup["questions"] = list(document_raw["questions"]) + [dict(document_raw["questions"][0])]
    with pytest.raises(ValueError, match="unique"):
        Vertical(**dup)


def test_choice_without_options_rejected(document_raw):
    """A CHOICE question without options must be rejected."""
    no_opts = dict(document_raw)
    no_opts["questions"] = [dict(q) for q in document_raw["questions"]]
    # 'purpose' is a CHOICE question; empty its options
    purpose_idx = next(i for i, q in enumerate(no_opts["questions"]) if q["id"] == "purpose")
    no_opts["questions"][purpose_idx] = dict(no_opts["questions"][purpose_idx])
    no_opts["questions"][purpose_idx]["options"] = []
    with pytest.raises(ValueError, match="options must be provided"):
        Vertical(**no_opts)


def test_duplicate_rubric_ids_rejected(document_raw):
    """Two rubric criteria with the same id must be rejected."""
    dup = dict(document_raw)
    dup["rubric"] = list(document_raw["rubric"]) + [dict(document_raw["rubric"][0])]
    with pytest.raises(ValueError, match="unique"):
        Vertical(**dup)


def test_pass_threshold_bounds():
    """pass_threshold must be in [0.0, 1.0]."""
    base = dict(
        id="test.x",
        name="t",
        description="t",
        questions=[
            {
                "id": "q",
                "prompt": "p",
                "type": "text",
                "why_it_matters": "w",
            }
        ],
        prompt_template="{q}",
        rubric=[{"id": "r", "name": "r", "description": "r"}],
    )
    with pytest.raises(ValueError):
        Vertical(**{**base, "pass_threshold": 1.5})
    with pytest.raises(ValueError):
        Vertical(**{**base, "pass_threshold": -0.1})


def test_question_default_typing():
    """default may be str, int, float, bool, or None."""
    for default_value in ("text", 5, 3.14, True, None):
        q = Question(
            id="q",
            prompt="p",
            type=QuestionType.TEXT,
            required=False,
            default=default_value,
            why_it_matters="w",
        )
        assert q.default == default_value
