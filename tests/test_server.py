"""Tests for the Lucid MCP server's tool logic.

These tests exercise the pure-Python helper `run_lucid`, not the MCP transport.
That keeps the suite fast and avoids needing to spin up a stdio server.
"""

from __future__ import annotations

import pytest

from lucid.server import run_lucid
from lucid.verticals._loader import reset_registry_cache


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    reset_registry_cache()
    yield
    reset_registry_cache()


def test_run_lucid_matches_one_pager():
    out = run_lucid("write a one-pager about our Q3 roadmap for the leadership team")
    assert out["status"] == "stub"
    assert out["vertical"]["id"] == "document.one_pager"
    assert out["intent"].startswith("write a one-pager")
    # Listener's questions are surfaced
    qids = {q["id"] for q in out["questions_listener_would_ask"]}
    assert qids == {"audience", "purpose", "stakes", "constraints"}


def test_run_lucid_no_match():
    out = run_lucid("what time is it in Tokyo")
    assert out["status"] == "no_match"
    assert "No vertical matched" in out["message"]
    assert "document.one_pager" in out["available_verticals"]


def test_run_lucid_with_explicit_hint():
    out = run_lucid(
        "this request has no keywords",
        vertical_hint="document.one_pager",
    )
    assert out["status"] == "stub"
    assert out["vertical"]["id"] == "document.one_pager"


def test_run_lucid_with_unknown_hint():
    out = run_lucid("anything", vertical_hint="not.a.real.vertical")
    assert out["status"] == "unknown_hint"
    assert "not.a.real.vertical" in out["message"]
    assert "document.one_pager" in out["available_verticals"]


def test_response_shape_is_serializable():
    """The dict returned must be JSON-serializable so MCP can transport it."""
    import json

    out = run_lucid("draft an executive summary of the customer research")
    json.dumps(out)  # must not raise


def test_lucid_run_tool_is_directly_callable():
    """The @mcp.tool-decorated function should still be callable as a normal
    Python function. If FastMCP ever changes this, our tests need to know."""
    from lucid.server import lucid_run

    out = lucid_run("write a one-pager about Q3 roadmap")
    assert out["status"] == "stub"
    assert out["vertical"]["id"] == "document.one_pager"
