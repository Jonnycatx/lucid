# Lucid Evaluation Harness

The eval harness measures whether Lucid's pipeline produces better output than a raw prompt to the same execution model. It is the gate that closes Phase 2.

## Method

For each prompt in `prompts.yaml`:

1. **Baseline run.** Send the raw prompt directly to the execution model (Sonnet 4.6 by default).
2. **Lucid run.** Send the prompt through Lucid's pipeline. Same execution model.
3. **Pairwise judge.** A stronger model (Opus 4.6) compares the two outputs blind. To remove position bias, the judge runs twice with positions swapped — only counts as a win if both passes agree. Disagreements are ties.
4. **Aggregate.** Win rate, by domain, by difficulty.

## Eval set

30 prompts spanning eight domains: document creation (15), creative writing, business strategy, tech / programming, lifestyle, education, content creation, roleplay, data analysis. Each prompt is tagged with difficulty and the specific challenge it tests.

The prompts are deliberately diverse because Lucid's thesis is universal fluency, not domain expertise. A win on one domain at the cost of a regression on another is not a real win.

## Run it

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Run a small slice first
python -m evals.harness compare --limit 5

# Run a single domain
python -m evals.harness compare --domain document

# Run the full eval and save results
python -m evals.harness compare --output evals/results/run_$(date +%Y%m%d_%H%M).json
```

## Cost

Each prompt does roughly: 1 baseline call (Sonnet) + 1 Lucid call (Sonnet, plus a Haiku Listener call) + 2 judge calls (Opus). Rough order of magnitude per prompt is a few cents to a few tens of cents depending on output length. Budget accordingly when running the full set.

## Acceptance bar for Phase 2

- Lucid wins more decisive comparisons than baseline does.
- No domain in which Lucid measurably regresses against baseline.
- Win rate persists when re-run on a sampled subset (no overfit to the judge).

If those bars are not hit, we do not tag v0.2. We diagnose what's wrong and iterate.

## What's currently testable

Vertical mode covers the 15 document-domain prompts today. The 15 cross-domain prompts are deliberately left in the eval set as `skipped` markers — they wait for the universal Translator (the architectural pivot articulated in `../docs/plan.md`). Once the universal Translator lands, the same harness re-runs across the full set without changes.
