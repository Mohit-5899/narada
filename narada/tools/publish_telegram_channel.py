#!/usr/bin/env python3
"""Post approved copy to a Telegram channel via the Bot API (sendMessage).

The bot must be an admin of the target channel. Most reliable Narada surface.

Env: TELEGRAM_BOT_TOKEN (or NARADA_TELEGRAM_BOT_TOKEN to use a separate bot),
     NARADA_TELEGRAM_CHANNEL (default channel when --channel omitted).

Usage:
  python3 publish_telegram_channel.py --channel @mychannel --text "final copy"
  python3 publish_telegram_channel.py --text-file /tmp/post.txt   # uses default channel

Exit codes: 0 posted, 1 API error, 2 bad usage/env.
Smoke test (offline): python3 publish_telegram_channel.py --smoke
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT_SECONDS = 30
MAX_MESSAGE_CHARS = 4096  # Telegram hard limit


def build_request(token: str, channel: str, text: str, parse_mode: str) -> tuple:
    """Return (url, form-encoded body bytes). Pure — testable offline."""
    if not text.strip():
        raise ValueError("refusing to post empty message")
    if len(text) > MAX_MESSAGE_CHARS:
        raise ValueError(f"message is {len(text)} chars; Telegram max is {MAX_MESSAGE_CHARS}")
    params = {"chat_id": channel, "text": text}
    if parse_mode != "none":
        params["parse_mode"] = parse_mode
    return (
        f"https://api.telegram.org/bot{token}/sendMessage",
        urllib.parse.urlencode(params).encode("utf-8"),
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    parser.add_argument("--channel", default=os.environ.get("NARADA_TELEGRAM_CHANNEL", ""),
                        help="@channelusername or -100... id (default: $NARADA_TELEGRAM_CHANNEL)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--text", help="message text")
    group.add_argument("--text-file", help="read message text from file (preferred; avoids shell quoting)")
    parser.add_argument("--parse-mode", default="none", choices=["none", "HTML", "MarkdownV2"])
    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()

    token = (os.environ.get("NARADA_TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    if not token:
        print("error: TELEGRAM_BOT_TOKEN (or NARADA_TELEGRAM_BOT_TOKEN) not set", file=sys.stderr)
        return 2
    if not ns.channel:
        print("error: no --channel and $NARADA_TELEGRAM_CHANNEL unset", file=sys.stderr)
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
        url, body = build_request(token, ns.channel, text, ns.parse_mode)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"error: Telegram API HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(f"error: cannot reach Telegram API: {e.reason}", file=sys.stderr)
        return 1

    if not data.get("ok"):
        print(f"error: Telegram rejected message: {json.dumps(data)[:500]}", file=sys.stderr)
        return 1
    msg = data["result"]
    print(json.dumps({"ok": True, "message_id": msg.get("message_id"), "chat": msg.get("chat", {}).get("username") or msg.get("chat", {}).get("id")}))
    return 0


def smoke() -> int:
    url, body = build_request("TOK", "@chan", "hello", "none")
    assert url.endswith("/botTOK/sendMessage") and b"chat_id=%40chan" in body and b"parse_mode" not in body
    _, body = build_request("TOK", "@chan", "hi", "HTML")
    assert b"parse_mode=HTML" in body
    for bad_text in ("", "x" * (MAX_MESSAGE_CHARS + 1)):
        try:
            build_request("TOK", "@chan", bad_text, "none")
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    print("publish_telegram_channel smoke OK (request builder)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
