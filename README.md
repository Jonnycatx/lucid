# Lucid

> The fluency layer between human intent and AI output.

**Status:** Alpha. Under active development. Not yet ready for production use.

## What Lucid is

The dominant constraint on real-world AI usefulness is not model capability. It is the loss of fidelity in the channel between the human and the model. Lucid closes that channel.

Lucid listens for the user's true intent (including what they did not say), translates that intent into the shape the underlying model performs best on, validates the output against the original intent, and accumulates a model of the user across sessions.

## Architecture

Lucid ships as a Model Context Protocol (MCP) server. Any MCP-compatible client — Claude, Cursor, Zed, others — can use it. Internally it runs custom orchestration logic over four layers:

- **Listener** — extracts true intent, including unspoken constraints.
- **Translator** — converts intent into the optimal prompt for the target model.
- **Validator** — grades output against a per-vertical rubric and re-runs on miss.
- **Memory** — accumulates a persistent model of the user across sessions.

Verticals (domain-specific configs) live as YAML files. Adding a new vertical is a config change, not a code change.

## Project status

Currently shipping: the vertical schema (`src/lucid/verticals/_schema.py`), the first vertical (structured document creation), and a passing test suite.

In progress: vertical loader, FastMCP server entry point, Listener and Translator implementation, Validator layer, Memory layer.

See `lucid-plan.md` for the full build plan and `fluency-thesis-operator.md` for the underlying thesis.

## Install (alpha)

Requires Python 3.10 or later. From the repository root:

```bash
pip install -e ".[dev]"
pytest
```

## Contributing

Contributions are welcome once the v0.1 milestone ships. The first thing to read is the build plan, then the thesis. Adding a new vertical is the easiest way to contribute meaningfully — see `docs/adding-a-vertical.md` (coming soon).

## License

MIT — see [LICENSE](LICENSE).
