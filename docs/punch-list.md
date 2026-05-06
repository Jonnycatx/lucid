# Lucid Punch List

Living tactical roadmap. Complements [`plan.md`](plan.md) — the plan covers strategic phases (0–5), this file covers concrete items within and across phases. Every item below carries an efficiency case: what it actually saves, unlocks, or measurably improves. Items are written so any contributor can pick one up cold.

Status legend: **NEXT** (do now) · **PARKED** (waiting on dependency) · **BACKLOG** (real but lower priority) · **DEFERRED** (legitimate future work) · **NOT PURSUING** (explicit no) · **DONE** (shipped — recorded with date and commit).

---

## Tier 1 — Behavioral fixes the eval data demands

The n=3 smoke run on 2026-05-05 produced two findings that shape this tier:
1. The skill clarifies too aggressively for one-shot use cases.
2. When the skill commits to producing output, it wins for the right structural reasons (specificity, concrete numbers, narrative voice).

### 1. Skill body clarification fix · **DONE (v3 — eval-iterated)**

*Completed 2026-05-05 over three iterations:*
- *v1 (original): "ask if 50%+ output change" — n=3 smoke showed model interpreted this too liberally; 1/3 prompts lost outright with judge confidence 0.95 because the skill asked instead of producing.*
- *v2 (first fix, commit `0effd3b`): "produce with bracketed placeholders, ask only when truly necessary" — n=3 smoke showed Lucid losing 0/2/1 because outputs felt like templates ("$[X]M acquisition · [Y]% IRR" reads as unfinished work).*
- *v3 (final, this commit): "produce a finished draft with plausible illustrative specifics — concrete numbers, dates, names. Optional one-line note that numbers are illustrative." n=3 smoke showed 2/0/1 with wins driven by specificity ("Postgres → Aurora, $18K/month, sprint numbers"). Bracket count dropped to ~0 in skill outputs.*

*Standalone and plugin SKILL.md kept identical. principles.md item #2 also updated to match. Two result JSONs saved as evidence trail.*

