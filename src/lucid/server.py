"""Lucid MCP server.

Exposes Lucid's fluency layer as a Model Context Protocol server. Any
MCP-compatible client (Claude, Cursor, Zed, others) can use it.

v0.1 surface:
  - lucid_run(intent, vertical_hint=None)
    Triage-only stub. Returns the matched vertical and the questions the
    Listener would ask. The full pipeline (Listener → Translator →
    Validator → Memory) is implemented in Phase 2 and beyond.

Run as a stdio MCP server:
    lucid                       # via the console script defined in pyproject.toml
    python -m lucid.server      # equivalent direct invocation
"""

from __future__ import annotations

from typing import Any, Optional

from mcp.server.fastmcp import FastMCP

from lucid.verticals._loader import load_registry, triage
from lucid.verticals._schema import Vertical


mcp = FastMCP("lucid")


# ----- Internal helpers (testable without going through MCP transport) ----


def _vertical_summary(v: Vertical) -> dict[str, Any]:
    """Compact serialization of a vertical for tool responses."""
    return {
        "id": v.id,
        "name": v.name,
        "version": v.version,
        "output_format": v.output_format.value,
    }


def _questions_summary(v: Vertical) -> list[dict[str, Any]]:
    """Serialize the Listener's question schema for tool responses."""
    return [
        {
            "id": q.id,
            "prompt": q.prompt,
            "type": q.type.value,
            "required": q.required,
            "options": q.options,
            "why_it_matters": q.why_it_matters,
        }
        for q in v.questions
    ]


def run_lucid(intent: str, vertical_hint: Optional[str] = None) -> dict[str, Any]:
    """Pure-Python implementation of the lucid_run tool.

    Separated from the MCP-decorated function so tests can call it directly
    without spinning up the MCP transport.
    """
    registry = load_registry()

    # If the caller forced a vertical, use it (or report unknown).
    if vertical_hint:
        vertical = registry.get(vertical_hint)
        if vertical is None:
            return {
                "status": "unknown_hint",
                "message": (
                    f"vertical_hint '{vertical_hint}' is not in the registry. "
                    f"Available: {sorted(registry.keys())}"
                ),
                "intent": intent,
                "available_verticals": sorted(registry.keys()),
            }
    else:
        vertical = triage(intent, registry)

    if vertical is None:
        return {
            "status": "no_match",
            "message": (
                "No vertical matched the request. In v0.1 this returns a stub. "
                "Later phases will fall through to a generic baseline pipeline."
            ),
            "intent": intent,
            "available_verticals": sorted(registry.keys()),
        }

    return {
        "status": "stub",
        "message": (
            "Lucid v0.1 skeleton. Vertical triage completed. "
            "The full Listener → Translator → Validator pipeline is not yet implemented."
        ),
        "intent": intent,
        "vertical": _vertical_summary(vertical),
        "questions_listener_would_ask": _questions_summary(vertical),
    }


# ----- MCP-exposed tool ---------------------------------------------------


@mcp.tool()
def lucid_run(intent: str, vertical_hint: Optional[str] = None) -> dict[str, Any]:
    """Run the Lucid fluency layer on a user request.

    In v0.1 this is a skeleton: it performs vertical triage and returns the
    matched vertical along with the questions the Listener would ask. The
    full pipeline is implemented in later phases.

    Args:
      intent: The user's raw request.
      vertical_hint: Optional vertical id to use directly, bypassing triage.

    Returns:
      A structured dict describing what would happen. See README for schema.
    """
    return run_lucid(intent=intent, vertical_hint=vertical_hint)


# ----- Entry point --------------------------------------------------------


def main() -> None:
    """Console-script entry. Runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
