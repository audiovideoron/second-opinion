# second-opinion

Get a second opinion from OpenAI when working inside Claude Code, billed to your ChatGPT subscription (no API key).

When you're deep in a session with one AI, it develops blind spots. It anchors to its own analysis and validates rather than challenges. `second-opinion` breaks that loop by sending your code or plans to a different model for independent review — without you having to copy-paste into another chat window.

## Why this exists

We noticed that Claude's built-in `/second-opinion` slash command was producing shallow, generic reviews. The problem wasn't the concept — it was three things:

1. **Anchoring bias** — Claude was sending its own analysis along with the code, which anchored OpenAI to validate rather than independently review
2. **JSON output format** — forcing structured JSON responses suppressed the model's ability to reason deeply
3. **Wrong model** — `gpt-4o` doesn't reason hard enough for code review; a reasoning model does (default: `gpt-5.6-terra`)

After fixing all three, the same test plan that got zero findings now produced a 9-point review catching event loop mismatches, incorrect patch targets, and missing code paths.

## Install

```bash
uv tool install second-opinion
```

Or from source:

```bash
git clone https://github.com/audiovideoron/second-opinion.git
uv tool install ./second-opinion
```

Requires Python 3.11+ and the [Codex CLI](https://github.com/openai/codex) (`codex`) on your PATH.

### One-time sign-in

Reviews run through `codex exec` on your ChatGPT plan, in their own isolated Codex home. Sign in once:

```bash
CODEX_HOME=~/.second-opinion/codex-home codex login
```

Choose **Sign in with ChatGPT**. No `OPENAI_API_KEY` is used or passed to the child process; an API-key login in that home is refused. The review runs text-only: the Codex child has no shell, a read-only sandbox, and an empty scratch directory.

## Usage

### Fresh-eyes review (default)

Send raw code or artifacts for independent review. The model sees them cold — no prior analysis, no anchoring.

```bash
# Review one file (stdin)
second-opinion --fresh < src/api/chat.py

# Review several files with a question: question first, then the files
printf '%s\n\n' "What breaks here?" | cat - a.py b.py | second-opinion --fresh

# Ask a question
second-opinion "Is this the right approach for chunking PDFs?"
```

### Validate mode

When you explicitly want to check your own analysis, use `--review`. This is the only mode where including your conclusions makes sense.

```bash
cat <<'EOF' | second-opinion --review
Here's my analysis of the auth module: [your findings]

The code: [relevant source]

Question: Did I miss anything?
EOF
```

### Model override

Default model is `gpt-5.6-terra` (about one-fifth the plan allowance of the Codex default, GPT-6 Astra). Use `--model` to pick another model your plan offers, `--reasoning-effort minimal|low|medium|high` (minimal maps to low), and `--timeout SECONDS` (default 300):

```bash
second-opinion --reasoning-effort low "Quick sanity check on this regex"
```

## Claude Code integration

Copy the included slash command to your Claude Code config:

```bash
cp claude-command.md ~/.claude/commands/second-opinion.md
```

Then use `/second-opinion` in any Claude Code session. Claude will:

1. Gather the raw artifact (code, plan, test output) — **not** its own analysis
2. Send it to OpenAI via `--fresh` (stdin) for independent review
3. Summarize the findings, evaluate them, and act on what's actionable

The anti-anchoring rule is built into the slash command prompt: Claude is instructed to send raw evidence, not its conclusions.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Review printed |
| 1 | Usage error, timeout, or any other codex error (codex's `ERROR:` line is printed) |
| 2 | `~/.second-opinion/codex-home` is not a ChatGPT sign-in (missing, unreadable, or API-key login); nothing was spawned |
| 3 | HOLD: ChatGPT plan usage limit reached. Prints codex's line and https://chatgpt.com/codex/settings/usage. There is no fallback and no other model is used |

## How it works

- **`reviewer.py`** — Two system prompts (fresh-eyes and validate) and a `review()` function that pipes the prompt to `codex exec` on stdin (ephemeral, read-only sandbox, shell tools disabled, fresh empty working directory, allowlisted environment) and returns the final message.
- **`cli.py`** — Parses `--fresh`, `--review`, `--model`, `--reasoning-effort`, `--timeout`. `--fresh` and `--review` read stdin only; a positional argument after them is an error.

No Python dependencies.

## License

MIT
