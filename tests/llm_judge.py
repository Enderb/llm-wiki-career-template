"""LLM-as-judge: list every CV claim that cannot be traced to a source file.

Backends (picked automatically in this order unless CV_JUDGE_BACKEND is set):

  anthropic  Anthropic Python SDK. Needs ANTHROPIC_API_KEY (or ANTHROPIC_AUTH_TOKEN).
  claude     The Claude Code CLI (`claude -p`), using your Claude Code login.
  opencode   The opencode CLI (`opencode run`), using whatever provider/model you
             configured in opencode (works with free and local models too).

Every backend gets the same prompt and must answer with the same JSON, so the
verdict is comparable whichever one ran. Results are cached in .cache/cv-judge/
keyed on (prompt, backend, model) so unchanged CVs are not re-billed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

from cvcheck import VAULT, load_config

PROMPT_VERSION = "1"
CACHE_DIR = os.path.join(VAULT, ".cache", "cv-judge")

SCHEMA = {
    "type": "object",
    "properties": {
        "unsupported_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "cv_excerpt": {"type": "string"},
                    "reason": {"type": "string"},
                },
                "required": ["claim", "cv_excerpt", "reason"],
                "additionalProperties": False,
            },
        },
        "claims_checked": {"type": "integer"},
    },
    "required": ["unsupported_claims", "claims_checked"],
    "additionalProperties": False,
}

INSTRUCTIONS = """You are a strict fact-checker for a job applicant's tailored CV.

You are given SOURCE FILES (the only ground truth) and a GENERATED CV. Go through
the CV claim by claim and decide whether each factual claim can be traced back to
the source files.

What counts as a factual claim:
- employers, job titles, teams, dates, locations, degrees, schools, grades, awards
- every number or metric (team sizes, percentages, multipliers, volumes, durations)
- achievements, responsibilities, projects and outcomes
- technologies, languages, tools and skills listed or implied as experience

Rules:
- A claim is SUPPORTED if a source states it, or it is a faithful paraphrase,
  summary or reasonable combination of statements in the sources.
- A claim is UNSUPPORTED if no source states it, if it inflates or changes a fact
  (a bigger number, a more senior title, a different date, a stronger outcome, a
  responsibility nobody mentions), or if it adds a technology/skill that no
  source mentions.
- Generic self-descriptions with no checkable fact ("ramps up fast",
  "user-centric") are not claims; skip them.
- Do not use outside knowledge. Do not give the benefit of the doubt.

Answer with ONLY a JSON object, no prose and no code fences, in exactly this shape:
{"unsupported_claims": [{"claim": "<the claim in a few words>",
  "cv_excerpt": "<exact words from the CV>", "reason": "<why no source supports it>"}],
 "claims_checked": <number of factual claims you checked>}
Use an empty list when every claim is supported."""


@dataclass
class Verdict:
    backend: str
    model: str
    unsupported: list[dict] = field(default_factory=list)
    claims_checked: int = 0
    cached: bool = False


class JudgeUnavailable(Exception):
    """No backend could be used; the check is skipped (never silently passed)."""


class JudgeError(Exception):
    """A backend ran but its answer could not be used."""


def build_prompt(cv_text: str, sources: dict[str, str]) -> str:
    parts = [INSTRUCTIONS, "\n\n=== SOURCE FILES ==="]
    for name, text in sources.items():
        parts.append(f"\n--- SOURCE: {name} ---\n{text.strip()}\n")
    parts.append("\n=== GENERATED CV ===\n" + cv_text.strip())
    parts.append("\n=== END ===\nReturn only the JSON object now.")
    return "\n".join(parts)


# ------------------------------------------------------------------ backends
def _has_anthropic() -> bool:
    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def pick_backend(conf: dict) -> str:
    wanted = (os.environ.get("CV_JUDGE_BACKEND") or conf["judge"]["backend"] or "auto").lower()
    if wanted != "auto":
        if wanted not in ("anthropic", "claude", "opencode"):
            raise JudgeUnavailable(f"unknown CV_JUDGE_BACKEND '{wanted}' (use anthropic, claude or opencode)")
        return wanted
    if _has_anthropic():
        return "anthropic"
    if shutil.which("claude"):
        return "claude"
    if shutil.which("opencode"):
        return "opencode"
    raise JudgeUnavailable(
        "no LLM backend available: set ANTHROPIC_API_KEY (and run scripts/setup.sh), "
        "or install the `claude` or `opencode` CLI")


def _model_for(backend: str, conf: dict) -> str:
    env = os.environ.get("CV_JUDGE_MODEL")
    if env:
        return env
    return conf["judge"].get(f"{backend}_model", "") or ""


def _run_anthropic(prompt: str, model: str, timeout: int) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise JudgeUnavailable("the `anthropic` package is not installed; run scripts/setup.sh") from exc
    client = anthropic.Anthropic(timeout=timeout)
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": SCHEMA},
        },
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise JudgeError("the model declined the request (stop_reason=refusal)")
    if response.stop_reason == "max_tokens":
        raise JudgeError("the model's answer was cut off (max_tokens)")
    return "".join(b.text for b in response.content if b.type == "text")


def _run_cli(cmd: list[str], prompt: str, timeout: int, attach_as: str | None = None) -> str:
    """Run a CLI in an empty temp dir, so it does not pick up this vault's
    AGENTS.md / CLAUDE.md and start acting as the vault agent. With attach_as,
    the prompt is written into that dir (CLIs refuse files outside their
    working dir in non-interactive mode) instead of being sent on stdin."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = os.path.realpath(tmp)  # macOS: /var -> /private/var, else CLIs call it "external"
        stdin = prompt
        if attach_as:
            path = os.path.join(tmp, attach_as)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(prompt)
            cmd = [path if part == attach_as else part for part in cmd]
            stdin = None
        env = dict(os.environ, PWD=tmp)  # some CLIs resolve paths from $PWD
        try:
            proc = subprocess.run(cmd, input=stdin, capture_output=True, text=True,
                                  timeout=timeout, cwd=tmp, env=env)
        except subprocess.TimeoutExpired as exc:
            raise JudgeError(f"`{cmd[0]}` timed out after {timeout}s") from exc
    if proc.returncode != 0:
        raise JudgeError(f"`{cmd[0]}` exited {proc.returncode}: {proc.stderr.strip()[-500:]}")
    return proc.stdout


