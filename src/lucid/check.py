"""Lucid health check.

A user-facing smoke test that answers the question "is Lucid working?"
without requiring an Anthropic API key. Runs as both a console script
(`lucid-check`) and a module (`python -m lucid.check`).

What it verifies:
  1. The package is importable and reports a version.
  2. The vertical registry loads cleanly and contains the expected
     verticals (specialized + fallback).
  3. Triage routes a representative prompt to a sensible vertical.
  4. The full pipeline runs end-to-end in stub mode (no API call) and
     produces a rendered prompt.
  5. Whether ANTHROPIC_API_KEY is set. Optional `--live` flag attempts
     a real Listener call to confirm auth.

Output is short, human-readable, and uses ASCII checkmarks so it works
in any terminal. Exit code is 0 if everything passes, 1 if anything
fails or warns.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Optional

CHECK = "[✓]"
WARN = "[!]"
FAIL = "[x]"


def _print(symbol: str, message: str) -> None:
    print(f"  {symbol} {message}")


def _section(title: str) -> None:
    print()
    print(title)
    print("=" * len(title))


def check(live: bool = False) -> int:
    """Run the health check. Returns the suggested exit code.

    Returns:
      0 if everything healthy.
      1 if anything failed or warned.
    """
    print("Lucid health check")
    print()

    had_warnings = False
    had_failures = False

    # 1. Import + version
    try:
        import lucid  # noqa: F401

        version = _try_get_version()
        _print(CHECK, f"Package importable (version {version})")
    except Exception as exc:  # noqa: BLE001
        _print(FAIL, f"Failed to import lucid: {exc}")
        return 1

    # 2. Registry
    try:
        from lucid.verticals._loader import load_registry

        registry = load_registry()
        specialized = sorted(v.id for v in registry.values() if not v.is_fallback)
        fallback = next((v for v in registry.values() if v.is_fallback), None)

        _print(CHECK, f"Registry loaded ({len(registry)} verticals)")
        for vid in specialized:
            print(f"      - {vid}")
        if fallback is not None:
            print(f"      - {fallback.id} (fallback)")
        else:
            _print(WARN, "No fallback vertical declared (general.fluency missing?)")
            had_warnings = True
    except Exception as exc:  # noqa: BLE001
        _print(FAIL, f"Registry failed to load: {exc}")
        return 1

    # 3. Triage smoke test
    try:
        from lucid.verticals._loader import triage

        sample = "draft a one-pager about Q3 priorities for the leadership team"
        v = triage(sample)
        if v is None:
            _print(FAIL, f"Triage returned no vertical for sample request")
            had_failures = True
        else:
            _print(CHECK, f'Triage: "{_truncate(sample)}" → {v.id}')
    except Exception as exc:  # noqa: BLE001
        _print(FAIL, f"Triage error: {exc}")
        had_failures = True

    # 4. Pipeline smoke test (stub mode)
    try:
        from lucid.server import run_lucid

        result = run_lucid(
            intent="draft a one-pager about Q3",
            answers={"audience": "leadership team", "purpose": "decision"},
            client=None,
        )
        status = result.get("status")
        if status == "complete" and result.get("rendered_prompt"):
            _print(CHECK, "Pipeline (stub mode): produced rendered prompt")
        else:
            _print(
                FAIL,
                f"Pipeline returned unexpected status: {status} "
                f"(message: {result.get('message', '')[:80]})",
            )
            had_failures = True
    except Exception as exc:  # noqa: BLE001
        _print(FAIL, f"Pipeline error: {exc}")
        had_failures = True

    # 5. API key presence
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        masked = _mask_key(api_key)
        _print(CHECK, f"ANTHROPIC_API_KEY is set ({masked})")
    else:
        _print(
            WARN,
            "ANTHROPIC_API_KEY is not set — Lucid will run in stub mode "
            "(rendered prompts only, no model calls)",
        )
        had_warnings = True

    # 6. Optional: live API test
    if live:
        if not api_key:
            _print(FAIL, "--live requested but ANTHROPIC_API_KEY is not set")
            had_failures = True
        else:
            ok = _live_listener_test()
            if ok:
                _print(CHECK, "Live API test: Listener extraction call succeeded")
            else:
                had_failures = True

    # Summary
    print()
    if had_failures:
        print(f"{FAIL} Lucid has problems. See messages above.")
        return 1
    if had_warnings:
        print(f"{WARN} Lucid is working but degraded — see warnings above.")
        return 1
    print(f"{CHECK} Lucid is healthy.")
    return 0


# ----- Internals ----------------------------------------------------------


def _try_get_version() -> str:
    """Return the installed lucid version, or '(unknown)' if it can't be read."""
    try:
        from importlib.metadata import version

        return version("lucid")
    except Exception:  # noqa: BLE001
        return "(unknown)"


def _truncate(s: str, n: int = 60) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _mask_key(key: str) -> str:
    if len(key) <= 12:
        return "*" * len(key)
    return key[:7] + "…" + key[-4:]


def _live_listener_test() -> bool:
    """Make a small real Listener call to verify auth + connectivity. Returns
    True on success, False on any failure (with the failure printed)."""
    try:
        from anthropic import Anthropic

        from lucid.listener import run_listener
        from lucid.verticals._loader import load_registry

        client = Anthropic()
        registry = load_registry()
        vertical = registry.get("document.one_pager")
        if vertical is None:
            _print(FAIL, "Live test: document.one_pager vertical missing")
            return False
        result = run_listener(
            intent="recommend killing product X to the leadership team",
            vertical=vertical,
            client=client,
        )
        if result.error is not None:
            _print(FAIL, f"Live test: {result.error}")
            return False
        return True
    except Exception as exc:  # noqa: BLE001
        _print(FAIL, f"Live test failed: {type(exc).__name__}: {exc}")
        return False


# ----- CLI ---------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="lucid-check",
        description=(
            "Run a Lucid health check. Verifies the package, vertical "
            "registry, triage, and pipeline. Pass --live to also attempt "
            "a real Anthropic API call."
        ),
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Make a real API call to verify ANTHROPIC_API_KEY works.",
    )
    args = parser.parse_args(argv)
    return check(live=args.live)


if __name__ == "__main__":
    sys.exit(main())
