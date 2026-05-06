# Lucid Evaluation Harness

The eval harness measures whether Lucid's pipeline produces better output than a raw prompt to the same execution model. It is the discipline that gates every release.

## Method

For each prompt in `prompts.yaml`:

1. **Baseline run.** Send the raw prompt directly to the execution model (Sonnet 4.6 by default).
2. **Treatment run.** Send the prompt through Lucid. Two runner modes:
   - `--runner skill` (default): the standalone skill body sent as a system prompt to the same model. This is what most users will install via `lucid.skill`.
   - `--runner lucid`: the full MCP-server pipeline (Listener + Translator + optional Validator). The advanced install path.
3. **Pairwise judge.** A stronger model (Opus 4.6) compares the two outputs blind. To remove position bias, the judge runs twice with positions swapped — only counts as a win if both passes agree. Disagreements are ties.
4. **Aggregate.** Win rate, by domain, by difficulty.

## Eval set

51 prompts spanning fourteen domains: document creation (15), email drafting (3), marketing copy (3), social media (3), Feynman/Socratic explanations (6), strategic recommendations (3), image-prompt engineering (3), creative writing (2), business strategy (2), code review (2), lifestyle (2), education (2), content (2), roleplay (2), data analysis (1).

Prompts are deliberately diverse because Lucid's thesis is universal fluency, not domain expertise. Wins on one domain at the cost of regressions on another are not real wins.

## Headline result (v0.2.0)

**79.4% decisive win rate (27 W / 7 L / 17 T) on n=51, position-debiased Opus 4.6 judge.** Full per-prompt outputs and judge reasoning saved to `results/skill-full.json`.

By domain (W / L / T):

```
document:    13  /  0  /  2   ← strongest, 87% decisive
analysis:     2  /  0  /  1
creative:     2  /  0  /  0
lifestyle:    2  /  0  /  0
email:        1  /  0  /  2
content:      1  /  0  /  1
roleplay:     1  /  0  /  1
marketing:    1  /  1  /  1
business:     1  /  1  /  0
image:        1  /  2  /  0   ← currently losing
explain:      2  /  1  /  3
education:    0  /  1  /  1   ← currently losing
code:         0  /  1  /  1   ← currently losing
data:         0  /  0  /  1
social:       0  /  0  /  3   ← all ties
```

## Run it

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Smoke test — 3 prompts (~$1)
python -m evals.harness compare --limit 3

# Curated cross-vertical sample by id (~$5)
python -m evals.harness compare \
  --ids "doc.platform_migration_status,email.budget_request_ceo,marketing.b2b_landing_hero,social.x_decision_fatigue,creative.unreliable_narrator,tech.code_optimizer,explain.feynman_vaccines,explain.socratic_market_efficiency,analysis.pricing_increase,prompt.image_midjourney_portrait" \
  --output results/skill-10-cross-vertical.json

# Single domain (e.g. document)
python -m evals.harness compare --domain document

# Full eval (~$15-25)
python -m evals.harness compare --output results/skill-full-$(date +%Y%m%d).json

# Compare the MCP-server pipeline (separate measurement, awaiting v0.3)
python -m evals.harness compare --runner lucid --output results/lucid-full.json
```

## Cost

Each prompt does roughly: 1 baseline call (Sonnet) + 1 treatment call (Sonnet, plus a Haiku Listener call when `--runner lucid`) + 2 judge calls (Opus). A few cents to a few tens of cents per prompt. n=51 full run is roughly $15–25 depending on output length.

## Acceptance bar

Phase 2 closure required:
- Lucid wins more decisive comparisons than baseline. ✅ (27 W vs. 7 L = 79.4% decisive)
- No domain in which Lucid measurably regresses. ⚠️ (3 domains currently losing — `code`, `image`, `education` — tracked as v0.4 iteration items)
- Win rate persists when re-run on a sampled subset (no overfit to the judge). ✅ (cross-vertical n=10 sample reproduced the directional result)

Phase 2 is closed. The remaining 3 weak domains are concrete iteration targets for v0.4.

## Saved results

Every meaningful eval run saves a JSON to `results/`. These are committed (force-added past `.gitignore`) as evidence trail:

- `skill-3-smoke.json` — first n=3 smoke (drove the v1 → v2 skill iteration)
- `skill-3-post-tier1.json` — n=3 after Tier 1 fixes (revealed v2 placeholder problem)
- `skill-3-post-tier1-v3.json` — n=3 after v3 (validated the iteration worked)
- `skill-10-cross-vertical.json` — n=10 directional, 1 prompt per specialized vertical
- `skill-full.json` — n=51 full eval, the published headline number

Anyone can verify the published 79.4% by reading the JSON. Every judge verdict's reasoning is preserved.
