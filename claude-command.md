# /second-opinion — Get a fresh perspective from OpenAI

When the user invokes this command, they are stuck on a problem and want a
second opinion from OpenAI. Your job is to **package the context, call the
bridge, and act on the response** — all in one step, no manual relay.

## Inputs

`$ARGUMENTS` contains the user's description of what they're stuck on.
It may be empty — if so, infer from recent conversation context.

## Step 1 — Gather context

Build a concise context package. Include **only what's relevant** to the problem:

- The specific question or blocker (from `$ARGUMENTS` or conversation)
- Relevant code snippets (files you've been editing or reading)
- Error messages or unexpected behavior
- What has already been tried and why it didn't work

Keep total context under 4000 tokens. Be ruthless — OpenAI needs signal, not noise.

## Step 2 — Call the tool

Pipe the context to the globally installed `second-opinion` CLI:

```bash
cat <<'CONTEXT' | second-opinion --review
<context>
[your gathered context here]
</context>

<question>
[the specific question you want answered]
</question>
CONTEXT
```

The `--review` flag sends context directly to OpenAI as a single completion —
no tools, no loop. Fast.

You can override the model with `--model gpt-4o-mini` for quick/cheap questions.

## Step 3 — Act on the response

Do NOT just print OpenAI's response and stop.

1. **Summarize** what OpenAI said (2-3 sentences max)
2. **Evaluate** — do you agree? Does it contradict what you've tried?
3. **Act** — if the suggestion is actionable and sound, implement it or
   investigate further. If it conflicts with what you know, explain why
   and propose a synthesis.

The goal is to **resolve the blocker**, not relay a message.

## Environment

Requires `OPENAI_API_KEY` set in your shell environment.
The `second-opinion` CLI is installed globally via `uv tool install`.
