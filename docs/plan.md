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
| 2 | First vertical end-to-end | Listener + Translator on document vertical; eval bar hit | DONE — published 79.4% decisive win rate on n=51, position-debiased Opus 4.6 judge ([`evals/results/skill-full.json`](../evals/results/skill-full.json)) |
| 3 | Generality | Two more verticals added; architecture transfers without core rewrite | DONE — 10 specialized verticals shipped (document, email, marketing, social, creative, code, explain.feynman, explain.socratic, analysis, prompt.image) plus universal fallback |
| 4 | Validator | Output graded against rubric; re-run on miss; loop closes | DONE — opt-in via `validate=True` on `run_lucid` |
| 5 | Memory | Per-user, per-vertical persistence; encrypted, exportable, auditable | pending |
| 6 | Public release | README polish, branding, contributor guide, GitHub launch | DONE — demo at [jonnycatx.github.io/lucid](https://jonnycatx.github.io/lucid/), `CONTRIBUTING.md` and `docs/authoring-a-vertical.md` shipped, principles canonized in `docs/principles.md`, three GitHub releases tagged. Org rename to `lucid-fluency` deferred to launch moment. |

## What's shipping today (v0.2.0)

- Pydantic vertical schema with cross-field placeholder validation
- 11 verticals: 10 specialized (document, email, marketing, social, creative, code, explain.feynman, explain.socratic, analysis, prompt.image) plus `general.fluency` universal fallback
- Vertical loader with keyword + priority triage and underscore-prefix exclusion (for the `_template/` scaffold)
- Listener (intent extraction via Haiku 4.5 tool-use, with prompt caching and graceful API-error handling)
- Translator (renders template, calls Sonnet 4.6 by default, system prompt sent as cacheable content block)
- Validator — Phase 4 (rubric grading via Sonnet 4.6, opt-in via `validate=True`, one-rerun budget on miss)
- FastMCP server exposing `lucid_run` with multi-turn clarification flow + the new `validate` parameter
- `lucid-check` health command with optional `--live` API smoke test
- 102 tests passing
- CI green on Python 3.10, 3.11, 3.12

## What's next (v0.3 candidates)

- 2-turn eval mode in the harness (so multi-turn verticals like `explain.socratic` are judged on the realistic flow rather than one-shot)
- `--runner lucid` n=51 eval to measure the MCP-pipeline path against the skill (validates the "advanced install" claim)
- Iterate on the three eval-weak verticals: `code.review`, `prompt.image`, and the marketing value-prop specificity miss
- LLM-based triage (Haiku classifier) to catch phrasings keyword-substring matching misses
- PyPI publication so `pip install lucid` works without `git clone`
- CI eval gate (n=3 per PR) to prevent quality regressions
- Phase 5 — Memory layer (significant build, deferred until eval discipline is consistently green)

---

## Repository layout

```
lucid/
├── pyproject.toml
├── README.md
├── LICENSE                          # MIT
├── CONTRIBUTING.md
├── docs/
│   ├── thesis.md                    # operator version (canonical)
│   ├── why-lucid.md                 # narrative version
│   ├── plan.md                      # this file
│   ├── principles.md                # universal craft principles
│   ├── authoring-a-vertical.md      # contributor onramp
│   ├── punch-list.md                # tactical roadmap (living)
│   ├── audit-2026-05-05.md          # full project audit
│   └── index.html                   # demo site (served via GH Pages)
├── skill/lucid-fluency/SKILL.md     # standalone fluency skill
├── plugin/                          # Cowork plugin bundle
│   ├── .claude-plugin/plugin.json
│   ├── .mcp.json
│   ├── README.md
│   ├── commands/lucid.md            # /lucid slash command
│   └── skills/lucid-fluency/SKILL.md
├── src/lucid/
│   ├── __init__.py
│   ├── server.py                    # FastMCP entry, lucid_run tool
│   ├── check.py                     # lucid-check health command
│   ├── listener.py                  # Layer 1 — intent extraction
│   ├── translator.py                # Layer 2 — prompt rendering + execution
│   ├── validator.py                 # Layer 4 — rubric grading, re-run on miss
│   └── verticals/
│       ├── _schema.py               # Pydantic schema, cross-field validators
│       ├── _loader.py               # discovery + keyword triage + fallback
│       ├── _template/               # scaffold for new verticals (skipped at load)
│       ├── general/                 # universal fallback (is_fallback: true)
│       ├── document/                # document.one_pager
│       ├── email/                   # email.professional
│       ├── marketing/               # marketing.copy
│       ├── social/                  # social.thread
│       ├── creative/                # creative.story
│       ├── code/                    # code.review
│       ├── explain_feynman/         # explain.feynman
│       ├── explain_socratic/        # explain.socratic
│       ├── analysis_recommendation/ # analysis.recommendation
│       └── prompt_image/            # prompt.image
├── evals/
│   ├── prompts.yaml                 # 51-prompt eval set
│   ├── harness.py                   # baseline + treatment + debiased judge
│   └── results/                     # saved JSON evidence trail
├── tests/                           # 102 tests
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
