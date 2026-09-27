#!/usr/bin/env python3
"""
lmtest.py -- drive the 6502-codegen skill against a model behind any
OpenAI-compatible chat-completions endpoint (LM Studio, llama.cpp's server,
vLLM, a LiteLLM proxy, a hosted gateway, ...). The endpoint is just a base URL;
nothing here assumes it is local, or that it is LM Studio specifically.

No new third-party packages: this script is stdlib-only. The skill's own
verifier (scripts/run.py -> py65) is the oracle, so run this with the SAME
Python environment where you installed py65 for the skill (e.g. activate the
skill's .venv first).

Flow:
  1. Load SKILL.md as the system prompt (the skill's instructions + contract).
  2. Send your task to the OpenAI-compatible endpoint.
  3. Pull the JSON test spec out of the model's reply.
  4. Hand that spec to the skill's run.py and report PASS / FAIL via exit code.
  5. (optional) feed failures back and let the model retry.

Endpoint / auth (each: flag, then env vars, then default):
  url    --url      $LMTEST_URL      $OPENAI_BASE_URL   default http://localhost:1234/v1
  key    --api-key  $LMTEST_API_KEY  $OPENAI_API_KEY    default none (sent as Bearer if set)
  model  --model    (auto-detected via /models; some endpoints need it explicit)

Usage:
  python lmtest.py "multiply two unsigned bytes, result in A:ZP_PTR"
  python lmtest.py --url http://localhost:1234/v1 --iters 3 "signed divide"
  python lmtest.py --url https://gw.example.com/v1 --api-key sk-... --model my-model "..."
  echo "rotate a 16-bit value left through carry" | python lmtest.py

The skill directory is found automatically if you run from inside its tree
(or drop this script anywhere in it). Otherwise set $LMTEST_SKILL or pass
--skill. Nothing is assumed about where the skill lives.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

SKILL_ENV = "LMTEST_SKILL"
DEFAULT_URL = "http://localhost:1234/v1"

# Nudge the model toward the run.py contract. SKILL.md documents the schema;
# this just guarantees the spec is last and self-contained so extraction is easy.
FORMAT_RULES = (
    "\n\n---\n"
    "When you return a routine, ALSO return a single fenced ```json block that "
    "is a valid spec for scripts/run.py: keys `program` (array of source lines), "
    "`origin` (int), `cpu` (\"nmos\" or \"65c02\"), and `cases` (array of "
    "{set, steps, expect}). The json block is what gets executed -- make it "
    "self-contained, put it LAST, and write nothing after it."
)


def _request(url, headers, data=None, timeout=600, soft=False):
    """GET (data=None) or POST a JSON endpoint. On network/HTTP failure either
    return None (soft=True) or exit with an actionable message (soft=False)."""
    req = urllib.request.Request(
        url, data=data, headers=headers,
        method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        if soft:
            return None
        if isinstance(e, urllib.error.HTTPError):
            body = e.read().decode(errors="replace")[:500]
            raise SystemExit(f"endpoint returned HTTP {e.code} for {url}\n{body}")
        raise SystemExit(
            f"couldn't reach {url}: {e.reason}\n"
            "Check the URL, the network, and that the server is up.")


def detect_model(base, headers):
    # /models is best-effort: not every endpoint exposes it, and auth may differ.
    res = _request(base + "/models", headers, timeout=10, soft=True)
    data = (res or {}).get("data", [])
    return data[0]["id"] if data else "auto"


def chat(base, model, messages, max_tokens, headers):
    payload = json.dumps({
        "model": model, "messages": messages,
        "temperature": 0.2, "max_tokens": max_tokens,
    }).encode()
    out = _request(base + "/chat/completions", headers, data=payload)
    return out["choices"][0]["message"]["content"]


def extract_spec(text):
    # Prefer fenced blocks; take the LAST one (final answer, past any <think>).
    # Capture everything between the fences so nested braces survive.
    blocks = re.findall(r"```(?:json)?\s*\n(.*?)```", text, re.S)
    for b in reversed(blocks):
        try:
            return json.loads(b.strip())
        except json.JSONDecodeError:
            pass
    # Fallback: largest brace-balanced span that parses (model forgot the fence).
    for s in (m.start() for m in re.finditer(r"\{", text)):
        depth = 0
        for i in range(s, len(text)):
            depth += (text[i] == "{") - (text[i] == "}")
            if depth == 0:
                try:
                    return json.loads(text[s:i + 1])
                except json.JSONDecodeError:
                    break
    return None


def run_spec(skill_dir, spec):
    run_py = os.path.join(skill_dir, "scripts", "run.py")
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(spec, f)
        path = f.name
    try:
        p = subprocess.run([sys.executable, run_py, path],
                           capture_output=True, text=True, timeout=120)
        return p.returncode, (p.stdout + p.stderr)
    finally:
        os.unlink(path)


def _is_skill_dir(path):
    """Looks like this skill: has SKILL.md and scripts/run.py."""
    return (os.path.isfile(os.path.join(path, "SKILL.md"))
            and os.path.isfile(os.path.join(path, "scripts", "run.py")))


def _walk_up(start):
    """Yield `start` and each parent directory up to the filesystem root."""
    cur = os.path.abspath(start)
    while True:
        yield cur
        parent = os.path.dirname(cur)
        if parent == cur:
            return
        cur = parent


def resolve_skill(explicit):
    """Find the skill directory without assuming any fixed root.

    Priority: --skill, then $LMTEST_SKILL (each validated, fail loud if wrong),
    then auto-detect by walking up from the CWD and from this script's location
    for a dir holding SKILL.md and scripts/run.py.
    """
    for label, raw in (("--skill", explicit),
                       ("$" + SKILL_ENV, os.environ.get(SKILL_ENV))):
        if not raw:
            continue
        path = os.path.abspath(os.path.expanduser(raw))
        if _is_skill_dir(path):
            return path
        raise SystemExit(
            f"{label} points at {path}, which doesn't look like the skill "
            "(missing SKILL.md or scripts/run.py).")
    for start in (os.getcwd(), os.path.dirname(os.path.abspath(__file__))):
        for d in _walk_up(start):
            if _is_skill_dir(d):
                return d
    raise SystemExit(
        "Couldn't locate the skill. Run from inside its tree, set "
        f"${SKILL_ENV}, or pass --skill /path/to/6502-codegen.")


def main():
    ap = argparse.ArgumentParser(
        description="Test the 6502-codegen skill against any OpenAI-compatible endpoint.")
    ap.add_argument("task", nargs="?", help="the 6502 task (or pipe via stdin)")
    ap.add_argument("--skill", default=None,
                    help="skill directory (default: auto-detect from CWD or this "
                         "script's location, or $LMTEST_SKILL)")
    ap.add_argument("--url", default=None,
                    help="OpenAI-compatible API base URL, e.g. http://host:1234/v1 "
                         "(default: $LMTEST_URL, $OPENAI_BASE_URL, else " + DEFAULT_URL + ")")
    ap.add_argument("--api-key", default=None,
                    help="bearer token if the endpoint needs auth "
                         "(default: $LMTEST_API_KEY, $OPENAI_API_KEY, else none)")
    ap.add_argument("--model", default=None,
                    help="model id; auto-detected via /models if omitted. Some "
                         "endpoints (e.g. OpenAI, some vLLM setups) require it explicitly.")
    ap.add_argument("--iters", type=int, default=1,
                    help="max attempts; >1 feeds verifier failures back to the model")
    ap.add_argument("--max-tokens", type=int, default=4096)
    ap.add_argument("--with-reference", action="store_true",
                    help="also inject the ~80K reference (heavy; needs a big context window)")
    args = ap.parse_args()

    task = args.task or sys.stdin.read().strip()
    if not task:
        ap.error("no task given (pass an argument or pipe one in)")

    base = (args.url or os.environ.get("LMTEST_URL")
            or os.environ.get("OPENAI_BASE_URL") or DEFAULT_URL).rstrip("/")
    api_key = (args.api_key or os.environ.get("LMTEST_API_KEY")
               or os.environ.get("OPENAI_API_KEY"))
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key

    skill = resolve_skill(args.skill)
    system = open(os.path.join(skill, "SKILL.md")).read()
    if args.with_reference:
        ref_path = os.path.join(skill, "references", "6502_reference.md")
        system += "\n\n# REFERENCE (6502_reference.md)\n" + open(ref_path).read()
    system += FORMAT_RULES

    model = args.model or detect_model(base, headers)
    print(f"[endpoint: {base}]  [model: {model}]  [skill: {skill}]  "
          f"[reference: {'on' if args.with_reference else 'off'}]\n")

    messages = [{"role": "system", "content": system},
                {"role": "user", "content": task}]

    for attempt in range(1, args.iters + 1):
        reply = chat(base, model, messages, args.max_tokens, headers)
        print(f"===== attempt {attempt}: model reply =====\n{reply}\n")

        spec = extract_spec(reply)
        if spec is None:
            print(">> no parseable JSON spec found (model ignored the contract).")
            if attempt < args.iters:
                messages += [
                    {"role": "assistant", "content": reply},
                    {"role": "user", "content":
                        "I couldn't find a valid ```json spec. Re-send the "
                        "routine with one self-contained json spec block, LAST, "
                        "and nothing after it."},
                ]
            continue

        code, out = run_spec(skill, spec)
        print(f"----- run.py (exit {code}) -----\n{out}")
        if code == 0:
            print(">> PASS")
            return 0
        if attempt < args.iters:
            messages += [
                {"role": "assistant", "content": reply},
                {"role": "user", "content":
                    f"The verifier reported a failure:\n{out}\n"
                    "Fix the routine and re-send the code plus a json spec."},
            ]

    print(">> did not pass within the iteration budget")
    return 1


if __name__ == "__main__":
    sys.exit(main())
