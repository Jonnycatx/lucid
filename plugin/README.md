# Lucid Plugin for Cowork

> The fluency layer between human intent and AI output, packaged as a one-click Cowork plugin.

## What this plugin does

Lucid is the layer between you and the AI model. Instead of you having to learn how to prompt, Lucid:

- **Listens** for your true intent — including things you didn't explicitly say
- **Asks clarifying questions** when it needs more information to produce great output
- **Translates** your intent into the prompt shape the model performs best on
- **Returns** dramatically better output than a raw prompt to the same model would produce

This plugin packages the [Lucid MCP server](https://github.com/Jonnycatx/lucid) so you can install it with one click in Cowork instead of installing Python packages and editing config files.

## What's inside

- **`lucid` MCP server** — the Lucid fluency pipeline, bundled.
- **`lucid-fluency` skill** — auto-triggers whenever you ask for a deliverable (a document, code, creative work, analysis, anything where output quality depends on how the request was framed).
- **`/lucid` slash command** — explicit invocation for power users.

## Prerequisites

Lucid runs as a local Python MCP server. You need:

- Python 3.10 or later installed on your machine
- The `lucid` Python package installed from source (PyPI release ships with v0.3):
  ```bash
  git clone https://github.com/Jonnycatx/lucid.git
  cd lucid
  pip install -e .
  ```
- An Anthropic API key

A future version of this plugin will bundle the Python dependencies automatically; for now, the install is two steps.

## Installation

1. Install the Lucid Python package from source:
   ```bash
   git clone https://github.com/Jonnycatx/lucid.git
   cd lucid
   pip install -e .
   ```

2. Install this plugin from the Cowork plugin manager.

3. Set your Anthropic API key as an environment variable. The plugin reads `ANTHROPIC_API_KEY`:
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-...
   ```

4. Restart Cowork. Lucid is now active.

## Using Lucid

You don't have to do anything. The `lucid-fluency` skill auto-triggers when you ask for a deliverable.

```
You: "Write a one-pager about our Q3 priorities for the leadership team."
Lucid: (asks clarifying questions if needed, then produces the document)
```

Or invoke explicitly:

```
You: "/lucid recommend whether we should sunset product X for the board"
```

## How it differs from plain Claude

Without Lucid, when you ask Claude to "write a one-pager," Claude makes assumptions about audience, tone, length, structure, and stakes — and you get a generic document.

With Lucid, the system asks the questions you didn't think to specify, then constructs the prompt that produces the document you actually wanted. Same model. Different output quality.

## Source

This plugin is open source: [github.com/Jonnycatx/lucid](https://github.com/Jonnycatx/lucid). The MCP server, the schema, the pipeline — every line is auditable. This plugin is a thin packaging layer that delivers the same code through Cowork's marketplace.

## Privacy and trust

Lucid processes your request locally (on your machine, via the local Python server) and calls the Anthropic API on your behalf using your own API key. Your data does not pass through any third-party server. The plugin is MIT-licensed and open source — you can read every line of code that mediates your prompts.

## License

[MIT](https://github.com/Jonnycatx/lucid/blob/main/LICENSE) — same as the underlying Lucid project.
