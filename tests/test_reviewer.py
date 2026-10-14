"""Tests for the codex-backed reviewer, using a fake `codex` on PATH."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

FAKE_CODEX = """\
#!{python}
import json, os, sys
here = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(here, "config.json")))
cfg.update(cfg.get("homes", {{}}).get(os.path.basename(os.environ.get("CODEX_HOME", "")), {{}}))
argv = sys.argv[1:]
rec = {{"argv": argv, "stdin": sys.stdin.read(), "env": dict(os.environ),
        "cwd": os.getcwd()}}
json.dump(rec, open(os.path.join(here, "record.json"), "w"))
open(os.path.join(here, "calls.txt"), "a").write(os.path.basename(os.environ.get("CODEX_HOME", "")) + "\\n")
if "-o" in argv and cfg.get("last"):
    open(argv[argv.index("-o") + 1], "w").write(cfg["last"])
sys.stdout.write(cfg.get("stdout", ""))
sys.stderr.write(cfg.get("stderr", ""))
sys.exit(cfg.get("rc", 0))
"""


class Rig:
    def __init__(self, tmp: Path):
        self.home = tmp / "home"
        self.bin = tmp / "bin"
        self.bin.mkdir()
        self.codex_home = self.home / ".second-opinion" / "codex-home"
        self.codex_home.mkdir(parents=True)
        script = self.bin / "codex"
        script.write_text(FAKE_CODEX.format(python=sys.executable))
        script.chmod(0o755)
        self.configure(last="REVIEW TEXT\n")
        self.set_auth({"auth_mode": "chatgpt", "tokens": {"secret": "SECRET-TOKEN"}})

    def configure(self, **cfg):
        (self.bin / "config.json").write_text(json.dumps(cfg))

    def set_auth(self, data):
        (self.codex_home / "auth.json").write_text(
            data if isinstance(data, str) else json.dumps(data)
        )

    def set_api_auth(self, data):
        api = self.home / ".second-opinion" / "codex-home-api"
        api.mkdir(parents=True, exist_ok=True)
        (api / "auth.json").write_text(json.dumps(data))

    @property
    def calls(self):
        path = self.bin / "calls.txt"
        return path.read_text().split() if path.exists() else []

    @property
    def record(self):
        path = self.bin / "record.json"
        return json.loads(path.read_text()) if path.exists() else None

    def run(self, *args, stdin="the context", extra_env=None, code=None):
        env = {
            "PATH": f"{self.bin}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(self.home),
            "PYTHONPATH": str(ROOT),
            "OPENAI_API_KEY": "sk-parent-secret",
        }
        env.update(extra_env or {})
        return subprocess.run(
            [sys.executable, "-c", code or "from second_opinion.cli import main; main()", *args],
            input=stdin, capture_output=True, text=True, env=env, check=False,
        )


@pytest.fixture
def rig(tmp_path):
    return Rig(tmp_path)


def test_success_prints_output_file(rig):
    r = rig.run("--fresh")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "REVIEW TEXT"


def test_prompt_arrives_on_stdin(rig):
    rig.run("--fresh", stdin="MY-ARTIFACT-BODY")
    rec = rig.record
    assert "MY-ARTIFACT-BODY" in rec["stdin"]
    assert "independent code reviewer" in rec["stdin"]
    assert "you have no shell" in rec["stdin"]
    assert rec["argv"][-1] == "-"
    assert "MY-ARTIFACT-BODY" not in " ".join(rec["argv"])


def test_argv_is_text_only_and_sandboxed(rig):
    rig.run("--fresh", "--model", "gpt-5.5", "--reasoning-effort", "high")
    argv = rig.record["argv"]
    assert argv[0] == "exec"
    assert "-s" in argv and argv[argv.index("-s") + 1] == "read-only"
    disabled = [argv[i + 1] for i, a in enumerate(argv) if a == "--disable"]
    assert {"shell_tool", "unified_exec"} <= set(disabled)
    assert "--ephemeral" in argv and "--skip-git-repo-check" in argv
    assert argv[argv.index("-m") + 1] == "gpt-5.5"
    assert 'model_reasoning_effort="high"' in argv


def test_minimal_effort_maps_to_low(rig):
    rig.run("--fresh", "--reasoning-effort", "minimal")
    assert 'model_reasoning_effort="low"' in rig.record["argv"]


def test_workdir_is_fresh_empty_resolved_dir(rig):
    rig.run("--fresh")
    rec = rig.record
    cd = rec["argv"][rec["argv"].index("-C") + 1]
    assert cd == os.path.realpath(cd)
    assert cd != str(ROOT)
    assert os.path.realpath(rec["cwd"]) != str(ROOT)


def test_openai_api_key_absent_from_child_env(rig):
    r = rig.run("--fresh", extra_env={"CODEX_API_KEY": "x", "ANTHROPIC_API_KEY": "y"})
    assert r.returncode == 0, r.stderr
    env = rig.record["env"]
    for key in ("OPENAI_API_KEY", "CODEX_API_KEY", "ANTHROPIC_API_KEY"):
        assert key not in env
    assert env["CODEX_HOME"] == str(rig.codex_home)


def test_api_key_auth_refused_before_spawn(rig):
    rig.set_auth({"auth_mode": "apikey", "OPENAI_API_KEY": "sk-LEAK"})
    r = rig.run("--fresh")
    assert r.returncode == 2
    assert rig.record is None
    assert "codex login" in r.stderr
    assert "sk-LEAK" not in r.stdout + r.stderr


@pytest.mark.parametrize("content", ["not json{", "[]", '{"no_mode": 1}', '{"auth_mode": null}'])
def test_garbage_auth_refused(rig, content):
    rig.set_auth(content)
    r = rig.run("--fresh")
    assert r.returncode == 2
    assert rig.record is None


def test_missing_auth_refused(rig):
    (rig.codex_home / "auth.json").unlink()
    r = rig.run("--fresh")
    assert r.returncode == 2
    assert rig.record is None
    assert "CODEX_HOME=~/.second-opinion/codex-home codex login" in r.stderr


def test_auth_contents_never_printed(rig):
    r = rig.run("--fresh")
    assert "SECRET-TOKEN" not in r.stdout + r.stderr


def test_openai_never_imported(rig):
    code = (
        "import sys\n"
        "from second_opinion.cli import main\n"
        "try:\n    main()\nfinally:\n"
        "    sys.stderr.write('OPENAI_IMPORTED=%s' % ('openai' in sys.modules))\n"
    )
    r = rig.run("--fresh", code=code)
    assert "OPENAI_IMPORTED=False" in r.stderr


def test_plan_limit_error_line_holds_with_exit_3(rig):
    line = "ERROR: You've hit your usage limit. Try again at 3:14 PM."
    rig.configure(rc=1, stderr=f"working...\n{line}\n")
    r = rig.run("--fresh")
    assert r.returncode == 3
    assert "HOLD" in r.stderr
    assert line in r.stderr
    assert "https://chatgpt.com/codex/settings/usage" in r.stderr
    assert "no fallback" in r.stderr.lower()
    assert r.stdout == ""


def test_upgrade_to_plus_wording_holds(rig):
    rig.configure(rc=1, stderr="ERROR: Upgrade to Plus to continue using Codex.\n")
    assert rig.run("--fresh").returncode == 3


def test_plan_limit_phrase_in_transcript_is_not_classified(rig):
    rig.configure(
        rc=1,
        stdout="the user said: you've hit your usage limit, upgrade to Plus\n",
        stderr="model note: hit your usage limit\nERROR: stream disconnected\n",
    )
    r = rig.run("--fresh")
    assert r.returncode == 1
    assert "HOLD" not in r.stderr
    assert "ERROR: stream disconnected" in r.stderr


def test_other_codex_error_prints_line_exit_1(rig):
    rig.configure(rc=1, stderr="ERROR: model not supported\n")
    r = rig.run("--fresh")
    assert r.returncode == 1
    assert "ERROR: model not supported" in r.stderr


def test_extra_positional_after_fresh_is_error_naming_stdin_form(rig):
    for flag in ("--fresh", "--review"):
        r = rig.run(flag, "file.md")
        assert r.returncode == 1
        assert "cat - <files>" in r.stderr and flag in r.stderr
        assert rig.record is None


API_SPENT = "ERROR: Quota exceeded. Check your plan and billing details.\n"


def test_no_api_home_uses_plan_only(rig):
    r = rig.run("--fresh")
    assert r.returncode == 0, r.stderr
    assert rig.calls == ["codex-home"]


def test_api_home_used_first(rig):
    rig.set_api_auth({"auth_mode": "apikey"})
    rig.configure(homes={"codex-home-api": {"last": "API REVIEW\n"}})
    r = rig.run("--fresh")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "API REVIEW"
    assert rig.calls == ["codex-home-api"]
    assert "account=api" in r.stderr


def test_api_balance_spent_falls_back_to_plan(rig):
    rig.set_api_auth({"auth_mode": "apikey"})
    rig.configure(
        last="PLAN REVIEW\n",
        homes={"codex-home-api": {"last": "", "stderr": API_SPENT, "rc": 1}},
    )
    r = rig.run("--fresh")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "PLAN REVIEW"
    assert rig.calls == ["codex-home-api", "codex-home"]
    assert "API balance spent" in r.stderr


def test_api_spent_then_plan_limit_holds(rig):
    rig.set_api_auth({"auth_mode": "apikey"})
    rig.configure(
        last="",
        stderr="ERROR: You've hit your usage limit. Try again at 11:18 PM.\n",
        rc=1,
        homes={"codex-home-api": {"stderr": API_SPENT}},
    )
    r = rig.run("--fresh")
    assert r.returncode == 3
    assert rig.calls == ["codex-home-api", "codex-home"]


def test_other_api_error_does_not_fall_back(rig):
    rig.set_api_auth({"auth_mode": "apikey"})
    rig.configure(homes={"codex-home-api": {"last": "", "stderr": "ERROR: boom\n", "rc": 1}})
    r = rig.run("--fresh")
    assert r.returncode == 1
    assert "ERROR: boom" in r.stderr
    assert rig.calls == ["codex-home-api"]


def test_api_home_without_apikey_mode_is_ignored(rig):
    rig.set_api_auth({"auth_mode": "chatgpt"})
    r = rig.run("--fresh")
    assert r.returncode == 0, r.stderr
    assert rig.calls == ["codex-home"]
