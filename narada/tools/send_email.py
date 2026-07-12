#!/usr/bin/env python3
"""Send an email via the Resend API (https://resend.com/docs/api-reference/emails/send-email).

Env: RESEND_API_KEY, NARADA_EMAIL_FROM (verified sender, e.g. "Narada <hi@yourdomain.com>").

Usage:
  python3 send_email.py --to owner@example.com --subject "Launch" --html-file /tmp/mail.html
  python3 send_email.py --to a@b.co --subject "Hi" --text "plain body"

Exit codes: 0 sent, 1 API error, 2 bad usage/env.
Smoke test (offline): python3 send_email.py --smoke
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 30
RESEND_ENDPOINT = "https://api.resend.com/emails"


def build_payload(sender: str, to: list, subject: str, html: str = None, text: str = None) -> dict:
    """Pure payload builder — testable offline."""
    if not subject.strip():
        raise ValueError("subject must not be empty")
    if not (html or text):
        raise ValueError("provide html or text body")
    payload = {"from": sender, "to": to, "subject": subject}
    if html:
        payload["html"] = html
    if text:
        payload["text"] = text
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    parser.add_argument("--to", action="append", help="recipient (repeatable)")
    parser.add_argument("--subject")
    parser.add_argument("--from", dest="sender", default=os.environ.get("NARADA_EMAIL_FROM", ""),
                        help='sender, default $NARADA_EMAIL_FROM (must be Resend-verified)')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--html-file", help="HTML body file")
    group.add_argument("--text", help="plain-text body")
    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()

    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        print("error: RESEND_API_KEY not set", file=sys.stderr)
        return 2
    if not ns.to or not ns.subject:
        print("error: --to and --subject are required", file=sys.stderr)
        return 2
    if not ns.sender:
        print("error: no --from and $NARADA_EMAIL_FROM unset", file=sys.stderr)
        return 2

    html = None
    if ns.html_file:
        with open(ns.html_file, "r", encoding="utf-8") as f:
            html = f.read()
    try:
        payload = build_payload(ns.sender, ns.to, ns.subject, html=html, text=ns.text)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"error: Resend HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"error: cannot reach Resend: {e.reason}", file=sys.stderr)
        return 1

    print(json.dumps({"ok": True, "email_id": data.get("id")}))
    return 0


def smoke() -> int:
    p = build_payload("Narada <n@x.co>", ["a@b.co"], "S", text="body")
    assert p == {"from": "Narada <n@x.co>", "to": ["a@b.co"], "subject": "S", "text": "body"}
    try:
        build_payload("n@x.co", ["a@b.co"], "S")
        raise AssertionError("expected ValueError for missing body")
    except ValueError:
        pass
    print("send_email smoke OK (payload builder)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
