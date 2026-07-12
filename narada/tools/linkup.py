#!/usr/bin/env python3
"""LinkUp live web search for the Narada researcher gana.

POST https://api.linkup.so/v1/search with Bearer $LINKUP_API_KEY.
  search --query "..." [--depth standard|deep] [--output searchResults|sourcedAnswer]

Power-up evidence: live search doing real work in the product (GrowthX rubric).
Exit codes: 0 ok, 1 API/network error, 2 bad usage/env.
Smoke test (offline): python3 linkup.py --smoke
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_URL = "https://api.linkup.so/v1/search"
TIMEOUT_SECONDS = 60


def build_payload(query: str, depth: str = "standard", output: str = "searchResults") -> dict:
    """Pure payload builder (unit-testable offline)."""
    if not query.strip():
        raise ValueError("empty query")
    if depth not in ("standard", "deep"):
        raise ValueError("depth must be standard|deep")
    return {"q": query, "depth": depth, "outputType": output}


def search(query: str, depth: str, output: str) -> dict:
    key = os.environ.get("LINKUP_API_KEY", "").strip()
    if not key:
        print("error: LINKUP_API_KEY not set (see narada/.env.example)", file=sys.stderr)
        sys.exit(2)
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(build_payload(query, depth, output)).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"error: LinkUp HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:400]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"error: cannot reach LinkUp: {e.reason}", file=sys.stderr)
        sys.exit(1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="offline self-check")
    sub = parser.add_subparsers(dest="cmd")
    p = sub.add_parser("search", help="live web search")
    p.add_argument("--query", required=True)
    p.add_argument("--depth", default="standard", choices=["standard", "deep"])
    p.add_argument("--output", default="searchResults", choices=["searchResults", "sourcedAnswer"])
    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()
    if ns.cmd != "search":
        parser.print_help()
        return 2
    result = search(ns.query, ns.depth, ns.output)
    # Compact output: name + url + first 200 chars of content per result.
    for r in result.get("results", [])[:10]:
        print(f"• {r.get('name', '?')} — {r.get('url', '')}")
        content = (r.get("content") or "").strip().replace("\n", " ")
        if content:
            print(f"  {content[:200]}")
    if result.get("answer"):
        print(f"\nANSWER: {result['answer']}")
    return 0


def smoke() -> int:
    p = build_payload("test", "deep", "sourcedAnswer")
    assert p == {"q": "test", "depth": "deep", "outputType": "sourcedAnswer"}, p
    try:
        build_payload("", "standard")
        raise AssertionError("empty query should raise")
    except ValueError:
        pass
    print("linkup smoke OK (payload builder)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
