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

  Model override:
    second-opinion --model gpt-4o-mini "Quick question about X"
"""

import sys

from .reviewer import review


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
            "  second-opinion --model gpt-4o-mini ...      # override model\n",
            file=sys.stderr,
        )
        sys.exit(0 if args else 1)

    # Parse --model flag
    model = "gpt-4o"
    if "--model" in args:
        idx = args.index("--model")
        if idx + 1 < len(args):
            model = args[idx + 1]
            args = args[:idx] + args[idx + 2 :]
        else:
            print("Error: --model requires a value", file=sys.stderr)
            sys.exit(1)

    # Check for mutually exclusive --fresh and --review
    has_fresh = "--fresh" in args
    has_review = "--review" in args

    if has_fresh and has_review:
        print("Error: --fresh and --review are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    # Fresh mode: independent review, no prior analysis
    if has_fresh:
        args.remove("--fresh")
        source = args[0] if args else "-"

        context = _read_context(source)
        print(review(context, model=model, fresh=True))

    # Review mode: structured context in, structured findings out
    elif has_review:
        args.remove("--review")
        source = args[0] if args else "-"

        context = _read_context(source)
        print(review(context, model=model, fresh=False))

    else:
        # Simple prompt mode — same as review but wraps the prompt
        prompt = " ".join(args)
        print(review(prompt, model=model))


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
