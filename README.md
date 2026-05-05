# Lucid &nbsp;·&nbsp; [Demo](https://jonnycatx.github.io/lucid/) &nbsp;·&nbsp; [Install ↓](#install) &nbsp;·&nbsp; [Thesis](docs/thesis.md)

> The fluency layer between human intent and AI output.

[![CI](https://github.com/Jonnycatx/lucid/actions/workflows/ci.yml/badge.svg)](https://github.com/Jonnycatx/lucid/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**One click. Zero setup.** [Download `lucid.skill`](https://github.com/Jonnycatx/lucid/releases/latest/download/lucid.skill), open it with Claude Desktop or Cowork, click *Save skill*. Lucid is on. No Python, no API key, no command line. Lucid uses your existing Claude session — nothing extra to configure.

The skill auto-fires on requests where prompt quality matters — documents, code, creative work, analysis. It listens for your true intent, asks one or two clarifying questions if anything required is missing, then produces structured output designed to beat a raw prompt to the same model. Win rate against a 30-prompt eval set with a position-debiased LLM judge is being measured for v0.2 closure; see [`evals/`](evals/).

> **Capability is a race. Fluency is a moat.**

See it in action at [**jonnycatx.github.io/lucid**](https://jonnycatx.github.io/lucid/) — same prompt, same model, with Lucid and without.

---

## What's in Lucid

- **One-click skill install** — auto-fires on deliverable requests. Zero setup, zero API key, uses your existing Claude session. *Recommended for almost everyone.*
- **MCP server (advanced)** — full pipeline with fine-grained control: separate Listener / Translator / Validator model selection, prompt caching, multi-turn orchestration. Install via [`lucid.plugin`](https://github.com/Jonnycatx/lucid/releases/latest/download/lucid.plugin) (Cowork) or `git clone` + `pip install -e .` for direct Claude Desktop config. Requires Python 3.10+ and an Anthropic API key. *(PyPI release with `pip install lucid` ships with v0.3 once eval-gated win-rate is published.)*
- **Universal fluency protocol** — Listen, Clarify, Translate, Validate. Same protocol whether you install the skill or run the MCP server.
- **Eval-gated quality** — 30-prompt eval set with position-debiased LLM-as-judge measures Lucid's win rate against the same model with a raw prompt. Every release has to clear the bar.
- **Open source, auditable** — every line of code, every prompt, every test, every thesis document lives in this repo. MIT-licensed.

---

## Install

### The skill — recommended, zero setup

[Download `lucid.skill`](https://github.com/Jonnycatx/lucid/releases/latest/download/lucid.skill) and open it with Claude Desktop or Cowork. The skill auto-fires on requests where prompt quality matters. No Python, no API key, no command line.

### The plugin — Cowork

[Download `lucid.plugin`](https://github.com/Jonnycatx/lucid/releases/latest/download/lucid.plugin) and install via Cowork's plugin manager. Adds the `/lucid` slash command and runs the full MCP pipeline (separate Listener + Translator + Validator models, prompt caching, multi-turn orchestration).

### The MCP server — developers and other MCP clients

```bash
git clone https://github.com/Jonnycatx/lucid.git
cd lucid
pip install -e ".[dev]"
pytest                              # 102 tests, no API key needed
lucid-check                         # health check: registry, triage, pipeline
export ANTHROPIC_API_KEY=sk-ant-... # required for live model calls
lucid-check --live                  # confirms auth + connectivity
lucid                               # run the MCP server over stdio
```

`lucid-check` is a no-API-needed smoke test that confirms the package is installed correctly, all verticals loaded, triage works, and the pipeline runs end-to-end in stub mode. Pass `--live` once you've set your API key to verify auth.

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
    validate=True,  # optional: grade output and re-run on miss
)
# {
#   "status": "complete",
#   "result": "## Q3 Roadmap\n\n...",
#   "model_used": "claude-sonnet-4-6",
#   "validation": {"weighted_score": 0.88, "passed": true, ...}
# }
```

---

## How it works

Four layers between your request and the model.

| Layer | Job |
|---|---|
| **Listener** | Extracts true intent — including unspoken constraints — from the user's request. Runs on Haiku 4.5. |
| **Translator** | Converts intent into the prompt shape the target model performs best on. Runs on Sonnet 4.6 by default. |
| **Validator** | Grades output against the vertical's rubric and re-runs the Translator once on miss. Opt-in via `validate=True`. |
| **Memory** | Accumulates a persistent model of the user across sessions. *(Phase 5)* |

---

## Project status

| Milestone | State |
|---|---|
| Skill (zero-setup install) | Shipped |
| MCP server: Listener + Translator + multi-turn clarification | Shipped |
| Validator layer: rubric grading + one-rerun budget | Shipped — opt-in |
| Cowork plugin packaging | Shipped |
| Eval harness (30 prompts, position-debiased LLM judge) | Shipped |
| Measured win rate vs. baseline | In progress |
| Memory layer | Planned (Phase 5) |

**102 tests passing.** CI green on Python 3.10 / 3.11 / 3.12.

## Read more

- [`docs/thesis.md`](docs/thesis.md) — operator version (why and how, in technical terms)
- [`docs/why-lucid.md`](docs/why-lucid.md) — narrative version, more accessible read
- [`docs/plan.md`](docs/plan.md) — build plan and roadmap
- [`docs/authoring-a-vertical.md`](docs/authoring-a-vertical.md) — add a new domain in 10 minutes

## Built with Claude

Lucid was designed and largely written through pair-programming with [Claude](https://claude.com), Anthropic's AI assistant. Every line of code, every test, every architecture decision is auditable in this repo's commit history. The same Claude infrastructure (the Anthropic API and the Model Context Protocol) is what Lucid runs on at runtime — so the project is end-to-end aligned with the platform that powers it.

## Contributing

The easiest meaningful contribution is adding a new vertical — about ten minutes once you've read [`docs/authoring-a-vertical.md`](docs/authoring-a-vertical.md). See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the broader guide (project philosophy, setup, code style, commit format).

## License

[MIT](LICENSE).
