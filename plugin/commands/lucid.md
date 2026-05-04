---
description: Run the Lucid fluency layer on a request explicitly. Use for power-user invocation; the lucid-fluency skill handles automatic invocation.
---

The user has invoked `/lucid` with the following request:

$ARGUMENTS

Call the `lucid_run` tool from the `lucid` MCP server with the request as the `intent` parameter:

```
lucid_run(intent="$ARGUMENTS")
```

Process the response by `status`:

- **`complete`** — Present the `result` field verbatim. Do not paraphrase, shorten, or summarize.
- **`needs_clarification`** — Surface the questions in `questions_to_ask` to the user. Wait for their answers, then call `lucid_run` again with the answers in the `answers` parameter.
- **`no_match`** — Tell the user Lucid did not have a known vertical for this request and fall through to a normal response.
- **`unknown_hint`** or other errors — Treat as `no_match`.

Do not surface raw Lucid metadata (status fields, vertical ids, model names) to the user unless they ask.
