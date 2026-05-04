# Contributing to Lucid

Thanks for considering a contribution. Lucid is alpha — the architecture is still settling and the eval discipline that gates changes is being built in Phase 2. Read this before opening a PR.

## Project philosophy

- **Fluency, not capability.** Lucid does not ship features that compete with the underlying model. It ships features that improve the channel between the user and the model.
- **Verticals as data, not code.** Adding a new domain should be a YAML file, not a code change. If your contribution requires hardcoded logic for a specific domain, the architecture is wrong — open an issue first.
- **Tests gate everything.** Every change must pass `pytest`. Eval-affecting changes will be gated by the eval suite once Phase 2 ships it.

## Easy first contributions

- **Add a new vertical.** Drop a `config.yaml` under `src/lucid/verticals/<your_vertical>/` that satisfies the schema in `src/lucid/verticals/_schema.py`. Add an eval set under `evals/<your_vertical>/`. Open a PR.
- **Improve an existing vertical's prompt template, rubric, or `why_it_matters` text.** Real-world prompts that produce poor output are the best motivation. Open an issue with the prompt and the bad output, then a PR with the fix.
- **Improve the Listener's extraction prompt.** If the Listener is missing answers it should reasonably catch from the user's text, that is a prompt improvement.
- **Documentation.** Examples in the README, docstrings, the build plan — anything that helps the next reader understand the architecture faster.

## Larger contributions

For new layers (Validator, Memory) or architectural changes, open an issue first to discuss. The build plan in [`docs/plan.md`](docs/plan.md) lays out the intended sequence; deviations are welcome but should be discussed before code.

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