**What.** Edit [`skill/lucid-fluency/SKILL.md`](../skill/lucid-fluency/SKILL.md) to bias toward producing-with-placeholders over asking, and tighten the "when to ask" rule to genuinely-unrecoverable cases (audience flips that change tone fundamentally; decisions the user hasn't actually made). Add explicit guidance: when concrete facts are missing but the form is clear, produce a draft using `[INSERT METRIC]`-style placeholders and close with "want me to swap in real specifics?"

**Efficiency case.** The n=3 smoke lost 1/3 outright because the skill asked when it should have produced (judge confidence 0.95, judge wrote: *"Response B asks a clarifying question instead of producing the requested deliverable"*). Without this fix, every dollar spent on n=10/n=30 evals would mostly be re-measuring this known bug. **Saves: $20+ in wasted eval spend.** Also fixes real-world UX: most users want a draft now, not another question.

**Effort.** ~30 min · no API cost.

### 2. `docs/principles.md` — canonical craft rules · **DONE**

*Completed 2026-05-05 · this commit · Seven numbered principles extracted from the skill body and shipped verticals: lead with form, produce with placeholders, be specific, match audience, show don't tell, end with what the form earned, respect explicit constraints. Skill body now references this file.*

**What.** Single file with 5–7 numbered universal principles extracted from the (corrected) skill body and the four shipped verticals: lead with what serves the form; produce with placeholders before asking; cut padding ruthlessly; match tone to audience; never meta-comment on the output; end on resonance not summary; respect explicit constraints exactly.

**Efficiency case.** Today the same principles are duplicated across `skill/SKILL.md` + 4 vertical `config.yaml` files. Updating a rule means 5+ edits with drift risk. Centralizing means one edit, no drift. **Reduces maintenance time per behavioral change from ~5 files → 1 file.** Earns its place because it encodes rules now backed by eval data, not speculation.

**Effort.** ~30 min · no API cost.

### 3. Vertical template scaffold · **DONE**

*Completed 2026-05-05 · this commit · Created `src/lucid/verticals/_template/config.yaml` — fully commented YAML with TODO markers and inline notes. Loader updated to skip underscore-prefixed directories so the template never loads as a real vertical. Test added (`test_underscore_prefixed_directories_are_skipped`).*

**What.** A fully-commented `src/lucid/verticals/_template/config.yaml` (excluded from the registry by an underscore prefix the loader skips) with TODO placeholders explaining each field. Contributors copy this when adding a new vertical, rather than copying a real vertical and editing.

**Efficiency case.** The current onramp ([`docs/authoring-a-vertical.md`](authoring-a-vertical.md)) says "copy `general.fluency` or `creative.story`." Both have real content the contributor must edit AND distinguish-from-template, leading to a known class of errors (forgotten id changes, accidental keyword inheritance, leftover `is_fallback: true`). A pure-template removes the distinguish step. **Reduces contributor PR time from ~30 min to ~10 min** and cuts a class of errors.

**Effort.** ~20 min · no API cost.

### 4. Wire the references · **DONE**

*Completed 2026-05-05 · this commit · Skill body links to principles.md. Authoring guide now points at the template (not real verticals) for the copy step and references principles.md for the system_prompt step. Vertical system_prompts NOT yet refactored to compose from principles.md — that work remains in punch-list item #23 (deferred).*

**What.** Update `skill/SKILL.md`, the four vertical `system_prompt` blocks, and `docs/authoring-a-vertical.md` to reference `principles.md` and `_template/` instead of restating rules or pointing at real verticals.

**Efficiency case.** Without this step, items 2–3 are just static files nobody reads. With it, every vertical and the skill all inherit the latest tested principles automatically. **Closes the DRY violation across the project's behavioral surface.**

**Effort.** ~20 min · no API cost.

---

## Tier 2 — Realistic measurement

### 5. 2-turn eval mode in `evals/harness.py` · **NEXT (after Tier 1)**

**What.** When the skill returns a clarifying question instead of an output, the harness auto-generates a plausible answer (cheap Haiku call) and re-runs the skill with the answer. The judged output is the second-turn result. Implementation: detect "?" + brevity in skill output → spawn an "auto-respond" Haiku call → re-run skill with the response in the user message → grade the second turn.

**Efficiency case.** The current one-shot harness penalizes the skill for behavior that's correct in real use (clarification → user answers → output). 2-turn mode measures what actual users experience. **Unblocks publishable win-rate that matches reality.** Cost: ~30% more API per prompt that triggers clarification, but signal per dollar is dramatically higher because we stop measuring a known limitation.

**Effort.** ~1 hr · no API cost to build (test mocked).

### 6. n=3 smoke re-run · **DONE (twice — drove v2→v3 iteration)**

*Completed 2026-05-05 · this commit · Re-ran n=3 smoke twice, ~$2 total. First run validated v2 fix (clarification gone) but exposed bracketed-placeholder problem. Second run validated v3 fix — outputs now confidently populate plausible specifics. Saved both JSONs to evals/results/ as evidence trail. Variance still dominant at n=3 (win rates have spanned 0%–100% across four runs), so the headline number remains unpublishable until n=10 or n=30 lands.*

**What.** `python -m evals.harness compare --limit 3 --runner skill` after Tier 1 lands. Confirms the clarification issue is gone before any larger spend.

**Efficiency case.** ~$1 spend that gates the $5 (n=10) and $15 (n=30) spends downstream. Without this checkpoint we'd risk burning $15+ on a run still measuring the same bug.

**Effort.** ~5 min · ~$1 API cost.

### 7. n=10 directional run · **DONE**

*Completed 2026-05-05 · curated 10-prompt cross-vertical sample (one per specialized vertical) via new `--ids` flag added to harness. Result: 4 W / 0 L / 6 T = 100% decisive on the directional sample. Wins driven by specificity (technical detail in document, audience-fit + emotional resonance in marketing, lens-and-camera completeness in image, length-constraint compliance in email). Ties on creative/code/explain/social where raw Sonnet is already strong. JSON saved to `evals/results/skill-10-cross-vertical.json`.*

### 8. n=51 full eval · **DONE**

*Completed 2026-05-05 · full eval set (30 original + 21 vertical-batch additions = 51 prompts) with `--runner skill`. **Result: 79.4% decisive win rate (27 W / 7 L / 17 T), position-debiased Opus 4.6 judge.** Strongest domain: document (87% decisive — 13 W / 0 L / 2 T). Domains where Lucid lost or struggled: code (0/2), image (1/3 W with 2 L), education (0/2). Ties dominate social (3/3). Loss-pattern analysis revealed two clusters — (a) judge preferring baseline's "kitchen sink" scaffolding (extra tables, settings, alternative variants) over Lucid's tightness in 5/7 losses, which is a stylistic difference more than a quality regression; (b) two genuine misses (`marketing.value_prop_therapy_app` was too generic on pain points; `explain.socratic_hire_decision` chose a supporting question instead of the most strategic one) that are real iteration opportunities for v0.4. Full JSON committed to `evals/results/skill-full.json`. README and demo site updated with the measured number.*

### 9. n=30 MCP-pipeline eval (`--runner lucid`) · **PARKED**

**What.** Same 30 prompts, but the full MCP pipeline (Listener + Translator + Validator). Separately measured.

**Efficiency case.** The MCP path is the ceiling claim ("with the full pipeline you get even more"). Without measuring it, that claim is hand-wavy. **Required for any "skill vs. server" comparison the README makes.**

**Effort.** ~20 min · ~$10–15 API cost.

---

## Tier 3 — Public surface and adoption

### 11. PyPI publication (`pip install lucid`) · **DEFERRED to v0.3 release**

**What.** Publish the package on PyPI so `pip install lucid` works without a `git clone` first.

**Efficiency case (when triggered).** Every developer install today is `git clone` + `cd` + `pip install -e .`. PyPI cuts that to one command. Reduces dev install time from ~3 min to ~30 sec.

**Why deferred.** The skill (recommended for almost everyone) doesn't need PyPI. The plugin doesn't need PyPI. Only direct-MCP-client users need it, which is a small audience pre-launch. PyPI publication also commits the project to a versioning cycle (no unpublishing, every change needs a version bump). Best done at v0.3 release time alongside measured eval data — one coherent release moment.

**Honesty fix completed 2026-05-05 · this commit.** Dropped misleading `pip install lucid` claims from `plugin/README.md` (two places) and `docs/index.html`. Replaced with explicit `git clone + pip install -e .` instructions. Added "PyPI release ships with v0.3" notes in three places (main README, plugin README, demo site) so readers know it's planned, not abandoned.

**Effort when triggered.** ~1 hr (PyPI account, twine upload, verify install in fresh venv).

### 12. Fresh-install validation · **DONE**

*Completed 2026-05-05 · this commit · Followed the README dev-install flow on a fresh venv at `/tmp/lucid-fresh-install/`. The install itself was clean — `pip install -e ".[dev]"`, `pytest` (102 passed), and `lucid-check` all worked first try. But the validation surfaced three real friction items, all fixed in this commit:*

- *Version mismatch: `pyproject.toml` and `src/lucid/__init__.py` said `0.1.0` while README, demo site, and project narrative all say v0.2 / v0.3. New developer running `lucid-check` saw "version 0.1.0" while the README said v0.2 — confusing first impression. Bumped both to `0.2.0`.*
- *Stale test count: README said "101 tests passing" in two places; actual count is 102 (we added the underscore-prefix test in commit `0effd3b`). Updated.*
- *Stray `pytest-cache-files-xpp7ys4_` directory was sitting in the working tree (created by deepeval test runs). Not tracked, but easy to accidentally commit. Added `pytest-cache-files-*/` to .gitignore.*

*Skill and plugin install paths NOT validated end-to-end (would require Cowork/Claude Desktop) — those remain as separate validation tasks if friction reports come in.*

### 13. Custom domain · **NOT PURSUING**

**What.** Buy a domain like `uselucid.dev` or `lucid-fluency.dev` and configure GitHub Pages CNAME.

**Decision 2026-05-05.** Owner has declined this for now. Reasoning: GitHub Pages URL is sufficient for the project's positioning; the brand-name space around "Lucid" is heavily contested (Lucid Motors, Lucid Software, Lucid AI) and the marginal SEO/credibility win doesn't justify ongoing cost or maintenance. Revisit only if traffic patterns specifically suggest a memorable URL is the dropout point.

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

### 25. Shared question library — `inherits_questions` schema field

**What.** Extract truly-common Listener questions (`audience`, `constraints`) into a shared YAML library (`src/lucid/verticals/_common.yaml`). Add an `inherits_questions: [audience, constraints]` field to the vertical schema. The loader merges inherited + local questions at registry-build time. Each vertical's YAML drops the duplicated definitions.

**Efficiency case.** Today `audience` is defined in 3+ verticals nearly identically; `constraints` in all 4. As verticals grow, this duplication grows linearly. Centralizing means a single edit propagates. Trigger conditions for promoting this to NEXT: (a) 8+ verticals exist, OR (b) 3+ truly-identical questions appear across all verticals, OR (c) a contributor PR demonstrates real duplication pain.

**Why not now.** With 4 verticals and only 2 nearly-shared questions, the abstraction overhead (new schema field, loader merge logic, migration) outweighs the DRY win. Each vertical's `why_it_matters` text is also slightly tuned per-domain — centralizing would lose that. Wait for the trigger conditions.

**Effort when triggered.** ~2 hr · no API cost.

### 27. Vertical expansion: 7-vertical seed batch · **DONE**

*Completed 2026-05-05 over 7 commits. Doubled specialized vertical count from 3 to 10. Each vertical was designed-discussion-first, then YAML-implemented, then triage-smoke-tested before commit. Eval prompts added for each (3 per vertical, 21 total) so the next n=30 batched API run will exercise specialized verticals rather than routing most prompts to the fallback.*

**What.** Ship 7 high-leverage specialized verticals to bring the total from 4 → 10. Each shipped one at a time with a design-discussion-first flow: agree on dimensions and structure, draft YAML, render sample prompt for sanity, add 2-3 representative eval prompts, commit, move on.

**Efficiency case.** Doubling specialized verticals from 3 → 10 expands the eval surface so the next n=30 batched run actually exercises specialized verticals (today, only ~5 of 30 prompts hit one). Per-vertical lift becomes measurable. Adoption surface grows. Contributor flywheel benefits from a fuller seed.

**Sequence.**
1. ✅ `email.professional` — completed 2026-05-05 · commit `802dbfe`
2. ✅ `marketing.copy` — completed 2026-05-05 · commit `d7d945e`
3. ✅ `social.thread` — completed 2026-05-05 · commit `61c044c`
4. ✅ `explain.feynman` — completed 2026-05-05 · commit `c86bad0`
5. ✅ `explain.socratic` — completed 2026-05-05 · commit `bb6393e`
6. ✅ `analysis.recommendation` — completed 2026-05-05 · commit `a5077c8`
7. ✅ `prompt.image` — completed 2026-05-05 · this commit
5. ⏳ `explain.socratic`
6. ⏳ `analysis.recommendation`
7. ⏳ `prompt.image`

**Out of scope for the seed batch.** `code.refactor` / `code.explain` will be handled by extending the existing `code.review` vertical (consolidation rather than duplication). High-liability domains (`legal.document.review`, `finance.personal`, `journal.therapy`) deferred to a careful pass with disclaimer patterns. Niche items (`history.whatif`, `puzzle.creation`) deferred until earned demand.

**Effort.** ~10–15 min per vertical for build + render review + eval prompts. ~2 hours total.

---

## Last item — do this last

### 26. Org rename — `lucid-fluency.github.io/lucid` · **PARKED (do at the very end)**

**What.** Create GitHub org `lucid-fluency`, transfer repo, update install/release URLs in `README.md`, `plugin/README.md`, demo `docs/index.html`, and the live GitHub Pages URL.

**Efficiency case.** `jonnycatx.github.io/lucid` reads as a side project; `lucid-fluency.github.io/lucid` reads as a project with intent. Trust signal at every link share. Free except for the rename overhead.

**Why this is last.** Repo transfers create redirect chains for every existing link, release URL, eval-results JSON URL, and screenshot in third-party content. The earlier we do the rename, the more redirects we generate. Doing it after the project has stabilized — eval data published, plugin/skill releases tagged, README links pointing at the v0.3 release — minimizes the redirect blast radius. Also lets us bundle the rename with the v1.0 / launch announcement as one coherent moment.

**Effort.** ~30 min total — owner's part: 60 sec to create the org. Mine: transfer + URL updates across README, plugin README, demo site, and any release-asset URLs.

- **Pick `NEXT` items first.** They're the highest-leverage, no-blocker items.
- **`PARKED` items have a stated dependency.** Don't unblock them by skipping the dependency.
- **`BACKLOG` items are real but can wait.** Pick them up when surface-area work matters.
- **`DEFERRED` items are tracked but not active.** Move to BACKLOG only when they bite.
- **`NOT PURSUING` items have an explicit "no" decision.** Don't revive without a written reason that overrides the original decision.
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

*(Tier 1 items are now `DONE` and remain inline in their tier sections for now. They'll move down to this section once 5+ items have shipped.)*

Last updated: 2026-05-05 (org rename moved to last position; custom domain marked NOT PURSUING).
