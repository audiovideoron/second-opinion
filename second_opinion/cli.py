"""CLI entry point for second-opinion.

Usage:
  Review mode (pipe context via stdin):
    echo '<context>...</context>' | second-opinion --review

  Prompt mode (simple question):
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

    # Review mode: structured context in, structured findings out
    if args and args[0] == "--review":
        source = args[1] if len(args) > 1 else "-"

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

        print(review(context, model=model))

    else:
        # Simple prompt mode — same as review but wraps the prompt
        prompt = " ".join(args)
        print(review(prompt, model=model))


if __name__ == "__main__":
    main()
