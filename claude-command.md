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

Send the raw artifact (file contents, code, test output) + a question that
pushes for pushback. The question should make OpenAI challenge the artifact —
surface weaknesses, unstated assumptions, counterarguments, and unhandled edge
cases — not merely catalogue observations. Anti-anchoring still applies: do NOT
reveal your own conclusions or summarize what you think is wrong.

For one file, redirect it to stdin:

```bash
second-opinion --fresh < path/to/file.md
```

For several files plus a question, pipe the question first, then the files
(a file path after `--fresh` is an error):

```bash
printf '%s\n\n' "<question>" | cat - a.py b.py | second-opinion --fresh
```

For assembled context, pipe via stdin:

```bash
cat <<'CONTEXT' | second-opinion --fresh
[raw file contents, code, test output — NOT your analysis]

Question: What weaknesses, unstated assumptions, or counterarguments does this miss? Make the strongest case that it is wrong.
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

Default model is `gpt-5.6-terra` (cheapest strong model on the Plus plan; GPT-6 Astra costs about 5x the allowance). Override with `--model` only if needed; `--reasoning-effort low` is the faster option. Do NOT use `o3` — it's been retired from this workflow.

## Step 2 — Act on the response

Do NOT just print OpenAI's response and stop.

1. **Summarize** what OpenAI said (2-3 sentences max)
2. **Evaluate** — do you agree? Does it contradict what you've tried?
3. **Act** — if the suggestion is actionable and sound, implement it or
   investigate further. If it conflicts with what you know, explain why
   and propose a synthesis.

The goal is to **resolve the blocker**, not relay a message.

## Environment

Runs on the user's ChatGPT subscription through `codex exec` — no `OPENAI_API_KEY`.
One-time setup: `CODEX_HOME=~/.second-opinion/codex-home codex login` (choose
Sign in with ChatGPT). The `second-opinion` CLI is installed globally via
`uv tool install`.

Exit codes: `2` = the codex home is not a ChatGPT sign-in (tell the user to run
the login command above); `3` = HOLD, plan usage limit reached. On exit 3, report
codex's line and the usage URL to the user and stop — there is no fallback, and
never substitute a Claude/Anthropic review. Any other nonzero exit: report the
printed error.
