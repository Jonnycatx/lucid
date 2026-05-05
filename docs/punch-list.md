# Lucid Punch List

Living tactical roadmap. Complements [`plan.md`](plan.md) — the plan covers strategic phases (0–5), this file covers concrete items within and across phases. Every item below carries an efficiency case: what it actually saves, unlocks, or measurably improves. Items are written so any contributor can pick one up cold.

Status legend: **NEXT** (do now) · **PARKED** (waiting on dependency) · **BACKLOG** (real but lower priority) · **DEFERRED** (legitimate future work) · **DONE** (shipped — recorded with date and commit).

---

## Tier 1 — Behavioral fixes the eval data demands

The n=3 smoke run on 2026-05-05 produced two findings that shape this tier:
1. The skill clarifies too aggressively for one-shot use cases.
2. When the skill commits to producing output, it wins for the right structural reasons (specificity, concrete numbers, narrative voice).

### 1. Skill body clarification fix · **NEXT**

**What.** Edit [`skill/lucid-fluency/SKILL.md`](../skill/lucid-fluency/SKILL.md) to bias toward producing-with-placeholders over asking, and tighten the "when to ask" rule to genuinely-unrecoverable cases (audience flips that change tone fundamentally; decisions the user hasn't actually made). Add explicit guidance: when concrete facts are missing but the form is clear, produce a draft using `[INSERT METRIC]`-style placeholders and close with "want me to swap in real specifics?"

**Efficiency case.** The n=3 smoke lost 1/3 outright because the skill asked when it should have produced (judge confidence 0.95, judge wrote: *"Response B asks a clarifying question instead of producing the requested deliverable"*). Without this fix, every dollar spent on n=10/n=30 evals would mostly be re-measuring this known bug. **Saves: $20+ in wasted eval spend.** Also fixes real-world UX: most users want a draft now, not another question.

**Effort.** ~30 min · no API cost.

### 2. `docs/principles.md` — canonical craft rules · **NEXT**

**What.** Single file with 5–7 numbered universal principles extracted from the (corrected) skill body and the four shipped verticals: lead with what serves the form; produce with placeholders before asking; cut padding ruthlessly; match tone to audience; never meta-comment on the output; end on resonance not summary; respect explicit constraints exactly.

**Efficiency case.** Today the same principles are duplicated across `skill/SKILL.md` + 4 vertical `config.yaml` files. Updating a rule means 5+ edits with drift risk. Centralizing means one edit, no drift. **Reduces maintenance time per behavioral change from ~5 files → 1 file.** Earns its place because it encodes rules now backed by eval data, not speculation.

**Effort.** ~30 min · no API cost.

### 3. Vertical template scaffold · **NEXT**

**What.** A fully-commented `src/lucid/verticals/_template/config.yaml` (excluded from the registry by an underscore prefix the loader skips) with TODO placeholders explaining each field. Contributors copy this when adding a new vertical, rather than copying a real vertical and editing.

**Efficiency case.** The current onramp ([`docs/authoring-a-vertical.md`](authoring-a-vertical.md)) says "copy `general.fluency` or `creative.story`." Both have real content the contributor must edit AND distinguish-from-template, leading to a known class of errors (forgotten id changes, accidental keyword inheritance, leftover `is_fallback: true`). A pure-template removes the distinguish step. **Reduces contributor PR time from ~30 min to ~10 min** and cuts a class of errors.

**Effort.** ~20 min · no API cost.

### 4. Wire the references · **NEXT**

**What.** Update `skill/SKILL.md`, the four vertical `system_prompt` blocks, and `docs/authoring-a-vertical.md` to reference `principles.md` and `_template/` instead of restating rules or pointing at real verticals.

**Efficiency case.** Without this step, items 2–3 are just static files nobody reads. With it, every vertical and the skill all inherit the latest tested principles automatically. **Closes the DRY violation across the project's behavioral surface.**

**Effort.** ~20 min · no API cost.

---

## Tier 2 — Realistic measurement

### 5. 2-turn eval mode in `evals/harness.py` · **NEXT (after Tier 1)**

**What.** When the skill returns a clarifying question instead of an output, the harness auto-generates a plausible answer (cheap Haiku call) and re-runs the skill with the answer. The judged output is the second-turn result. Implementation: detect "?" + brevity in skill output → spawn an "auto-respond" Haiku call → re-run skill with the response in the user message → grade the second turn.

**Efficiency case.** The current one-shot harness penalizes the skill for behavior that's correct in real use (clarification → user answers → output). 2-turn mode measures what actual users experience. **Unblocks publishable win-rate that matches reality.** Cost: ~30% more API per prompt that triggers clarification, but signal per dollar is dramatically higher because we stop measuring a known limitation.

**Effort.** ~1 hr · no API cost to build (test mocked).

### 6. n=3 smoke re-run · **PARKED (after Tier 1)**

**What.** `python -m evals.harness compare --limit 3 --runner skill` after Tier 1 lands. Confirms the clarification issue is gone before any larger spend.

**Efficiency case.** ~$1 spend that gates the $5 (n=10) and $15 (n=30) spends downstream. Without this checkpoint we'd risk burning $15+ on a run still measuring the same bug.

**Effort.** ~5 min · ~$1 API cost.

### 7. n=10 directional run · **PARKED**

**What.** `--limit 10`, mixed across domains (document, creative, code, lifestyle, education).

**Efficiency case.** Real signal at n=10 — variance becomes interpretable. Reveals whether the skill wins broadly or only on documents. **Decides whether to invest in n=30 or back up and improve further.**

**Effort.** ~10 min · ~$5 API cost.

### 8. n=30 full eval · **PARKED**

**What.** Full 30-prompt eval with `--runner skill`. Saved JSON committed to `evals/results/`.

**Efficiency case.** This is the artifact that converts "Lucid is theoretically better" → "Lucid is X% better, position-debiased Opus judge, here's the JSON." **Unlocks: demo site headline number, README win-rate claim, the credibility signal needed for adoption.**

**Effort.** ~20 min · ~$10–15 API cost.

### 9. n=30 MCP-pipeline eval (`--runner lucid`) · **PARKED**

**What.** Same 30 prompts, but the full MCP pipeline (Listener + Translator + Validator). Separately measured.

**Efficiency case.** The MCP path is the ceiling claim ("with the full pipeline you get even more"). Without measuring it, that claim is hand-wavy. **Required for any "skill vs. server" comparison the README makes.**

**Effort.** ~20 min · ~$10–15 API cost.

---

## Tier 3 — Public surface and adoption

### 10. Org rename — `lucid-fluency.github.io/lucid` · **PARKED (your action)**

**What.** Create GitHub org `lucid-fluency`, transfer repo, update install/release URLs in `README.md`, `plugin/README.md`, and the demo `docs/index.html`.

**Efficiency case.** `jonnycatx.github.io/lucid` reads as a side project; `lucid-fluency.github.io/lucid` reads as a project with intent. **Trust signal at every link share.** Free.

**Effort.** ~30 min total — your part: 60 sec to create org. My part: transfer + URL updates.

### 11. PyPI publication (`pip install lucid`) · **BACKLOG**

**What.** Publish the package on PyPI so the README's `pip install lucid` line actually works (currently requires `git clone` first).

**Efficiency case.** Every developer install today is `git clone` + `cd` + `pip install -e`. PyPI cuts that to one command. **Reduces dev install time from ~3 min to ~30 sec** and removes a known dropout point. Critical once we want to attract third-party MCP-client developers.

**Effort.** ~1 hr · no API cost.

### 12. Fresh-install validation · **BACKLOG**

**What.** On a fresh machine or fresh venv, follow the README install flow exactly — skill download, plugin install, dev install. Document and fix any friction.

**Efficiency case.** We've never validated the documented install path. Friction here = silent dropouts we never observe. **Catches missing dependencies, broken steps, or ambiguous instructions before users hit them.**

**Effort.** ~30 min · no API cost.

### 13. Custom domain · **BACKLOG**

**What.** Buy a domain like `uselucid.dev` or `lucid-fluency.dev`, configure GitHub Pages CNAME.

**Efficiency case.** Memorable URL aids word-of-mouth and conference mentions. **Optional polish, not foundational.** Worth the ~$15/yr only after the project earns visibility.

**Effort.** ~30 min · ~$15/yr.

### 14. Live API demo on the site · **BACKLOG**

**What.** Replace the pre-baked outputs in `docs/index.html` with a real "Try It" button: user types a prompt → backend (Cloudflare Worker / Vercel function) calls Lucid → shows raw vs. Lucid side-by-side.

**Efficiency case.** Pre-baked examples are convincing but not conclusive. A live demo where visitors paste their own prompts is the strongest possible "see it works" moment. **Increases conversion from visit → install dramatically.** Risks: API key management, rate limiting, abuse vector.

**Effort.** ~4–6 hr · ongoing API cost (per demo invocation).

---

## Tier 4 — Architectural depth

### 15. LLM-based triage · **PARKED (after Tier 1 + Tier 2 prove value)**

**What.** Replace the substring keyword-matching `triage()` with a Haiku classification call (~$0.0005/request).

**Efficiency case.** Current triage misses on phrasing it doesn't have keywords for ("draft me an executive summary about X" hits; "give me something I can hand the CEO" doesn't). LLM classifier captures intent regardless of phrasing. **Improves vertical hit rate without requiring users to know trigger words.** Risks: adds ~200ms latency and ~$0.0005 to every request — measurable cost trade-off.

