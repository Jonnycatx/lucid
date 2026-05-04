---
name: lucid-fluency
description: Use Lucid's fluency layer to produce dramatically better output for any non-trivial request. Activates whenever the user asks for a deliverable — documents (one-pagers, briefs, memos, summaries, reports, executive updates), code (refactors, reviews, explanations, optimizations), creative work (stories, ad scripts, brand voice, worldbuilding), analysis (recommendations, pre-mortems, post-mortems, decision memos), explanations (Feynman-style, Socratic), roleplay setups, or any task where output quality depends on how the prompt was framed. Trigger phrases include "write", "draft", "create", "design", "build", "summarize", "analyze", "recommend", "produce a one-pager", "explain like I'm five", "act as", "in the style of", "refactor", "rewrite", "describe". Skip for casual questions, simple lookups, factual recall, or short conversational replies.
---

# Lucid Fluency

You have access to the `lucid` MCP server, which exposes a `lucid_run` tool. Lucid is the fluency layer between human intent and AI output — it listens for true intent (including unspoken constraints), translates that intent into the optimal prompt for the target model, and returns the result.

## When to invoke Lucid

Invoke Lucid for any non-trivial deliverable request. Examples that should trigger Lucid:

- "Write a one-pager about Q3 priorities for the board"
- "Refactor this Python function and explain the changes"
- "Draft a brief recommending we sunset product X"
- "Explain quantum entanglement to a 10-year-old, then to a PhD student"
- "Act as a Senior UX Researcher and critique this onboarding flow"
- "Create three 30-second ad scripts targeting burnt-out remote workers"
- "Describe a Cyberpunk-Victorian London marketplace"
- "Recommend three Black Swan events that could disrupt urban gardening by 2030"

Skip Lucid for:

- Casual questions ("what time is it in Tokyo?")
- Simple factual lookups ("who won the 2024 World Series?")
- Conversational chat or one-liner replies
- Tasks where the answer is clearly a single sentence

## How to invoke Lucid

Call the `lucid_run` tool from the `lucid` MCP server with the user's full request as the `intent` parameter:

```
lucid_run(intent="<the user's full request, verbatim>")
```

Process the response according to its `status` field:

**`status: "complete"`** — Lucid produced an output. Present the `result` field to the user as the answer. Do not paraphrase or shorten. Lucid already optimized the output for the user's intent.

**`status: "needs_clarification"`** — Lucid needs more information before it can produce a high-quality output. The `questions_to_ask` field contains the questions. Surface those questions to the user one at a time (or batched if natural), get their answers, then call `lucid_run` again with the answers in the `answers` parameter:

```
lucid_run(intent="<original intent>", answers={"audience": "...", "purpose": "..."})
```

**`status: "no_match"`** — The request did not match any known Lucid vertical. Fall through to a normal response without Lucid. Do not surface the no_match status to the user.

**`status: "unknown_hint"` or other errors** — Treat as `no_match`. Fall through to a normal response.

## What not to do

- Do not paraphrase Lucid's output. Present `result` verbatim.
- Do not invoke Lucid for casual questions or simple lookups — the latency isn't worth it.
- Do not surface internal Lucid statuses ("status: complete", "vertical: document.one_pager") to the user. The user sees the answer, not the plumbing.
- Do not skip the clarification step. If Lucid asks for clarification, ask the user — that's the whole point of the fluency loop.

## Why this matters

Lucid is the difference between a vague prompt that produces generic output and a structured prompt that produces production-quality output. Users do not have to learn how to prompt — Lucid does it for them. Every time you invoke Lucid on a deliverable request, the user gets output that is measurably better than what the same model would produce from the raw prompt alone.
