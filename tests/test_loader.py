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


def test_triage_no_match_returns_fallback():
    """A request with no specialized match returns the fallback vertical."""
    v = triage("what time is it in Tokyo right now")
    assert v is not None
    assert v.id == "general.fluency"
    assert v.is_fallback is True


def test_triage_returns_none_when_no_fallback_in_registry():
    """If a custom registry has no fallback vertical, no_match returns None."""
    only = Vertical(
        id="x.only",
        name="only",
        description="only",
        questions=[
            {"id": "q", "prompt": "p", "type": "text", "why_it_matters": "w"}
        ],
        prompt_template="{q}",
        rubric=[{"id": "r", "name": "r", "description": "r"}],
        keywords=["foo"],
    )
    v = triage("nothing relevant here", registry={only.id: only})
    assert v is None


def test_triage_specialized_beats_fallback():
    """When a specialized vertical matches, the fallback is not selected."""
    v = triage("write a one-pager for the board")
    assert v is not None
    assert v.id == "document.one_pager"


def test_load_registry_includes_fallback():
    """The shipped registry exposes general.fluency as the fallback."""
    reg = load_registry()
    assert "general.fluency" in reg
    assert reg["general.fluency"].is_fallback is True


def test_load_registry_includes_specialized_verticals():
    """Document, creative, and code verticals all load and are non-fallback."""
    reg = load_registry()
    for vid in ("document.one_pager", "creative.story", "code.review"):
        assert vid in reg, f"missing specialized vertical: {vid}"
        assert reg[vid].is_fallback is False


def test_underscore_prefixed_directories_are_skipped():
    """The _template scaffold (and any other _-prefixed dir) is not a vertical
    and must not appear in the registry."""
    reg = load_registry()
    template_ids = [vid for vid in reg if vid.startswith("TODO")]
    assert template_ids == [], (
        f"Underscore-prefixed dirs should be skipped, but found: {template_ids}"
    )
    assert "_template" not in reg
    # Sanity: the _template/config.yaml file exists on disk but isn't loaded.
    from pathlib import Path

    from lucid.verticals._loader import VERTICALS_DIR

    assert (Path(VERTICALS_DIR) / "_template" / "config.yaml").is_file()


def test_triage_routes_creative_prompt_to_creative_story():
    """A clearly creative request hits the creative vertical, not fallback."""
    v = triage("write a short story about an unreliable narrator on a heist")
    assert v is not None
    assert v.id == "creative.story"


def test_triage_routes_code_prompt_to_code_review():
    """A clearly engineering request hits the code vertical, not fallback."""
    v = triage("refactor this Python function for performance and explain Big O")
    assert v is not None
    assert v.id == "code.review"


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


def test_multiple_fallback_verticals_rejected(tmp_path, monkeypatch):
    """If two verticals both declare is_fallback=True, registry load fails."""
    from lucid.verticals import _loader

    common = (
        "questions:\n"
        "  - id: q\n"
        "    prompt: p\n"
        "    type: text\n"
        "    why_it_matters: w\n"
        "prompt_template: '{q}'\n"
        "rubric:\n"
        "  - id: r\n"
        "    name: r\n"
        "    description: r\n"
        "is_fallback: true\n"
    )
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "config.yaml").write_text(f"id: a.fallback\nname: a\ndescription: a\n{common}")
    (b / "config.yaml").write_text(f"id: b.fallback\nname: b\ndescription: b\n{common}")

    monkeypatch.setattr(_loader, "VERTICALS_DIR", tmp_path)
    reset_registry_cache()
    with pytest.raises(ValueError, match="Multiple fallback verticals"):
        load_registry()


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
