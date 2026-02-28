"""Core reviewer — sends context to OpenAI and returns structured findings."""

from openai import OpenAI

SYSTEM_PROMPT = """\
You are a senior software engineer providing a second opinion.
You will receive context from another AI assistant — code, errors, analysis, or questions.
Your job is to provide an independent perspective.

If the context includes analysis from another AI, do not simply validate it.
Independently verify claims against the provided code and evidence.

Be thorough. Be specific. Reference exact names, values, line numbers, and patterns.
If something is wrong, explain WHY it's wrong and what the correct approach is.
Do not soften your findings. Say what needs to be said."""

FRESH_SYSTEM_PROMPT = """\
You are an independent code reviewer seeing this artifact for the first time.
No prior analysis has been done — you are the first reviewer.

Your approach:
1. Read the artifact carefully. Think through it before responding.
2. Enumerate ALL code paths, branches, edge cases, and implicit assumptions.
3. For each one, verify: is it correct? Is it tested? Are edge cases handled?
4. Look for what is MISSING — unhandled cases, uncovered branches, incorrect assumptions.
5. Check for subtle issues: state leakage, ordering dependencies, concurrency, error semantics.

Be thorough. Be specific. Reference exact names, values, line numbers, and patterns.
If something is wrong, explain WHY it's wrong and what the correct approach is.
Do not soften your findings. Say what needs to be said."""


def review(context: str, model: str = "gpt-4o", fresh: bool = False) -> str:
    """Send context to OpenAI for review. Single completion, no tools."""

    prompt = FRESH_SYSTEM_PROMPT if fresh else SYSTEM_PROMPT

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": context},
        ],
    )
    return response.choices[0].message.content or ""
