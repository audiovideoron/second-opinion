# second-opinion

Get a second opinion from OpenAI when working inside Claude Code.

When you're deep in a session with one AI, it develops blind spots. It anchors to its own analysis and validates rather than challenges. `second-opinion` breaks that loop by sending your code or plans to a different model for independent review — without you having to copy-paste into another chat window.

## Why this exists

We noticed that Claude's built-in `/second-opinion` slash command was producing shallow, generic reviews. The problem wasn't the concept — it was three things:

1. **Anchoring bias** — Claude was sending its own analysis along with the code, which anchored OpenAI to validate rather than independently review
2. **JSON output format** — forcing structured JSON responses suppressed the model's ability to reason deeply
3. **Wrong model** — `gpt-4o` doesn't reason hard enough for code review; `o3` does

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

Requires Python 3.11+ and an OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

## Usage

### Fresh-eyes review (default)

Send raw code or artifacts for independent review. The model sees them cold — no prior analysis, no anchoring.

```bash
# Review a file
second-opinion --fresh src/api/chat.py

# Review from stdin
cat test-plan.md | second-opinion --fresh

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

Default model is `o3` (reasoning). Use `--model` for faster/cheaper questions:

```bash
second-opinion --model gpt-4o "Quick sanity check on this regex"
```

## Claude Code integration

Copy the included slash command to your Claude Code config:

```bash
cp claude-command.md ~/.claude/commands/second-opinion.md
```

Then use `/second-opinion` in any Claude Code session. Claude will:

1. Gather the raw artifact (code, plan, test output) — **not** its own analysis
2. Send it to OpenAI via `--fresh` for independent review
3. Summarize the findings, evaluate them, and act on what's actionable

The anti-anchoring rule is built into the slash command prompt: Claude is instructed to send raw evidence, not its conclusions.

## How it works

Two files, ~80 lines total:

- **`reviewer.py`** — Two system prompts (fresh-eyes and validate) and a `review()` function that calls OpenAI's chat completion API. No JSON format constraint — the model returns natural prose so it can reason freely.
- **`cli.py`** — Parses `--fresh`, `--review`, `--model` flags. Reads from file path or stdin. Prints the response.

That's it. No frameworks, no config files, no dependencies beyond `openai`.

## License

MIT
