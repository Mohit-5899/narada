#!/usr/bin/env python3
"""Narada ↔ Convex bridge.

POSTs to a single Convex HTTP action at $CONVEX_URL/api/agent with a shared
secret. The Convex side dispatches on the "fn" field. Functions:

  get-business    fn=get_business_by_telegram_id  {telegram_user_id}
  bind-telegram   fn=bind_telegram                {link_token, telegram_user_id}
  save-brief      fn=save_brand_brief             {business_id, brief(json)}
  log-task        fn=log_task                     {business_id, task_type, status, summary, surface?, output_ref?}
  append-eval-case fn=append_eval_case            {business_id, brief, failure, expected}
  get-tasks       fn=get_tasks                    {business_id, limit}

Env: CONVEX_URL (e.g. https://happy-otter-123.convex.site), CONVEX_AGENT_SECRET.
Exit codes: 0 ok, 1 remote/HTTP error, 2 bad usage/env.

Smoke test (offline): python3 convex_client.py --smoke
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 30


def _require_env() -> tuple:
    url = os.environ.get("CONVEX_URL", "").strip().rstrip("/")
    secret = os.environ.get("CONVEX_AGENT_SECRET", "").strip()
    missing = [n for n, v in (("CONVEX_URL", url), ("CONVEX_AGENT_SECRET", secret)) if not v]
    if missing:
        print(f"error: missing env vars: {', '.join(missing)} (see narada/.env.example)", file=sys.stderr)
        sys.exit(2)
    return url, secret


def build_payload(fn: str, args: dict) -> dict:
    """Pure payload builder (unit-testable offline)."""
    clean = {k: v for k, v in args.items() if v is not None}
    return {"fn": fn, "args": clean}


def call_convex(fn: str, args: dict) -> dict:
    url, secret = _require_env()
    payload = build_payload(fn, args)
    req = urllib.request.Request(
        f"{url}/api/agent",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {secret}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"error: Convex HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"error: cannot reach Convex at {url}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print(f"error: Convex returned non-JSON: {body[:500]}", file=sys.stderr)
        sys.exit(1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("get-business", help="resolve telegram user -> business + brand brief")
    p.add_argument("--telegram-user-id", required=True)

    p = sub.add_parser("bind-telegram", help="bind telegram_user_id to a business via link token")
    p.add_argument("--link-token", required=True)
    p.add_argument("--telegram-user-id", required=True)

    p = sub.add_parser("save-brief", help="save/replace a brand brief (JSON string or @file)")
    p.add_argument("--business-id", required=True)
    p.add_argument("--brief", required=True, help="JSON string, or @path/to/file.json")

    p = sub.add_parser("log-task", help="log a completed agency task")
    p.add_argument("--business-id", required=True)
    p.add_argument("--task-type", required=True, choices=["research", "copy", "publish", "analysis", "chat"])
    p.add_argument("--status", required=True, choices=["done", "failed"])
    p.add_argument("--summary", required=True)
    p.add_argument("--surface", default=None)
    p.add_argument("--output-ref", default=None)

    p = sub.add_parser("append-eval-case", help="append a failure/escalation to the eval set")
    p.add_argument("--business-id", required=True)
    p.add_argument("--brief", required=True)
    p.add_argument("--failure", required=True)
    p.add_argument("--expected", required=True)

    p = sub.add_parser("get-tasks", help="read task history for a business")
    p.add_argument("--business-id", required=True)
    p.add_argument("--limit", type=int, default=50)

    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()
    if not ns.cmd:
        parser.print_help()
        return 2

    if ns.cmd == "get-business":
        result = call_convex("get_business_by_telegram_id", {"telegram_user_id": str(ns.telegram_user_id)})
    elif ns.cmd == "bind-telegram":
        result = call_convex("bind_telegram", {"link_token": ns.link_token, "telegram_user_id": str(ns.telegram_user_id)})
    elif ns.cmd == "save-brief":
        raw = ns.brief
        if raw.startswith("@"):
            with open(raw[1:], "r", encoding="utf-8") as f:
                raw = f.read()
        try:
            brief = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"error: --brief is not valid JSON: {e}", file=sys.stderr)
            return 2
        result = call_convex("save_brand_brief", {"business_id": ns.business_id, "brief": brief})
    elif ns.cmd == "log-task":
        result = call_convex("log_task", {
            "business_id": ns.business_id, "task_type": ns.task_type, "status": ns.status,
            "summary": ns.summary, "surface": ns.surface, "output_ref": ns.output_ref,
        })
    elif ns.cmd == "append-eval-case":
        result = call_convex("append_eval_case", {
            "business_id": ns.business_id, "brief": ns.brief,
            "failure": ns.failure, "expected": ns.expected,
        })
    elif ns.cmd == "get-tasks":
        result = call_convex("get_tasks", {"business_id": ns.business_id, "limit": ns.limit})
    else:  # pragma: no cover
        return 2

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def smoke() -> int:
    """Offline self-checks — no network, no env required."""
    p = build_payload("log_task", {"business_id": "b1", "surface": None, "summary": "s"})
    assert p == {"fn": "log_task", "args": {"business_id": "b1", "summary": "s"}}, p
    p = build_payload("get_business_by_telegram_id", {"telegram_user_id": "42"})
    assert p["args"]["telegram_user_id"] == "42"
    configured = bool(os.environ.get("CONVEX_URL")) and bool(os.environ.get("CONVEX_AGENT_SECRET"))
    print(f"convex_client smoke OK (payload builder). env configured: {configured}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
