# Lucid

> The fluency layer between human intent and AI output.

[![CI](https://github.com/Jonnycatx/lucid/actions/workflows/ci.yml/badge.svg)](https://github.com/Jonnycatx/lucid/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](#)
[![MCP](https://img.shields.io/badge/MCP-server-8A2BE2.svg)](https://modelcontextprotocol.io/)

**Status:** Alpha. The runtime pipeline is end-to-end working; the eval gate that closes Phase 2 is the next milestone. See [`docs/plan.md`](docs/plan.md).

## What Lucid is

The dominant constraint on real-world AI usefulness is not model capability. It is the loss of fidelity in the channel between the human and the model. Lucid closes that channel.

Lucid ships as a Model Context Protocol (MCP) server. Any MCP-compatible client — Claude Desktop, Cursor, Zed — can use it. It listens for the user's true intent (including what they did not say), translates that intent into the shape the underlying model performs best on, validates output against the original intent, and accumulates a model of the user across sessions.

## Why Lucid

The thesis: prompt quality is the dominant constraint on AI output quality, and the next hundred million users will not learn to prompt. Whoever closes that gap owns the median AI experience.

- [`docs/thesis.md`](docs/thesis.md) — operator version (why and how, in technical terms)
- [`docs/why-lucid.md`](docs/why-lucid.md) — narrative version (more accessible read)
- [`docs/plan.md`](docs/plan.md) — build plan and roadmap

## How it works

Lucid runs custom orchestration over four layers.

| Layer | Job |
|---|---|
| **Listener** | Extracts true intent — including unspoken constraints — from the user's request. Runs on Haiku. |
| **Translator** | Converts intent into the prompt shape the target model performs best on. Runs on Sonnet 4.6 by default. |
| **Validator** | Grades output against a per-vertical rubric and re-runs on miss. *(Phase 4)* |
| **Memory** | Accumulates a persistent model of the user across sessions. *(Phase 5)* |

Verticals (domain-specific configs) live as YAML files. Adding a new vertical is a config change, not a code change. The first shipping vertical is `document.one_pager` — structured single-page documents (executive summaries, briefs, decision memos).

## Quickstart

```bash
git clone https://github.com/Jonnycatx/lucid.git
cd lucid
pip install -e ".[dev]"
pytest                              # 47 tests, no API key needed
export ANTHROPIC_API_KEY=sk-ant-... # required for live model calls
lucid                               # run the MCP server over stdio
```

Use Lucid programmatically:

```python
from lucid.server import run_lucid

# Turn 1: ambiguous request — Lucid asks for what it's missing
result = run_lucid("draft a one-pager about our Q3 roadmap")
# {
#   "status": "needs_clarification",
#   "questions_to_ask": [
#     {"id": "audience", "prompt": "Who is reading this document?", ...},
#     {"id": "purpose",  "prompt": "What's the desired outcome?", ...}
#   ],
#   ...
# }

# Turn 2: provide the answers — Lucid runs the full pipeline
result = run_lucid(
    "draft a one-pager about our Q3 roadmap",
    answers={"audience": "leadership team", "purpose": "decision"},
)
# {
#   "status": "complete",
#   "result": "## Q3 Roadmap\n\n...",
#   "vertical": {"id": "document.one_pager", ...},
#   "answers_used": {...},
#   "model_used": "claude-sonnet-4-6"
# }
```

Without `ANTHROPIC_API_KEY` set, Lucid runs in stub mode — it returns the rendered prompt rather than calling the API. Useful for inspecting what Lucid *would* send.

## Connect to Claude Desktop

Add Lucid to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lucid": {
      "command": "lucid",
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

Lucid will appear as an available tool in Claude Desktop. The same pattern works for Cursor, Zed, and any MCP-compatible client.

## Project status

| Milestone | State |
|---|---|
| Vertical schema and first vertical | Done |
| Listener (intent extraction via Haiku) | Done |
| Translator (template + Sonnet 4.6) | Done |
| End-to-end pipeline with multi-turn clarification | Done |
| Eval set + DeepEval grading | In progress |
| Validator layer | Planned (Phase 4) |
| Memory layer | Planned (Phase 5) |

47 tests passing. CI green across Python 3.10, 3.11, 3.12.

## Project layout

```
lucid/
├── pyproject.toml
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── docs/
│   ├── thesis.md          # operator-version thesis (why this exists)
│   ├── why-lucid.md       # narrative-version thesis
│   └── plan.md            # build plan
├── src/lucid/
│   ├── server.py          # FastMCP entry, lucid_run tool
│   ├── listener.py        # Layer 1
│   ├── translator.py      # Layer 2
│   └── verticals/
│       ├── _schema.py     # vertical data model (Pydantic)
│       ├── _loader.py     # discovery + triage
│       └── document/
│           └── config.yaml  # first vertical
└── tests/
    ├── test_schema.py
    ├── test_loader.py
    ├── test_listener.py
    ├── test_translator.py
    └── test_server.py
```

## Contributing

Contributions welcome. The easiest meaningful contribution is adding a new vertical: drop a YAML file under `src/lucid/verticals/<your_vertical>/config.yaml` that satisfies the schema in `_schema.py`. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full guide.

## License

[MIT](LICENSE).
