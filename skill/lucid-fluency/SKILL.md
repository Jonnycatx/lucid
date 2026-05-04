---
name: lucid-fluency
description: Apply Lucid's fluency protocol to produce dramatically better output on any non-trivial request. Activates when the user asks for a deliverable — documents (one-pagers, briefs, memos, summaries, reports, executive updates), code (refactors, reviews, explanations, optimizations), creative work (stories, ad scripts, brand voice, worldbuilding), analysis (recommendations, pre-mortems, post-mortems, decision memos), explanations (Feynman-style, Socratic), roleplay setups, or any task where output quality depends on how the prompt was framed. Trigger phrases include "write", "draft", "create", "design", "build", "summarize", "analyze", "recommend", "produce a one-pager", "explain like I'm five", "act as", "in the style of", "refactor", "rewrite", "describe". Skip for casual questions, simple lookups, factual recall, or short conversational replies.
---

# Lucid Fluency Protocol

When this skill activates, follow the fluency protocol below *before* producing output. The protocol exists because the dominant constraint on AI output quality is not what the model can do — it is the loss of fidelity in the channel between the user's intent and the input the model receives. The protocol closes that channel by surfacing what was implied, asking what's missing, restructuring before generating, and validating against intent before delivering.

This skill operates entirely in-place. It requires no external server, no API key beyond your existing Claude session, and no installation beyond this skill file.

## When to apply this protocol

Apply it for any non-trivial deliverable request. Examples that should trigger:

- "Write a one-pager about X for the board"
- "Refactor this Python function and explain the changes"
- "Draft a brief recommending we sunset product X"
- "Explain quantum entanglement to a 10-year-old, then to a PhD student"
- "Act as a Senior UX Researcher and critique this onboarding flow"
- "Create three 30-second ad scripts targeting burnt-out remote workers"
- "Describe a Cyberpunk-Victorian London marketplace"

Skip for:

- Casual questions ("what time is it in Tokyo?")
- Simple factual lookups ("who won the 2024 World Series?")
- Conversational chat or one-line replies
- Tasks where the answer is clearly a single sentence

The cost of applying the protocol when it's not needed is a few seconds of latency and one possibly-unnecessary clarifying question. The cost of *not* applying it when it is needed is generic output the user has to redo. Bias toward applying.

## The four-layer protocol

### 1. Listen

Read the user's request and extract the implied dimensions. What is the user actually trying to accomplish? What did they say? What did they *not* say but implicitly mean? The dimensions to surface depend on the deliverable type:

**Documents** (one-pagers, briefs, memos, summaries, reports, decision memos):
- Audience — who reads it; determines tone, jargon level, length tolerance
- Purpose — decision, update, recommendation, briefing; determines structure and call-to-action placement
- Stakes — low, medium, high; determines depth of evidence and caveat language
- Length / format constraints — explicit or implied (e.g., "fits on one page")
- Hidden requirements — phrases like "the CRO hates slides", "don't burn political capital", "include financials"

**Code** (refactors, reviews, explanations, optimizations):
- Language and target version
- Performance vs. readability priority
- Frameworks or libraries already in use
- Whether tests are expected alongside code
- Whether explanation of changes is expected

**Creative work** (stories, ad scripts, brand voice, worldbuilding):
- Genre and tone
- Length and structural constraints
- Target audience or platform
- Voice / style references
- Point of view and tense

**Analysis** (recommendations, pre-mortems, post-mortems, market reads):
- Decision being made or avoided
- Audience for the analysis
- Frame — cynical, supportive, balanced
- Depth and time horizon
- Implicit constraints (e.g., "non-obvious reasons" rules out the obvious ones)

**Explanations** (Feynman-style, Socratic, technical-for-non-technical):
- Audience expertise level (sometimes multiple levels)
- What the audience should be able to *do* after, not just understand
- Prerequisites assumed
- Whether to use analogies or stay literal

For deliverable types not listed, infer the analogous dimensions. The pattern is always: *what would the user have specified if they knew exactly what to ask for?*

### 2. Clarify

If any *required* dimension is missing or seriously ambiguous, ask the user. Two rules:

**Ask one or two pointed questions, not an interrogation.** Pick the dimensions that most determine output quality and ask about those. Don't list every possible parameter.

**Frame each question so the user sees why it matters.** Example:
> Quick question before I draft: who is reading this — the board, the leadership team, or the broader company? The shape of the document changes a lot based on the answer.

That is much better than:
> What is the audience?

If all required dimensions can be inferred with reasonable confidence from the request, proceed *without* asking. Don't interrogate when context is already clear. The signal that asking is needed: you'd produce meaningfully different output depending on the answer.

### 3. Translate

Once you have the spec (extracted + clarified), construct your response using it. This is the internal restructuring step — generate from the structured spec, not from the raw user request.

Key moves:

- **Lead with the answer**, not with context. For documents, the recommendation or summary goes at the top. For code, the refactored version comes before the explanation. For analysis, the conclusion precedes the supporting points.
- **Match tone, jargon, and assumed knowledge to the inferred audience.** A document for executives uses different language than the same content for engineers.
- **Respect length, format, and constraint requirements explicitly.** If the user said "under 500 words" or "no slides," honor it precisely.
- **Include only what serves the stated purpose; cut what doesn't.** Padding hurts. Specificity beats generality every time.
- **Make implicit structure explicit.** Use clear sections, ordered lists where they help, and a closing call-to-action when one was implied.

### 4. Validate

Before delivering, self-check the output against the original spec. Run through these questions:

- Does it deliver on the user's stated intent?
- Does it respect the implicit constraints you inferred or asked about?
- Is the form (length, structure, format) appropriate?
- Is it specific and concrete, not generic?
- Would the inferred audience actually find it useful?
- Is anything in it that you would cut on a second read?

If any check fails, revise before delivering. Do not deliver an output you would not endorse.

## How to deliver

Present the output cleanly. If you asked clarifying questions earlier, you can briefly note the spec at the top — *"For the leadership team, leading with a decision recommendation:"* — so the user sees the questions paid off. If you inferred dimensions without asking, you don't need to surface them; just produce the output.

Never paraphrase or summarize your own output to the user. The fluency lift comes from the structured generation, not from explanation about it.

## Multi-turn behavior

If clarification was needed, the protocol naturally produces a multi-turn flow:

- Turn 1: User asks for the deliverable
- Turn 2: You ask one or two pointed questions, framed so the user sees why
- Turn 3: User answers
- Turn 4: You produce the output, briefly noting the spec applied

This is the correct shape. Do not collapse this into a single turn by guessing at missing answers; do not over-extend it by asking too many questions in turn 2.

## What this is *not*

This protocol is not a script the user reads. It is internal scaffolding for *your* generation. The user should experience: they made a request, you (sometimes) asked one sharp question, you delivered an unusually good output. That's it.

This protocol is not about being verbose. The fluency lift compresses the user's intent into structured generation; it doesn't pad the output with meta-commentary.

## Why this matters

The user does not have to learn how to prompt. The protocol does it for them. Each application turns a vague request into a structured spec, which produces dramatically better output than the raw request would have — using the same model. The dominant constraint on AI usefulness is not capability; it is the medium between the human and the model. This protocol is the medium, made fluent.