**Effort.** ~2 hr · adds runtime API cost.

### 16. Memory layer (Phase 5) · **DEFERRED**

**What.** Per-user persistent storage of preferences, voice, recurring constraints. Encrypted, exportable, auditable.

**Efficiency case.** Today every Lucid request starts cold — the user re-states their preferences each time. Memory means accumulated context fills the gaps automatically. **Long-term: the difference between Lucid as a useful tool and Lucid as the "ambient infrastructure" the thesis describes.** Significant build; comes after the eval gate is consistently green.

**Effort.** 2–3 days · adds ongoing storage cost.

### 17. CI eval gate · **PARKED (after publishable baseline)**

**What.** GitHub Actions workflow that runs an n=3 (or larger) eval on every PR. PRs that drop win-rate below a threshold get auto-flagged.

**Efficiency case.** Today nothing prevents a contributor's vertical or skill change from regressing quality. Eval gate makes regression impossible to merge silently. **Reduces quality drift over time as the project grows.** Requires: stable baseline number to compare against (see #8).

**Effort.** ~1 hr · ~$1 per PR in API cost.

### 18. Cost / latency telemetry · **BACKLOG**

**What.** `run_lucid()` returns timing and token counts in the response: `{"timing": {"listener_ms": ..., "translator_ms": ..., "validator_ms": ...}, "tokens": {"input": ..., "output": ..., "cache_hits": ...}}`.

