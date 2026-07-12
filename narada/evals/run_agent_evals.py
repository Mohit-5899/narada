#!/usr/bin/env python3
"""Narada live agent evals — one canned workflow task per agent, checked programmatically.

Layer 2 of the pre-deploy gate (layer 1 = check_skills.py, free/static).
Each case in agent_evals.jsonl is a self-contained task_prompt (mini brand
context inline) run through Hermes one-shot mode:

  uv run hermes-agent --query="..." --enabled_toolsets=reasoning --max_turns=4

and the FINAL RESPONSE is checked with string/regex assertions (280-char X
limit, CTA present, refusal to publish unapproved, LEARNINGS block, ...).

Usage:
  python3 run_agent_evals.py            # DRY (default): validate cases, print plan. Free.
  python3 run_agent_evals.py --live     # execute all 6 cases. COSTS TOKENS:
                                        #   ~$0.10-0.50 per case depending on model.
  python3 run_agent_evals.py --live --case copywriter_x_post
  python3 run_agent_evals.py --smoke    # offline self-checks

Prerequisites for --live:
  - repo root has a working `uv run hermes-agent` (model API key in env,
    e.g. OPENROUTER_API_KEY)
  - narada skills wired into ~/.hermes/config.yaml (skills.external_dirs,
    README step 3) so "Follow the narada-<x> skill" resolves. Without that
    the prompts still run but you are testing the bare model, not the skill.
  - No live surface is touched: every case uses the "reasoning" toolset only.

Manual alternative (no CLI): each case carries a "manual" field — the exact
Telegram message to send @NaradaMarketingbot and what to eyeball.

Outputs saved to outputs_agents/<git-label>/<id>.txt for inspection/re-check.
Exit codes: 0 all pass (or dry-valid), 1 check failures, 2 setup problem.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from run_evals import git_label  # same table/exit conventions as run_evals.py

HERE = Path(__file__).resolve().parent
CASES_FILE = HERE / "agent_evals.jsonl"
REPO_ROOT = HERE.parent.parent
OUT_DIR = HERE / "outputs_agents"

CHECK_TYPES = {"max_chars", "max_words", "regex_present", "regex_absent"}
FINAL_MARKER = "FINAL RESPONSE:"
LIVE_TIMEOUT_S = 600


def load_cases() -> list:
    if not CASES_FILE.exists():
        print(f"error: {CASES_FILE} not found", file=sys.stderr)
        sys.exit(2)
    cases = []
    for i, line in enumerate(CASES_FILE.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"error: agent_evals.jsonl line {i} is invalid JSON: {e}", file=sys.stderr)
            sys.exit(2)
    return cases


def validate_case(case: dict) -> list:
    """Return list of problems (empty = valid)."""
    problems = []
    for key in ("id", "agent", "skill", "task_prompt", "checks"):
        if not case.get(key):
            problems.append(f"missing '{key}'")
    for i, check in enumerate(case.get("checks") or []):
        ctype = check.get("type")
        if ctype not in CHECK_TYPES:
            problems.append(f"checks[{i}]: unknown type {ctype!r}")
            continue
        if ctype in ("max_chars", "max_words") and not isinstance(check.get("limit"), int):
            problems.append(f"checks[{i}]: {ctype} needs int 'limit'")
        if ctype in ("regex_present", "regex_absent"):
            try:
                re.compile(check.get("pattern") or "", re.IGNORECASE)
            except re.error as e:
                problems.append(f"checks[{i}]: bad pattern: {e}")
    return problems


def run_check(check: dict, text: str) -> bool:
    ctype = check["type"]
    if ctype == "max_chars":
        return len(text.strip()) <= check["limit"]
    if ctype == "max_words":
        body = text
        stop = check.get("strip_from")
        if stop:
            i = body.upper().find(stop.upper())
            if i != -1:
                body = body[:i]
        return len(body.split()) <= check["limit"]
    if ctype == "regex_present":
        return bool(re.search(check["pattern"], text, re.IGNORECASE))
    if ctype == "regex_absent":
        return not re.search(check["pattern"], text, re.IGNORECASE)
    raise ValueError(f"unknown check type {ctype!r}")


def check_name(check: dict) -> str:
    return check.get("why") or check["type"]


def build_cmd(case: dict) -> list:
    run = case.get("run", {})
    cmd = [
        "uv", "run", "hermes-agent",
        f"--query={case['task_prompt']}",
        f"--max_turns={run.get('max_turns', 4)}",
    ]
    if run.get("enabled_toolsets"):
        cmd.append(f"--enabled_toolsets={run['enabled_toolsets']}")
    return cmd


def extract_final_response(stdout: str):
    """Pull the model's answer out of run_agent.py's decorated stdout."""
    idx = stdout.rfind(FINAL_MARKER)
    if idx == -1:
        return None
    body = []
    started = False
    for line in stdout[idx + len(FINAL_MARKER):].splitlines():
        if not started and line.strip("- ") == "":  # skip blank + dashed separator
            continue
        started = True
        body.append(line)
    return "\n".join(body).strip() or None


SKILLS_DIR = REPO_ROOT / "narada" / "skills"
EVAL_MODEL = os.environ.get("NARADA_EVAL_MODEL", "claude-haiku-4-5")


def anthropic_call(system: str, user: str) -> str:
    """Direct Anthropic Messages API — production parity: the gateway injects
    skill content as context; here the SKILL.md is the system prompt.
    No OpenRouter, no Hermes loop (cases are tool-free by design)."""
    import urllib.request
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps({
            "model": EVAL_MODEL,
            "max_tokens": 1024,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }).encode("utf-8"),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=LIVE_TIMEOUT_S) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(b.get("text", "") for b in data.get("content", []))


def run_live_case(case: dict, out_dir: Path) -> dict:
    """Execute one case; return {'id', 'agent', 'results': {name: bool} | None, 'error': str|None}."""
    skill_file = SKILLS_DIR / f"narada-{case['agent']}" / "SKILL.md"
    try:
        skill = skill_file.read_text(encoding="utf-8")
    except OSError as e:
        return {"id": case["id"], "agent": case["agent"], "results": None,
                "error": f"skill file missing: {e}"}
    system = "You are a Narada specialist agent. Follow this skill exactly.\n\n" + skill
    try:
        text = anthropic_call(system, case["task_prompt"])
    except Exception as e:
        return {"id": case["id"], "agent": case["agent"], "results": None,
                "error": f"API call failed: {e}"}
    (out_dir / f"{case['id']}.raw.txt").write_text(text, encoding="utf-8")
    if not text.strip():
        return {"id": case["id"], "agent": case["agent"], "results": None,
                "error": "empty response"}
    (out_dir / f"{case['id']}.txt").write_text(text, encoding="utf-8")
    results = {check_name(c): run_check(c, text) for c in case["checks"]}
    return {"id": case["id"], "agent": case["agent"], "results": results, "error": None}


def print_results(rows: list) -> bool:
    """run_evals.py-style table; returns True if everything passed."""
    header = f"{'case':<28}{'agent':<12}{'checks':<10}failed"
    print(f"\ngit: {git_label()}   cases: {len(rows)}")
    print(header)
    print("-" * max(len(header), 70))
    all_ok = True
    for row in rows:
        if row["results"] is None:
            all_ok = False
            print(f"{row['id']:<28}{row['agent']:<12}{'ERROR':<10}{row['error']}")
            continue
        passed = sum(row["results"].values())
        total = len(row["results"])
        fails = [n for n, ok in row["results"].items() if not ok]
        all_ok = all_ok and not fails
        print(f"{row['id']:<28}{row['agent']:<12}{f'{passed}/{total}':<10}{', '.join(fails) or '-'}")
    print()
    return all_ok


def dry_run(cases: list) -> int:
    problems_total = 0
    print(f"DRY RUN — {len(cases)} cases validated, nothing executed (use --live to run; "
          f"~$0.10-0.50/case).\n")
    for case in cases:
        problems = validate_case(case)
        problems_total += len(problems)
        status = "INVALID" if problems else "ok"
        print(f"[{status}] {case.get('id', '?'):<28} agent={case.get('agent', '?'):<11} "
              f"checks={len(case.get('checks') or [])}")
        for p in problems:
            print(f"          - {p}")
        if not problems:
            cmd = build_cmd(case)
            shown = [c if len(c) <= 70 else c[:67] + "..." for c in cmd]
            print(f"          cmd: {' '.join(shown)}")
            print(f"          manual: {case.get('manual', '-')}")
    print()
    if problems_total:
        print(f"INVALID case file: {problems_total} problem(s).")
        return 2
    print("Case file valid. Run with --live to execute.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--live", action="store_true",
                        help="execute cases via `uv run hermes-agent` (~$0.10-0.50 per case)")
    parser.add_argument("--case", help="run only this case id")
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()

    cases = load_cases()
    if ns.case:
        cases = [c for c in cases if c.get("id") == ns.case]
        if not cases:
            print(f"error: no case with id {ns.case!r}", file=sys.stderr)
            return 2

    if not ns.live:
        return dry_run(cases)

    bad = {c.get("id"): validate_case(c) for c in cases if validate_case(c)}
    if bad:
        print(f"error: fix case file first (run without --live for details): {list(bad)}",
              file=sys.stderr)
        return 2

    out_dir = OUT_DIR / git_label()
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in cases:
        print(f"running {case['id']} ({case['agent']}) ...", flush=True)
        rows.append(run_live_case(case, out_dir))
    ok = print_results(rows)
    print(f"outputs: {out_dir}")
    try:
        push_scores_to_langfuse(rows, git_label())  # silent skip if keys unset
    except Exception as e:
        print(f"(langfuse push failed, results still valid locally: {e})")
    return 0 if ok else 1


def smoke() -> int:
    # Response extraction from run_agent.py's decorated stdout.
    stdout = "banner\n🎯 FINAL RESPONSE:\n" + "-" * 30 + "\n\nHello world\nline 2"
    assert extract_final_response(stdout) == "Hello world\nline 2"
    assert extract_final_response("no marker here") is None

    # Each check type, pass + fail paths.
    assert run_check({"type": "max_chars", "limit": 5}, "abc  ")
    assert not run_check({"type": "max_chars", "limit": 2}, "abcd")
    assert run_check({"type": "max_words", "limit": 2, "strip_from": "SOURCES"},
                     "two words\nSOURCES\nmany many more words here")
    assert not run_check({"type": "max_words", "limit": 1}, "three words here")
    assert run_check({"type": "regex_present", "pattern": r"\bcta\b"}, "has a CTA now")
    assert not run_check({"type": "regex_absent", "pattern": "banned"}, "a BANNED word")

    # The shipped case file is valid.
    for case in load_cases():
        problems = validate_case(case)
        assert not problems, f"{case.get('id')}: {problems}"

    # Command construction.
    cmd = build_cmd({"task_prompt": "hi", "run": {"enabled_toolsets": "reasoning", "max_turns": 3}})
    assert cmd[:3] == ["uv", "run", "hermes-agent"] and "--enabled_toolsets=reasoning" in cmd, cmd

    print("run_agent_evals smoke OK")
    return 0


# ---------------------------------------------------------------- langfuse
def push_scores_to_langfuse(rows: list, label: str) -> None:
    """Push eval results into Langfuse as one trace + one score per case,
    so eval history lives next to the runtime traces (trend over versions).
    Uses the public ingestion API with basic auth; no SDK dependency."""
    import base64
    import datetime
    import urllib.request
    import uuid
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
    sk = os.environ.get("LANGFUSE_SECRET_KEY", "")
    host = os.environ.get("LANGFUSE_BASE_URL", "https://jp.cloud.langfuse.com").rstrip("/")
    if not (pk and sk):
        print("(langfuse push skipped: LANGFUSE_PUBLIC_KEY/SECRET_KEY not set)")
        return
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    trace_id = str(uuid.uuid4())
    batch = [{
        "id": str(uuid.uuid4()), "type": "trace-create", "timestamp": now,
        "body": {"id": trace_id, "name": f"narada-eval-run {label}",
                 "tags": ["evals", label], "timestamp": now},
    }]
    for r in rows:
        results = r.get("results") or {}
        passed = sum(1 for v in results.values() if v)
        total = len(results) or 1
        batch.append({
            "id": str(uuid.uuid4()), "type": "score-create", "timestamp": now,
            "body": {"id": str(uuid.uuid4()), "traceId": trace_id,
                     "name": f"eval:{r['id']}", "value": passed / total,
                     "comment": f"{passed}/{total} checks · agent={r['agent']}"
                                + (f" · ERROR: {r['error']}" if r.get("error") else "")},
        })
    req = urllib.request.Request(
        f"{host}/api/public/ingestion",
        data=json.dumps({"batch": batch}).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Basic " + base64.b64encode(f"{pk}:{sk}".encode()).decode()},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        resp.read()
    print(f"langfuse: pushed {len(rows)} eval scores (trace 'narada-eval-run {label}')")


if __name__ == "__main__":
    sys.exit(main())
