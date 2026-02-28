# /second-opinion — Get a fresh perspective from OpenAI

When the user invokes this command, they are stuck on a problem and want a
second opinion from OpenAI. Your job is to **package the context, call the
bridge, and act on the response** — all in one step, no manual relay.

## Inputs

`$ARGUMENTS` contains the user's description of what they're stuck on.
It may be empty — if so, infer from recent conversation context.

## Step 1 — Gather context

**Anti-anchoring rule:** Do NOT include your own findings, analysis, or
conclusions in the context you send. Send the **raw artifact** — file contents,
code, error output — and a neutral question. Let OpenAI form its own opinion
from the evidence. Including your analysis causes OpenAI to validate rather
than independently review.

There are two modes:

### Fresh-eyes mode (default — use `--fresh`)

Send the raw artifact (file contents, code, test output) + a neutral question.
The question should ask OpenAI to independently identify issues, missing code
paths, or edge cases. Do NOT summarize what you think is wrong.

```bash
cat <<'CONTEXT' | second-opinion --fresh
<artifact>
[raw file contents, code, test output — NOT your analysis]
</artifact>

<question>
[neutral question: "What issues, missing code paths, or edge cases do you see?"]
</question>
CONTEXT
```

### Validate mode (only when user explicitly asks — use `--review`)

Only use this when the user says "validate my review", "check my analysis",
or similar. This is the only time you include your own findings.

```bash
cat <<'CONTEXT' | second-opinion --review
<context>
[your analysis + the supporting code/evidence]
</context>

<question>
[the specific question you want validated]
</question>
CONTEXT
```

Keep total context under 4000 tokens in either mode. Be ruthless — OpenAI
needs signal, not noise.

You can override the model with `--model gpt-4o-mini` for quick/cheap questions.

## Step 2 — Act on the response

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
