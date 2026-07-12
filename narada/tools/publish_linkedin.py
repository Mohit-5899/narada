#!/usr/bin/env python3
"""Post to LinkedIn via the ugcPosts API. STATUS: STUB / UNTESTED (P4 surface).

TODO before this is real:
  1. LinkedIn OAuth app with w_member_social scope, member access token.
  2. Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN (urn:li:person:XXXX).
  3. Verify against api.linkedin.com — the request below follows the docs
     (https://learn.microsoft.com/linkedin/consumer/integrations/self-serve/share-on-linkedin)
     but has NOT been exercised end-to-end. Expect 401/403 until step 1-2 done.

This tool fails loudly and honestly; it never fakes a post.

Usage: python3 publish_linkedin.py --text "post" | --text-file /tmp/post.txt
Exit codes: 0 posted, 1 API error, 2 bad usage / not configured.
Smoke test (offline): python3 publish_linkedin.py --smoke
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 30
ENDPOINT = "https://api.linkedin.com/v2/ugcPosts"
MAX_POST_CHARS = 3000  # LinkedIn UGC limit


def build_payload(author_urn: str, text: str) -> dict:
    """Pure payload builder — testable offline."""
    if not text.strip():
        raise ValueError("refusing to post empty text")
    if len(text) > MAX_POST_CHARS:
        raise ValueError(f"post is {len(text)} chars; LinkedIn max is {MAX_POST_CHARS}")
    if not author_urn.startswith("urn:li:"):
        raise ValueError(f"LINKEDIN_AUTHOR_URN must start with 'urn:li:', got {author_urn!r}")
    return {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text")
    group.add_argument("--text-file")
    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()

    token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "").strip()
    author = os.environ.get("LINKEDIN_AUTHOR_URN", "").strip()
    if not token or not author:
        print(
            "error: LinkedIn publishing is NOT configured (P4 surface, untested).\n"
            "Set LINKEDIN_ACCESS_TOKEN + LINKEDIN_AUTHOR_URN after completing the\n"
            "OAuth TODO in this file's header. Use publish_telegram_channel.py or\n"
            "send_email.py as reliable surfaces instead.",
            file=sys.stderr,
        )
        return 2

    if ns.text_file:
        with open(ns.text_file, "r", encoding="utf-8") as f:
            text = f.read()
    elif ns.text:
        text = ns.text
    else:
        print("error: provide --text or --text-file", file=sys.stderr)
        return 2

    try:
        payload = build_payload(author, text)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            post_id = resp.headers.get("x-restli-id") or ""
            print(json.dumps({"ok": True, "post_id": post_id}))
            return 0
    except urllib.error.HTTPError as e:
        print(
            f"error: LinkedIn API HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}\n"
            "(This surface is untested — see TODO in file header.)",
            file=sys.stderr,
        )
        return 1
    except urllib.error.URLError as e:
        print(f"error: cannot reach LinkedIn API: {e.reason}", file=sys.stderr)
        return 1


def smoke() -> int:
    p = build_payload("urn:li:person:abc", "hello world")
    assert p["author"] == "urn:li:person:abc"
    assert p["specificContent"]["com.linkedin.ugc.ShareContent"]["shareCommentary"]["text"] == "hello world"
    for bad_args in (("urn:li:person:abc", ""), ("person:abc", "hi"), ("urn:li:person:abc", "x" * 3001)):
        try:
            build_payload(*bad_args)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    print("publish_linkedin smoke OK (payload builder; API path remains untested)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
