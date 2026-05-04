"""Vertical discovery and loading.

Verticals live as YAML files under `src/lucid/verticals/<vertical_id>/config.yaml`.
At startup we scan the verticals directory, load each config, validate it against
the schema, and expose a registry keyed by vertical id.

Design notes:
  - Invalid verticals fail loudly at load time. A broken vertical is a deploy
    problem, not a runtime problem; we want the failure visible immediately.
  - The registry is loaded once and cached. Verticals are static config; if
    they change, restart the server.
  - Triage matching lives here too, since it operates on the registry.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

from lucid.verticals._schema import Vertical


VERTICALS_DIR = Path(__file__).resolve().parent
CONFIG_FILENAME = "config.yaml"


class VerticalLoadError(Exception):
    """Raised when a vertical config fails to load or validate."""


def _iter_vertical_config_paths() -> list[Path]:
    """Find every config.yaml under the verticals directory."""
    return sorted(VERTICALS_DIR.glob(f"*/{CONFIG_FILENAME}"))


def load_vertical(config_path: Path) -> Vertical:
    """Load and validate a single vertical from a config.yaml path."""
    if not config_path.is_file():
        raise VerticalLoadError(f"Config not found: {config_path}")
    try:
        with open(config_path) as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise VerticalLoadError(f"Invalid YAML in {config_path}: {e}") from e
    if not isinstance(raw, dict):
        raise VerticalLoadError(
            f"{config_path}: top-level YAML must be a mapping, got {type(raw).__name__}"
        )
    try:
        return Vertical(**raw)
    except Exception as e:
        raise VerticalLoadError(f"Schema validation failed for {config_path}: {e}") from e


@lru_cache(maxsize=1)
def load_registry() -> dict[str, Vertical]:
    """Discover and load every vertical on disk.

    Returns a dict keyed by vertical id. Cached for the lifetime of the process.
    Raises VerticalLoadError on the first invalid vertical encountered.
    Raises ValueError if two verticals declare the same id.
    """
    registry: dict[str, Vertical] = {}
    for config_path in _iter_vertical_config_paths():
        v = load_vertical(config_path)
        if v.id in registry:
            raise ValueError(
                f"Duplicate vertical id '{v.id}': "
                f"{registry[v.id]} and {config_path} both declare it"
            )
        registry[v.id] = v
    return registry


def reset_registry_cache() -> None:
    """Clear the cached registry. Useful for tests."""
    load_registry.cache_clear()


# ----- Triage: match a raw user request to a vertical ---------------------


def triage(intent: str, registry: dict[str, Vertical] | None = None) -> Vertical | None:
    """Pick the best vertical for a raw user request.

    v0.1 strategy: case-insensitive keyword match. Score each vertical by the
    number of its keywords that appear in the intent string. Tiebreak on
    `priority` (higher wins). Return None if nothing matches.

    This will be replaced or augmented by an LLM-driven classifier in a later
    phase, but the keyword version gives us a deterministic, testable baseline.
    """
    reg = registry if registry is not None else load_registry()
    needle = intent.lower()

    best: Vertical | None = None
    best_score = 0
    best_priority = -(10**9)

    for v in reg.values():
        score = sum(1 for kw in v.keywords if kw.lower() in needle)
        if score == 0:
            continue
        if score > best_score or (score == best_score and v.priority > best_priority):
            best = v
            best_score = score
            best_priority = v.priority

    return best
