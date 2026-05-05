"""Tests for the Lucid health-check command."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from lucid.check import _mask_key, _truncate, check, main
from lucid.verticals._loader import reset_registry_cache


@pytest.fixture(autouse=True)
def _clear_registry_cache():
    reset_registry_cache()
    yield
    reset_registry_cache()


# ----- Pure helpers -------------------------------------------------------


def test_mask_key_short_string():
    assert _mask_key("abc") == "***"


def test_mask_key_full_format():
    masked = _mask_key("sk-ant-1234567890abcdef")
    assert masked.startswith("sk-ant-")
    assert masked.endswith("cdef")
    assert "…" in masked


def test_truncate_below_limit():
    assert _truncate("hello", 10) == "hello"


def test_truncate_above_limit():
    out = _truncate("a very long input", 8)
    assert len(out) == 8
    assert out.endswith("…")


# ----- check() integration ------------------------------------------------


def test_check_passes_in_stub_mode_with_no_api_key(monkeypatch, capsys):
    """No API key set → all real checks pass, exit code is 1 (warning only)."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    rc = check(live=False)
    captured = capsys.readouterr().out
    assert "Package importable" in captured
    assert "Registry loaded" in captured
    assert "Triage" in captured
    assert "document.one_pager" in captured
    assert "general.fluency (fallback)" in captured
    assert "Pipeline (stub mode)" in captured
    assert "ANTHROPIC_API_KEY is not set" in captured
    # Warning state → non-zero exit
    assert rc == 1
    assert "Lucid is working but degraded" in captured


def test_check_passes_with_api_key_no_live(monkeypatch, capsys):
    """API key set but --live not passed → fully healthy, exit 0."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-1234567890abcdef")
    rc = check(live=False)
    captured = capsys.readouterr().out
    assert "ANTHROPIC_API_KEY is set" in captured
    assert "sk-ant-" in captured
    assert "cdef" in captured  # masked tail
    assert rc == 0
    assert "Lucid is healthy" in captured


def test_check_with_live_but_no_key_fails(monkeypatch, capsys):
    """--live requested but no key → fails with a useful message."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    rc = check(live=True)
    captured = capsys.readouterr().out
    assert "--live requested but ANTHROPIC_API_KEY is not set" in captured
    assert rc == 1


def test_main_no_args_runs_check(monkeypatch):
    """main() with no args runs the default check."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-1234567890abcdef")
    rc = main([])
    assert rc == 0


def test_main_live_flag_parses(monkeypatch):
    """--live flag is recognized and routes to live mode."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # No key → live mode fails fast without making a real API call.
    rc = main(["--live"])
    assert rc == 1


def test_check_handles_registry_failure(monkeypatch, capsys):
    """If the registry can't load, check fails fast and prints why."""
    from lucid.verticals import _loader

    def boom():
        raise RuntimeError("synthetic registry error")

    monkeypatch.setattr(_loader, "load_registry", boom)
    rc = check(live=False)
    captured = capsys.readouterr().out
    assert "Registry failed to load" in captured
    assert "synthetic registry error" in captured
    assert rc == 1
