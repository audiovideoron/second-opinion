# second-opinion

Get a second opinion from OpenAI inside Claude Code.

A tiny CLI tool that pipes context to OpenAI and returns structured findings — designed to be called from a Claude Code slash command when you're stuck and want a fresh perspective from a different LLM.

## Install

```bash
uv tool install second-opinion
```

Or from source:

```bash
git clone https://github.com/audiovideoron/second-opinion.git
uv tool install ./second-opinion
```

## Setup

1. Set your OpenAI API key:

```bash
export OPENAI_API_KEY="sk-..."
```

2. Add the Claude Code slash command (one-time, user-level):

Copy `claude-command.md` to `~/.claude/commands/second-opinion.md`

## Usage

### From the CLI

```bash
# Simple question
second-opinion "Is this the right approach for chunking PDFs?"

# Review mode — pipe structured context
cat <<'EOF' | second-opinion --review
<context>
def chunk(text):
    return text.split("\n\n")
</context>

<question>
Is this chunking strategy good enough for RAG, or should I use heading-aware splitting?
</question>
EOF

# Use a different model
second-opinion --model gpt-4o-mini "Quick sanity check on X"
```

### From Claude Code

Just type `/second-opinion <what you're stuck on>` in any project. Claude will gather context, call the tool, and act on OpenAI's response.

## How it works

1. Claude packages the problem context (code, errors, what's been tried)
2. Pipes it to `second-opinion --review`
3. OpenAI returns structured JSON findings with issue, evidence, confidence, and suggestion
4. Claude evaluates the response and either implements the suggestion or explains why it disagrees

## Output format

```json
{
  "findings": [
    {
      "issue": "Naive splitting loses heading context",
      "evidence": "text.split('\\n\\n') discards section hierarchy",
      "confidence": "high",
      "suggestion": "Use heading-aware chunking that preserves parent headings as context"
    }
  ]
}
```

## License

MIT
