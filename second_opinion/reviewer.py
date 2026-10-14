"""Core reviewer: runs the review through `codex exec` on a ChatGPT subscription.

No OpenAI SDK and no API key. The child codex runs text-only (no shell tools),
in a fresh empty directory, with its own isolated CODEX_HOME that must hold a
ChatGPT sign-in.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

SYSTEM_PROMPT = """\
You are a senior software engineer providing a second opinion.
You will receive context from another AI assistant — code, errors, analysis, or questions.
Your job is to provide an independent perspective.

If the context includes analysis from another AI, do not simply validate it.
Actively argue the other side: surface its unstated assumptions and the strongest counterargument before you conclude.
Independently verify claims against the provided code and evidence.

Be thorough. Be specific. Reference exact names, values, line numbers, and patterns.
If something is wrong, explain WHY it's wrong and what the correct approach is.
Do not soften your findings. Say what needs to be said."""

FRESH_SYSTEM_PROMPT = """\
You are an independent code reviewer seeing this artifact for the first time.
No prior analysis has been done — you are the first reviewer.

Adopt an adversarial stance: your default assumption is that this artifact is flawed, and your job is to prove it. Build the strongest possible case that it is wrong, incomplete, or unsafe before you concede any part is sound. A clean verdict must be earned with evidence, not granted by default.

Your approach:
1. Read the artifact carefully. Think through it before responding.
2. Enumerate ALL code paths, branches, edge cases, and implicit assumptions.
3. For each one, verify: is it correct? Is it tested? Are edge cases handled?
4. Look for what is MISSING — unhandled cases, uncovered branches, incorrect assumptions.
5. Check for subtle issues: state leakage, ordering dependencies, concurrency, error semantics.

Be thorough. Be specific. Reference exact names, values, line numbers, and patterns.
If something is wrong, explain WHY it's wrong and what the correct approach is.
Do not soften your findings. Say what needs to be said."""


TEXT_ONLY_NOTE = (
    "Text-only review: you have no shell. For a runtime claim, name the command "
    "or test that would prove it and the result you expect."
)

USAGE_URL = "https://chatgpt.com/codex/settings/usage"
LOGIN_HINT = "CODEX_HOME=~/.second-opinion/codex-home codex login"

# Plan-limit wordings, matched against codex's terminal ERROR line only.
_PLAN_LIMIT_MARKERS = ("hit your usage limit", "upgrade to plus")

_ENV_ALLOWLIST = (
    "PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "TMPDIR", "TZ",
    "SSL_CERT_FILE", "SSL_CERT_DIR", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY",
    "https_proxy", "http_proxy", "no_proxy",
)

_EFFORT_MAP = {"minimal": "low"}


class ReviewError(Exception):
    """A failure with the CLI exit code it should produce."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


def codex_home() -> Path:
    return Path.home() / ".second-opinion" / "codex-home"


def _check_auth(home: Path) -> None:
    """Refuse unless auth.json says auth_mode == "chatgpt". Reads only that key."""
    refusal = (
        f"second-opinion: {home} is not a ChatGPT sign-in. Run once:\n"
        f"  {LOGIN_HINT}\n"
        "and choose 'Sign in with ChatGPT' (API-key logins are refused)."
    )
    try:
        with open(home / "auth.json", encoding="utf-8") as f:
            mode = json.load(f).get("auth_mode")
    except (OSError, ValueError, AttributeError):
        raise ReviewError(refusal, 2) from None
    if mode != "chatgpt":
        raise ReviewError(refusal, 2)


def _child_env(home: Path) -> dict[str, str]:
    env = {k: os.environ[k] for k in _ENV_ALLOWLIST if k in os.environ}
    env.update({k: v for k, v in os.environ.items() if k.startswith("LC_")})
    env["CODEX_HOME"] = str(home)
    return env


def _terminal_error(*streams: str) -> str | None:
    """The last line starting with `ERROR:` across codex's output, if any."""
    found = None
    for text in streams:
        for line in text.splitlines():
            if line.strip().startswith("ERROR:"):
                found = line.strip()
    return found


def review(
    context: str,
    model: str = "gpt-5.6-terra",
    fresh: bool = False,
    reasoning_effort: str = "medium",
    timeout: float = 300.0,
) -> str:
    """Review `context` with `codex exec` and return the final message.

    Raises ReviewError (exit 2: not a ChatGPT sign-in; exit 3: plan usage limit,
    hold with no fallback; exit 1: any other failure).
    """
    instructions = FRESH_SYSTEM_PROMPT if fresh else SYSTEM_PROMPT
    prompt = f"{instructions}\n\n{TEXT_ONLY_NOTE}\n\n{context}"
    effort = _EFFORT_MAP.get(reasoning_effort, reasoning_effort)

    home = codex_home()
    _check_auth(home)

    with tempfile.TemporaryDirectory(prefix="second-opinion-") as tmp:
        workdir = Path(tmp).resolve() / "work"
        workdir.mkdir()
        last = Path(tmp).resolve() / "last.md"
        cmd = [
            "codex", "exec", "--ephemeral", "--skip-git-repo-check",
            "-C", str(workdir),
            "-s", "read-only",
            "--disable", "shell_tool", "--disable", "unified_exec",
            "-c", f'model_reasoning_effort="{effort}"',
            "-m", model,
            "-o", str(last),
            "-",
        ]
        try:
            proc = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True,
                timeout=timeout, env=_child_env(home), cwd=workdir, check=False,
            )
        except FileNotFoundError:
            raise ReviewError("second-opinion: `codex` not found on PATH.", 1) from None
        except subprocess.TimeoutExpired:
            raise ReviewError(
                f"second-opinion: request timed out after {timeout:g}s. "
                "Try a longer --timeout or a lower --reasoning-effort for large contexts.",
                1,
            ) from None

        text = last.read_text(encoding="utf-8") if last.exists() else ""

    if proc.returncode == 0 and text.strip():
        return text

    line = _terminal_error(proc.stderr, proc.stdout)
    if line and any(m in line.lower() for m in _PLAN_LIMIT_MARKERS):
        raise ReviewError(
            "HOLD: your ChatGPT plan usage limit is reached. There is no fallback "
            "and no other model will be used.\n"
            f"codex said: {line}\n"
            f"Usage: {USAGE_URL}",
            3,
        )
    if line:
        raise ReviewError(line, 1)
    raise ReviewError(
        f"second-opinion: codex exited {proc.returncode} with no review output.", 1
    )
