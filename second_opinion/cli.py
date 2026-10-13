"""CLI entry point for second-opinion.

Usage:
  Fresh-eyes mode (independent review, no prior analysis):
    echo '<artifact>...</artifact>' | second-opinion --fresh
    second-opinion --fresh artifact.md

  Review mode (validate existing analysis):
    echo '<context>...</context>' | second-opinion --review
    second-opinion --review context.txt

  Simple prompt:
    second-opinion "Is this approach correct for chunking PDFs?"

  Model / reasoning / timeout overrides:
    second-opinion --model gpt-4o "Quick question about X"
    second-opinion --reasoning-effort high --fresh artifact.md
    second-opinion --timeout 600 --fresh big_artifact.md
"""

import sys

from openai import APITimeoutError, OpenAIError

from .reviewer import review

_VALID_EFFORTS = {"minimal", "low", "medium", "high"}


def _pop_value_flag(args: list[str], name: str) -> tuple[str | None, list[str]]:
    """Extract `--name <value>` from args.

    Returns (value_or_None, remaining_args). Exits with an error if the flag is
    present without a following value.
    """
    if name not in args:
        return None, args
    idx = args.index(name)
    if idx + 1 >= len(args):
        print(f"Error: {name} requires a value", file=sys.stderr)
        sys.exit(1)
    return args[idx + 1], args[:idx] + args[idx + 2 :]


def main() -> None:
    args = sys.argv[1:]

    if not args or args == ["--help"]:
        print(
            "Usage:\n"
            '  second-opinion "your question"              # simple prompt\n'
            "  second-opinion --fresh                      # fresh-eyes review from stdin\n"
            "  second-opinion --fresh artifact.md          # fresh-eyes review from file\n"
            "  second-opinion --review                     # review context from stdin\n"
            "  second-opinion --review context.txt         # review context from file\n"
            "  second-opinion --model gpt-4o ...           # override model (default: gpt-5.5)\n"
            "  second-opinion --reasoning-effort high ...  # minimal|low|medium|high (default: medium)\n"
            "  second-opinion --timeout 600 ...            # request timeout in seconds (default: 300)\n",
            file=sys.stderr,
        )
        sys.exit(0 if args else 1)

    # Value-taking flags — extract before positional/source handling.
    model, args = _pop_value_flag(args, "--model")
    model = model or "gpt-5.5"

    effort, args = _pop_value_flag(args, "--reasoning-effort")
    reasoning_effort = effort or "medium"
    if reasoning_effort not in _VALID_EFFORTS:
        print(
            f"Error: --reasoning-effort must be one of {sorted(_VALID_EFFORTS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    timeout_raw, args = _pop_value_flag(args, "--timeout")
    timeout = 300.0
    if timeout_raw is not None:
        try:
            timeout = float(timeout_raw)
        except ValueError:
            print("Error: --timeout requires a number (seconds)", file=sys.stderr)
            sys.exit(1)
        if timeout <= 0:
            print("Error: --timeout must be positive", file=sys.stderr)
            sys.exit(1)

    # Mutually exclusive --fresh / --review
    has_fresh = "--fresh" in args
    has_review = "--review" in args
    if has_fresh and has_review:
        print("Error: --fresh and --review are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    if has_fresh:
        args.remove("--fresh")
        context = _read_context(args[0] if args else "-")
        fresh = True
    elif has_review:
        args.remove("--review")
        context = _read_context(args[0] if args else "-")
        fresh = False
    else:
        # Simple prompt mode — the remaining args ARE the prompt.
        context = " ".join(args)
        if not context.strip():
            print("Error: empty context", file=sys.stderr)
            sys.exit(1)
        fresh = False

    try:
        print(
            review(
                context,
                model=model,
                fresh=fresh,
                reasoning_effort=reasoning_effort,
                timeout=timeout,
            )
        )
    except APITimeoutError:
        print(
            f"second-opinion: request timed out after {timeout:g}s. "
            "Try a longer --timeout or a lower --reasoning-effort for large contexts.",
            file=sys.stderr,
        )
        sys.exit(1)
    except OpenAIError as exc:
        print(f"second-opinion: OpenAI API error: {exc}", file=sys.stderr)
        sys.exit(1)


def _read_context(source: str) -> str:
    """Read context from stdin or a file path."""
    if source == "-":
        context = sys.stdin.read()
    else:
        try:
            with open(source, encoding="utf-8") as f:
                context = f.read()
        except FileNotFoundError:
            print(f"Error: file not found: {source}", file=sys.stderr)
            sys.exit(1)

    if not context.strip():
        print("Error: empty context", file=sys.stderr)
        sys.exit(1)

    return context


if __name__ == "__main__":
    main()