def _run_claude(prompt: str, model: str, timeout: int) -> str:
    cmd = ["claude", "-p", "--output-format", "text"]
    if model:
        cmd += ["--model", model]
    return _run_cli(cmd, prompt, timeout)


def _run_opencode(prompt: str, model: str, timeout: int) -> str:
    # The prompt is too long for a command-line argument, so attach it as a file.
    name = "cv_judge_prompt.md"
    cmd = ["opencode", "run",
           "Follow the instructions in the attached file exactly. "
           "Read the whole file. Reply with only the JSON object."]
    if model:
        cmd += ["--model", model]
    cmd += ["--file", name]  # last: --file takes an array of values
    return _run_cli(cmd, prompt, timeout, attach_as=name)


RUNNERS = {"anthropic": _run_anthropic, "claude": _run_claude, "opencode": _run_opencode}


# ------------------------------------------------------------------- parsing
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def parse_answer(text: str) -> dict:
    """Find the JSON verdict in a model answer (tolerates fences/log noise)."""
    text = ANSI.sub("", text)
    decoder = json.JSONDecoder()
    found = None
    for i, ch in enumerate(text):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "unsupported_claims" in obj:
            found = obj  # keep the last one: CLIs may echo the prompt's example
    if found is None or not isinstance(found.get("unsupported_claims"), list):
        snippet = text.strip()[-400:]
        raise JudgeError(f"could not find the JSON verdict in the model's answer: …{snippet}")
    if not found["unsupported_claims"] and not found.get("claims_checked"):
        # An empty list with nothing checked means the model never read the CV.
        raise JudgeError("the model reported checking 0 claims; it probably did not read "
                         "the CV. Try another model (CV_JUDGE_MODEL) or backend.")
    return found


# ---------------------------------------------------------------------- main
def judge(cv_text: str, sources: dict[str, str], conf: dict | None = None) -> Verdict:
    conf = conf or load_config()
    backend = pick_backend(conf)
    model = _model_for(backend, conf)
    timeout = int(conf["judge"].get("timeout_seconds", 600))
    prompt = build_prompt(cv_text, sources)

    key = hashlib.sha256(
        "\0".join([PROMPT_VERSION, backend, model, prompt]).encode()).hexdigest()[:32]
    cache_file = os.path.join(CACHE_DIR, key + ".json")
    use_cache = os.environ.get("CV_JUDGE_NO_CACHE") != "1"
    if use_cache and os.path.exists(cache_file):
        with open(cache_file, encoding="utf-8") as fh:
            data = json.load(fh)
        cached = True
    else:
        data = parse_answer(RUNNERS[backend](prompt, model, timeout))
        cached = False
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    claims = [c if isinstance(c, dict) else {"claim": str(c)} for c in data["unsupported_claims"]]
    return Verdict(backend=backend, model=model or "(CLI default)",
                   unsupported=claims, claims_checked=int(data.get("claims_checked") or 0),
                   cached=cached)
