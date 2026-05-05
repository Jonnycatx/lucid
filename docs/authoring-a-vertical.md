# Authoring a Lucid Vertical

A "vertical" is a domain Lucid is fluent in — documents, code review, creative writing, and so on. Adding a new one is a single YAML file. This guide walks through the whole flow end to end.

**Start here:**

- [`_template/config.yaml`](../src/lucid/verticals/_template/config.yaml) — fully-commented scaffold with TODO placeholders. **This is what you copy.** Underscore-prefixed directories are skipped by the registry, so the template never loads as a real vertical.
- [`docs/principles.md`](principles.md) — the universal craft principles your vertical's `system_prompt` should reflect. Read this before drafting your prompt template.

**Reference verticals** (read for examples, don't copy their content):

- [`general/`](../src/lucid/verticals/general/config.yaml) — the universal fallback. Form-agnostic, soft defaults, never blocks.
- [`document/`](../src/lucid/verticals/document/config.yaml) — narrow, opinionated, structurally strict (one-pager / executive summary).
- [`creative/`](../src/lucid/verticals/creative/config.yaml) — specialized but tonally flexible (fiction, scenes, ad copy).
- [`code/`](../src/lucid/verticals/code/config.yaml) — specialized with engineering-specific conventions and choice-typed answers.

---

## What a vertical is

A vertical is data, not code. It tells Lucid four things for one domain:

| Part | Job |
|---|---|
| **Questions** | What does the Listener need to know to produce great output? |
| **Prompt template** | How should the Translator shape the prompt sent to the execution model? |
| **System prompt** | What role / discipline should the model adopt for this domain? |
| **Rubric** | How will the Validator (Phase 4) grade the output? |
| **Triage** | Keywords and priority that decide which vertical handles which request. |

The schema is defined in [`_schema.py`](../src/lucid/verticals/_schema.py). The loader in [`_loader.py`](../src/lucid/verticals/_loader.py) discovers every `config.yaml` under `src/lucid/verticals/<id>/`, validates it, and registers it.

---

## When to add a vertical

**Add a vertical when** you have a domain where the right output shape is genuinely different from a generic deliverable — different opening, different structure, different success criteria. Examples that justify a vertical:

- A specific document genre (one-pager, RFC, post-mortem)
- A creative form with strong conventions (haiku, ad script, brand voice)
- An engineering task with specific output expectations (code review, refactor, threat model)

**Don't add a vertical when** the request is just "produce a good version of X." That's what `general.fluency` is for. If your vertical's prompt template would be 80% the same as `general.fluency`, the fallback will already handle it.

---

## The 10-minute walkthrough

### 1. Pick an id and create the directory

Verticals live under `src/lucid/verticals/<your_vertical>/`. The id is dot-namespaced, top level is the broad domain.

```bash
mkdir -p src/lucid/verticals/recipe
touch src/lucid/verticals/recipe/__init__.py
touch src/lucid/verticals/recipe/config.yaml
```

The id should be `<domain>.<subtype>`: `document.one_pager`, `creative.story`, `code.review`. For a single-vertical domain, `<domain>.<subtype>` is still preferred — it leaves room for siblings later.

### 2. Copy the template, not a real vertical

Copy `src/lucid/verticals/_template/config.yaml` into your new directory. Every field has a `# TODO` marker and an inline note explaining what to fill in. Reference verticals (above) show what filled-in versions look like in practice — read them for examples, but copy from the template.

```bash
cp src/lucid/verticals/_template/config.yaml src/lucid/verticals/recipe/config.yaml
```

### 3. Fill in the questions

Questions are what the Listener tries to extract from the user's request. Each one has:

```yaml
- id: audience            # stable identifier; used as {audience} in prompt_template
  prompt: Who is reading this?     # what the Listener asks (or infers)
  type: text                       # text | choice | multi | number | boolean
  options: []                      # required for choice/multi
  required: false                  # false → uses default if unanswered
  default: general adult readers   # used when not required and not extracted
  why_it_matters: |                # used by the Listener to decide aggressiveness
    Audience determines tone, jargon level, and what assumptions can be left
    unstated. The same content for an exec vs. a child is two different outputs.
```

**Three rules of thumb:**

1. **Bias toward optional with sensible defaults.** Required questions surface as clarification turns and interrupt the flow. Mark a question required only when a wrong default would meaningfully damage the output.
2. **Keep the question count under five.** If you need more, reconsider whether a vertical or a domain split is the better unit.
3. **Write `why_it_matters` honestly.** It's the prompt the Listener uses internally to decide whether to ask. "Audience matters" is too vague; "audience determines tone, jargon, and length tolerance" is actionable.

### 4. Write the prompt template

The template is rendered with `{question_id}` placeholders and the reserved `{original_intent}`, then sent as the user message to the execution model.

Three patterns that work:

- **Lead with structured spec, then verbatim intent.** Lets the model see both what you extracted and what the user said.
- **Be explicit about form.** Don't say "produce a good document" — say "open with one crisp sentence stating the recommendation, then 3–5 supporting points each with concrete evidence, then one explicit next step."
- **End with anti-patterns.** A list of things NOT to do (don't pad, don't summarize your own output, don't tack on a moral) tightens output dramatically.

The schema validates that every `{placeholder}` in the template is either a question id you defined or the reserved `{original_intent}`. If you reference an undefined placeholder, the registry refuses to load.

### 5. Write the system prompt

Short and sharp. The system prompt sets the role and the priorities. Three to six sentences is plenty. Should reflect the universal principles in [`docs/principles.md`](principles.md) — pick the ones most relevant to your domain — plus one or two domain-specific overrides.

```yaml
system_prompt: |
  You are a strategic communicator producing decision-quality one-page documents.
  Be concise. Lead with the answer. Support with evidence. End with action.
  Never pad. If a point isn't strong, cut it rather than soften it.
```

The system prompt is sent as a cacheable content block (`cache_control: ephemeral`), so repeated calls to the same vertical hit the prompt cache. Keep it stable across calls — don't include per-request data here.

### 6. Write the rubric

Rubric criteria are how the Validator (Phase 4) will grade output. Each criterion has an id, name, plain-language description, and a relative weight. Weights are not auto-normalized — the Validator computes the weighted average and divides by sum of weights at compute time.

```yaml
rubric:
  - id: structure
    name: Structure
    description: Document has a one-sentence summary, supporting points, and a clear next step.
    weight: 1.0
  - id: action_clarity
    name: Action clarity
    description: The next step or recommendation is explicit and unambiguous.
    weight: 1.5    # this matters more than structure for decision memos
```

Even though the Validator hasn't shipped, write the rubric thoughtfully. The criteria you choose are also a discipline check on the prompt template — if you can't articulate what "good" looks like for this vertical, the prompt template probably can't produce it either.

### 7. Write the triage triggers

Triage is currently keyword-based and case-insensitive. Add the phrases users actually say.

```yaml
keywords:
  - one-pager
  - executive summary
  - decision memo
  # phrases that genuinely signal this vertical, not generic deliverable words

priority: 0          # higher wins on tiebreaks; reserve high values for narrow verticals
```

**Two rules:**

1. **Prefer phrases over single words.** "memo" is too broad ("memorandum of understanding" is not your vertical). "decision memo" is right.
2. **Don't poach generic words.** "write" and "create" should not be on any vertical's keyword list — they belong to the fallback. Keywords should be the words that distinguish *your* vertical from every other one.

If your vertical isn't keyword-detectable (intent is signaled by structure, not vocabulary), leave keywords empty and rely on `priority` if you also use a hint, or wait for the LLM-based triage upgrade in a later phase.

`examples:` is a list of example user requests that fit your vertical. Currently informational; will become few-shot data for the LLM triage.

### 8. Test it locally

```bash
pytest                                              # all 79 tests pass
python -c "from lucid.verticals._loader import load_registry; print(load_registry().keys())"
python -c "from lucid.verticals._loader import triage; print(triage('your example request here').id)"
```

If your vertical doesn't appear in `load_registry()`, the YAML is malformed — the loader prints the schema error and refuses to load it.

If your vertical doesn't get picked by `triage()` on a representative request, your keywords don't match. Tune them.

To run the full pipeline end-to-end with stubbed models (no API key needed):

```bash
python -c "
from lucid.server import run_lucid
print(run_lucid('your representative request', client=None))
"
```

You'll see either `status: needs_clarification` (Listener wants more info — required questions you defined) or `status: complete` with a stub output that's the rendered prompt. The rendered prompt is the most important thing to inspect — it's what the model will actually see.

### 9. Iterate on the prompt template

Read the rendered prompt. Ask yourself:

- Would a smart writer in this domain want this brief?
- Are there contradictions between sections?
- Is there filler that the model might pad out?
- Are the constraints concrete enough to enforce?

The single biggest source of mediocre Lucid output is a prompt template that says generic things (`be clear`, `be concise`) instead of specific things (`open with one sentence stating the recommendation; supporting points must each cite evidence`).

### 10. Open the PR

```bash
git checkout -b add-recipe-vertical
git add src/lucid/verticals/recipe/
git commit -m "Add recipe vertical with seasonal-pantry and dietary constraints"
git push origin add-recipe-vertical
```

In the PR description, include:

- One paragraph: what the vertical is for and what user requests it serves.
- Two or three sample requests that should triage to this vertical.
- The rendered prompt for one of them (paste it in).
- Anything you tried that didn't work — failed keyword sets, prompt patterns that produced bad output. Negative results help reviewers.

---

## Conventions

**Id namespacing.** Use `<domain>.<subtype>`. Document genres go under `document.*`, code tasks under `code.*`, creative forms under `creative.*`, etc. New top-level domains are fine — that's the architecture's intent.

**File layout.**
```
src/lucid/verticals/<your_vertical>/
├── __init__.py        # empty file; required for Python package discovery
└── config.yaml        # your vertical
```

**Versioning.** Bump `version:` in your YAML when you change `prompt_template`, `system_prompt`, or `questions`. The version surfaces in `lucid_run`'s output so callers can debug regressions.

**No code in verticals.** A vertical is YAML. If your vertical needs Python, the architecture is wrong — open an issue first.

**One fallback maximum.** `is_fallback: true` is reserved for the `general.fluency` vertical. If you have a use case for a second fallback, open an issue — it's a structural decision.

---

## What good looks like

A great vertical, six months from now, looks like this:

- 3–5 questions, all with sharp `why_it_matters` text
- A prompt template that a domain expert reading it for the first time would describe as "yes, that's what I'd want briefed"
- A system prompt that fits in a tweet
- A rubric whose criteria, if all met, would describe excellent output for the domain
- Keywords that match the domain unambiguously without poaching generic deliverable words
- An eval contribution: 5–10 representative prompts in `evals/prompts.yaml` so the harness can measure your vertical against the baseline

If your vertical hits all six, it earns its place in the standard.
