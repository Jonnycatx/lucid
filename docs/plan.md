# Lucid — Build Plan

*Living source of truth. Updated as decisions are made and phases ship.*

---

## What it is
Lucid is the fluency layer between human intent and AI output. It listens for true intent, translates intent into the input shape the model performs best on, accumulates a model of the user across sessions, and validates output against the original intent before returning. See [thesis.md](thesis.md) for the full thesis and [why-lucid.md](why-lucid.md) for the narrative version.

## Architecture (one-line)
Custom Python orchestration server. Exposes itself externally via MCP. Consumes MCP for outbound tool/data needs. Internal layers are in-process Python modules in v1.

---

## Phase 0 decisions — locked

| Decision | Choice | Why |
|---|---|---|
| Public form factor | MCP server | Matches infrastructure thesis. Works in any MCP client (Claude, Cursor, Zed, future). Lands in Anthropic's MCP discovery surfaces. |
| Internal architecture | Custom orchestration in-process; MCP only at external boundary | Pipeline is stateful, multi-step, conditional — wrong fit for pure MCP request-response. |
| Language | Python | FastMCP 3.0 is the de facto standard. AI/ML library coverage is Python-first. DeepEval is Python. |
| MCP framework | FastMCP (`mcp` PyPI package) | Decorator-based, auto-schema, minimal boilerplate. Official Anthropic SDK. |
| Eval framework | DeepEval | 50+ metrics. Native pytest integration → eval gates run in CI. |
| License | MIT | Maximum adoption surface. |
| Repo layout | Standard Python `src/` package | Recognized instantly by Python OSS contributors. |
| First vertical | Structured document creation | Serves the thesis (next 100M users don't write code). Less crowded than code-gen prompt enhancement. |
| Pipeline latency budget | 5–15s with UI streaming | Industry standard for AI products in 2026. |
| Triage in v1 | Required | Without triage, every casual request pays the fluency tax. |
| Cost optimization stack | Haiku 4.5 for Listener/Validator + Anthropic prompt caching + triage bypass | ~5–10% cost overhead vs. raw baseline. |
| Listener mode | Interactive (ask user when info missing) | Higher quality output. Matches the validator-loop thesis. |
| Default execution model | Sonnet 4.6 | Strong on writing, fits 5–15s budget, sensible cost. |

## Phase 0 decisions — deferred

- Detailed memory architecture (deferred to Phase 5; Phase 1 reserves the data layer placeholder)

---

## Build phases

| Phase | Outcome | Exit criterion | Status |
|---|---|---|---|
| 0 | Decisions locked | This document complete | DONE |
| 1 | Foundation | Repo skeleton; schema defined; loader + triage; MCP server skeleton; CI wired | DONE |
| 2 | First vertical end-to-end | Listener + Translator on document vertical; eval bar hit | IN PROGRESS — pipeline done; eval set + measurement remaining |
| 3 | Generality | Two more verticals added; architecture transfers without core rewrite | pending |
| 4 | Validator | Output graded against rubric; re-run on miss; loop closes | pending |
| 5 | Memory | Per-user, per-vertical persistence; encrypted, exportable, auditable | pending |
| 6 | Public release | README polish, branding, contributor guide, GitHub launch | partial — repo public, polish ongoing |

## What's shipping today (v0.1.0)

- Pydantic vertical schema with cross-field placeholder validation
- One vertical: `document.one_pager` (structured document creation)
- Vertical loader with keyword + priority triage
- Listener (intent extraction via Haiku tool-use)
- Translator (renders template, calls Sonnet 4.6 by default)
- FastMCP server exposing `lucid_run` with multi-turn clarification flow
- 47 tests passing across schema, loader, listener, translator, and pipeline
- CI green on Python 3.10, 3.11, 3.12

## What's next for Phase 2 closure

- Eval set: 10–20 real document-creation prompts with structured rubric
- DeepEval-based grader using each vertical's rubric
- Baseline runner: raw prompt to same model, for comparison
- Acceptance bar: measurable lift over baseline before Phase 2 closes

---

## Repository layout

```
lucid/
├── pyproject.toml
├── README.md
├── LICENSE                 # MIT
├── docs/
│   ├── thesis.md           # operator version (canonical)
│   ├── why-lucid.md        # narrative version
│   └── plan.md             # this file
├── src/lucid/
│   ├── __init__.py
│   ├── server.py           # FastMCP entry, lucid_run tool
│   ├── listener.py         # Layer 1
│   ├── translator.py       # Layer 2
│   ├── memory.py           # Layer 3 — Phase 5
│   ├── validator.py        # Layer 4 — Phase 4
│   └── verticals/
│       ├── _schema.py
│       ├── _loader.py
│       └── document/
│           └── config.yaml # First vertical
├── evals/                  # Per-vertical eval sets — Phase 2
├── tests/
└── .github/workflows/ci.yml
```

## Hardware requirements (developer)

Standard Mac, Windows, or Linux. No GPU. Heavy compute is Anthropic API calls. Local resource needs: Python 3.10+, ~500MB disk for dependencies, an editor.

## Stack at a glance

- Python 3.10+
- `mcp` (FastMCP) — MCP server framework
- `anthropic` — model API client
- `pydantic` — data structures
- `pyyaml` — vertical configs
- `deepeval` — eval framework (pytest-integrated)
- `pytest` — tests + eval runner
- GitHub Actions — CI
