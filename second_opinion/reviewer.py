"""Core reviewer — sends context to OpenAI and returns structured findings."""

from openai import OpenAI

SYSTEM_PROMPT = """\
You are a senior software engineer providing a second opinion.
You will receive context from another AI assistant — code, errors, analysis, or questions.
Your job is to provide an independent perspective.

RESPONSE FORMAT — strict, no exceptions:
Return ONLY a JSON object with a single key "findings" containing an array.
Each element must have exactly these fields:

  issue              — what is wrong or what you'd do differently (one sentence)
  evidence           — specific code, values, or details that support your point
  confidence         — "low", "medium", or "high"
  suggestion         — concrete action to resolve it (file/function if possible)

Rules:
- Do NOT include any text outside the JSON object.
- Do NOT wrap the JSON in markdown code fences.
- If you have no findings, return: {"findings": []}
- Be specific: reference exact names, values, and patterns from the context.
- Keep each field concise — one or two sentences max."""


def review(context: str, model: str = "gpt-4o") -> str:
    """Send context to OpenAI for review. Single completion, no tools."""

    client = OpenAI()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": context},
        ],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""
