# Contributing to Lucid

Thanks for considering a contribution. Lucid is at v0.2.0 — Phases 1 through 4 of the build plan are shipped, Phase 5 (Memory) is the only major roadmap item remaining. The eval discipline is real and the published headline win rate (79.4% decisive on n=51, position-debiased Opus 4.6 judge) is the bar new contributions are measured against.

Read this before opening a PR.

## Project philosophy

- **Fluency, not capability.** Lucid does not ship features that compete with the underlying model. It ships features that improve the channel between the user and the model.
- **Verticals as data, not code.** Adding a new domain should be a YAML file, not a code change. If your contribution requires hardcoded logic for a specific domain, the architecture is wrong — open an issue first.
- **Tests gate everything.** Every change must pass `pytest` (currently 102 tests). Eval-affecting changes — skill body, vertical templates, rubrics — should ideally be re-measured against the eval set before merge. CI eval gating is on the v0.3 roadmap.

## Easy first contributions

- **Add a new vertical.** Drop a `config.yaml` under `src/lucid/verticals/<your_vertical>/` that satisfies the schema in `src/lucid/verticals/_schema.py`. The full step-by-step is in [`docs/authoring-a-vertical.md`](docs/authoring-a-vertical.md) — about ten minutes if you copy from an existing vertical and specialize. Add representative prompts to `evals/prompts.yaml` so the harness measures your vertical. Open a PR.
- **Improve an existing vertical's prompt template, rubric, or `why_it_matters` text.** Real-world prompts that produce poor output are the best motivation. Open an issue with the prompt and the bad output, then a PR with the fix.
- **Improve the Listener's extraction prompt.** If the Listener is missing answers it should reasonably catch from the user's text, that is a prompt improvement.
- **Documentation.** Examples in the README, docstrings, the build plan — anything that helps the next reader understand the architecture faster.

## Larger contributions

For new layers (Memory is the only major one remaining — Validator shipped in v0.2.0) or architectural changes, open an issue first to discuss. The build plan in [`docs/plan.md`](docs/plan.md) and the tactical roadmap in [`docs/punch-list.md`](docs/punch-list.md) lay out the intended sequence; deviations are welcome but should be discussed before code.

## Setup

```bash
git clone https://github.com/Jonnycatx/lucid.git
cd lucid
pip install -e ".[dev]"
pytest
```

CI runs the same `pytest` invocation against Python 3.10, 3.11, and 3.12.

## Code style

- Pydantic v2 patterns throughout. Use `field_validator` and `model_validator`.
- Type hints everywhere. PEP 604 union syntax (`str | None`) preferred over `Optional`.
- Docstrings on public functions. Module-level docstrings when the design choice is non-obvious.
- No silent failures. When the system can't do something, it must say so loudly with a precise message.

## Commits

- Imperative mood ("Add validator", not "Added validator").
- Reference the phase if it's part of the build plan ("Phase 4: Validator layer").
- Squash trivial fixups before merging.

## License

By contributing, you agree your contribution is licensed under [MIT](LICENSE).
