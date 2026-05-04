"""Tests for vertical discovery, loading, and triage."""

from __future__ import annotations

import pytest

from lucid.verticals._loader import (
    VerticalLoadError,
    load_registry,
    reset_registry_cache,
    triage,
)
from lucid.verticals._schema import Vertical


@pytest.fixture(autouse=True)
def _clear_cache():
    """Each test starts with a fresh registry cache."""
    reset_registry_cache()
    yield
    reset_registry_cache()


def test_registry_loads_document_vertical():
    """The shipped registry must include the document vertical."""
    reg = load_registry()
    assert "document.one_pager" in reg
    assert isinstance(reg["document.one_pager"], Vertical)


def test_registry_is_cached():
    """Two calls return the same dict object."""
    a = load_registry()
    b = load_registry()
    assert a is b


def test_triage_matches_one_pager():
    """A clear one-pager request finds the document vertical."""
    v = triage("write a one-pager about our Q3 roadmap for the leadership team")
    assert v is not None
    assert v.id == "document.one_pager"


def test_triage_matches_executive_summary():
    """Different keyword phrasing also matches."""
    v = triage("I need an executive summary of the customer research")
    assert v is not None
    assert v.id == "document.one_pager"


def test_triage_no_match_returns_none():
    """A request with no matching keywords returns None."""
    v = triage("what time is it in Tokyo right now")
    assert v is None


def test_triage_priority_tiebreak():
    """When two verticals match equally, higher priority wins."""
    low = Vertical(
        id="x.low",
        name="low",
        description="low",
        questions=[
            {"id": "q", "prompt": "p", "type": "text", "why_it_matters": "w"}
        ],
        prompt_template="{q}",
        rubric=[{"id": "r", "name": "r", "description": "r"}],
        keywords=["foo"],
        priority=0,
    )
    high = Vertical(
        id="x.high",
        name="high",
        description="high",
        questions=[
            {"id": "q", "prompt": "p", "type": "text", "why_it_matters": "w"}
        ],
        prompt_template="{q}",
        rubric=[{"id": "r", "name": "r", "description": "r"}],
        keywords=["foo"],
        priority=10,
    )
    fake_registry = {low.id: low, high.id: high}
    v = triage("hello foo world", registry=fake_registry)
    assert v is not None
    assert v.id == "x.high"


def test_triage_score_beats_priority():
    """More keyword matches beats higher priority."""
    one_kw = Vertical(
        id="x.one",
        name="one",
        description="one",
        questions=[
            {"id": "q", "prompt": "p", "type": "text", "why_it_matters": "w"}
        ],
        prompt_template="{q}",
        rubric=[{"id": "r", "name": "r", "description": "r"}],
        keywords=["foo"],
        priority=100,
    )
    two_kw = Vertical(
        id="x.two",
        name="two",
        description="two",
        questions=[
            {"id": "q", "prompt": "p", "type": "text", "why_it_matters": "w"}
        ],
        prompt_template="{q}",
        rubric=[{"id": "r", "name": "r", "description": "r"}],
        keywords=["foo", "bar"],
        priority=0,
    )
    fake_registry = {one_kw.id: one_kw, two_kw.id: two_kw}
    v = triage("foo bar baz", registry=fake_registry)
    assert v is not None
    assert v.id == "x.two"


def test_invalid_yaml_raises_load_error(tmp_path, monkeypatch):
    """Invalid YAML in a config produces VerticalLoadError."""
    from lucid.verticals import _loader

    bad_dir = tmp_path / "bad"
    bad_dir.mkdir()
    (bad_dir / "config.yaml").write_text("this: is: not: valid: yaml")

    monkeypatch.setattr(_loader, "VERTICALS_DIR", tmp_path)
    reset_registry_cache()
    with pytest.raises(VerticalLoadError, match="Invalid YAML"):
        load_registry()