**Efficiency case.** Currently we have no per-call observability. Hard to verify prompt caching is working, identify the bottleneck, or report cost-per-request truthfully. **Unlocks measurable optimization** — today we'd be optimizing blind.

**Effort.** ~1 hr · no API cost.

### 19. Per-vertical eval breakdown · **PARKED (after #8)**

**What.** Once #8 lands, parse `evals/results/skill-30.json` and produce a per-vertical breakdown: `creative.story 75%, code.review 60%, document.one_pager 70%, general.fluency 40%`. Publish to README and demo site.

**Efficiency case.** Per-domain numbers reveal which verticals earn their place and where the fallback is doing the heavy lifting. **Drives data-grounded decisions on which new verticals to build next** (the gaps where general.fluency underperforms).

**Effort.** ~30 min · no API cost.

---

## Parking lot — DEFERRED

These are real but lower-priority. Listed so they're not lost.

### 20. Skill `description` tightening
The skill's auto-trigger description in YAML frontmatter is currently a paragraph. Probably fine, but should be tested against negative examples (casual questions that shouldn't trigger). Address only if eval data shows over-triggering.

### 21. `CHANGELOG.md`
Standard hygiene. Add at first proper release (v0.3+).

### 22. Lucid in-session status indicator
Some way to show "Lucid fired" mid-session. Constrained by what host clients (Cowork, Claude Desktop) display. Defer until users report this as real friction.

### 23. Shared-principles refactor for verticals (post-#2)
Once `principles.md` exists, vertical `system_prompt` blocks should compose from shared principles + domain-specific layer. Today they restate. Architectural cleanup; doesn't change behavior. Defer until the principles file has been live and tested.

### 24. Validator: live grading on a real prompt
The Validator (Phase 4) is built but only smoke-tested. Run it on real eval prompts to confirm it produces sensible scores and the re-roll budget improves outputs.

---

## How to use this list

- **Pick `NEXT` items first.** They're the highest-leverage, no-blocker items.
- **`PARKED` items have a stated dependency.** Don't unblock them by skipping the dependency.
- **`BACKLOG` items are real but can wait.** Pick them up when surface-area work matters.
- **`DEFERRED` items are tracked but not active.** Move to BACKLOG only when they bite.
- **Every item should have a concrete efficiency case.** If a new item lacks one, the item is probably speculation.

## Keeping this list current

The list is only useful if it stays current. Discipline:

1. **When an item ships**, change its status from `NEXT`/`PARKED`/etc. to `DONE` and add a one-line entry under it: `Completed YYYY-MM-DD · [commit-sha](https://github.com/Jonnycatx/lucid/commit/<sha>) · brief note on what changed`.
2. **Once 5+ DONE items accumulate**, move them en masse to the `## Shipped` section at the bottom (newest first). Keeps the active list scannable.
3. **When a new item is identified**, add it to the appropriate tier with full structure (What / Efficiency case / Effort) and a starting status. Don't just append a one-liner — items without an efficiency case get culled.
4. **When a `PARKED` item's dependency clears**, promote it to `NEXT`.
5. **Update the "Last updated" date** at the bottom each time the list changes.
6. **Commit punch-list updates with the work they describe**, not as standalone commits — e.g. the commit that ships item #1 should also flip its status to DONE.

## Shipped

*(nothing yet — Tier 1 items are still NEXT. As items complete, move them here from above with their completion line.)*

Last updated: 2026-05-05.
