# Lucid &nbsp;·&nbsp; [Install →](https://github.com/Jonnycatx/lucid/releases/latest/download/lucid.skill)

> The fluency layer between human intent and AI output.

[![Built with Claude](https://img.shields.io/badge/Built%20with-Claude-D97757)](https://claude.com)
[![CI](https://github.com/Jonnycatx/lucid/actions/workflows/ci.yml/badge.svg)](https://github.com/Jonnycatx/lucid/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.2.0-orange.svg)](#)
[![MCP](https://img.shields.io/badge/MCP-server-8A2BE2.svg)](https://modelcontextprotocol.io/)

**One click. Zero setup.** Download `lucid.skill` (the link above), open it with Claude Desktop or Cowork, click *Save skill*. Lucid is on. No Python, no API key, no command line. Lucid uses your existing Claude session — nothing extra to configure.

The skill auto-fires on requests where prompt quality matters — documents, code, creative work, analysis. It listens for your true intent, asks one or two clarifying questions if anything required is missing, then produces structured output designed to beat a raw prompt to the same model. Win rate against a 30-prompt eval set with a position-debiased LLM judge is being measured for v0.2 closure; see [`evals/`](evals/).

---

## What's in Lucid

- **One-click skill install** — [download lucid.skill](https://github.com/Jonnycatx/lucid/releases/latest/download/lucid.skill) and open. Zero setup. Uses your existing Claude session, no API key needed. *This is the recommended path for almost everyone.*
- **MCP server (advanced)** — for developers and power users who want fine-grained control: separate Listener / Translator / Validator model selection, prompt caching, multi-turn orchestration. Install via [lucid.plugin](https://github.com/Jonnycatx/lucid/releases/latest/download/lucid.plugin) (Cowork) or `pip install` for direct Claude Desktop config. Requires Python 3.10+ and an Anthropic API key.
- **Universal fluency protocol** — Listen, Clarify, Translate, Validate. Same protocol whether you install the skill or run the MCP server.
- **Eval-gated quality** — 30-prompt eval set with position-debiased LLM-as-judge measures Lucid's win rate against the same model with a raw prompt. Every release has to clear the bar.
- **Open source, auditable** — every line of code, every prompt, every test, every thesis document lives in this repo. MIT-licensed. Built with Claude, in the open.

---

## What Lucid is

The dominant constraint on real-world AI usefulness is not model capability. It is the loss of fidelity in the channel between the human and the model. Lucid closes that channel.

Lucid listens for the user's true intent (including what they did not say), translates it into the shape the underlying model performs best on, validates output against the original intent, and accumulates a model of the user across sessions. It ships as a Model Context Protocol (MCP) server — any MCP-compatible client (Cowork, Claude Desktop, Cursor, Zed) can use it.

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
| **Validator** | Grades output against intent and re-runs on miss. *(Phase 4)* |
| **Memory** | Accumulates a persistent model of the user across sessions. *(Phase 5)* |

## For developers and other MCP clients

If you're a developer, or you use an MCP client other than Cowork, install the OSS package directly.

```bash
git clone https://github.com/Jonnycatx/lucid.git
cd lucid
pip install -e ".[dev]"
pytest                              # 63 tests, no API key needed
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
#   "model_used": "claude-sonnet-4-6"
# }
```

Add Lucid to Claude Desktop's `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lucid": {
      "command": "lucid",
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

## Project status

| Milestone | State |
|---|---|
| Standalone fluency skill (zero-setup install) | Done |
| Vertical schema and first vertical | Done |
| Listener / Translator / pipeline (MCP server, multi-turn clarification) | Done |
| Cowork plugin packaging | Done |
| Eval harness (30 prompts, position-debiased LLM judge) | Done |
| Phase 2 closure: measured win rate vs. baseline | In progress |
| Validator layer | Planned (Phase 4) |
| Memory layer | Planned (Phase 5) |

63 tests passing. CI green across Python 3.10, 3.11, 3.12.

## Project layout

```
lucid/
├── pyproject.toml
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── docs/                          # thesis and build plan
├── skill/                         # Standalone fluency skill (zero-setup install)
│   └── lucid-fluency/SKILL.md
├── plugin/                        # Cowork plugin (manifest, skill, command, MCP)
├── evals/                         # 30-prompt eval set + LLM-as-judge harness
├── src/lucid/
│   ├── server.py                  # FastMCP entry, lucid_run tool
│   ├── listener.py                # Layer 1
│   ├── translator.py              # Layer 2
│   └── verticals/
│       ├── _schema.py             # vertical data model (Pydantic)
│       ├── _loader.py             # discovery + triage
│       └── document/
│           └── config.yaml        # first vertical
└── tests/
```

## Built with Claude

Lucid was designed and largely written through pair-programming with [Claude](https://claude.com), Anthropic's AI assistant. Every line of code, every test, every architecture decision is auditable in this repo's commit history. The same Claude infrastructure (the Anthropic API and the Model Context Protocol) is what Lucid runs on at runtime — so the project is end-to-end aligned with the platform that powers it.

## Contributing

Contributions welcome. The easiest meaningful contribution is adding a new vertical: drop a YAML file under `src/lucid/verticals/<your_vertical>/config.yaml` that satisfies the schema in `_schema.py`. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full guide.

## License

[MIT](LICENSE).
