#!/usr/bin/env python3
"""Zernio social publishing client — Narada's primary publish surface.

Zernio (zernio.com) posts to connected social accounts (X, LinkedIn,
Instagram, etc.) via one API. Auth: "Authorization: Bearer $ZERNIO_API_KEY".

Subcommands:
  accounts   GET  /accounts     list connected accounts (platform/username/ids)
  post       POST /posts        publish now, or schedule with --schedule
  usage      GET  /usage-stats  plan usage / remaining quota

Usage:
  python3 zernio.py accounts
  python3 zernio.py post --content "final copy" --platform x \\
      --account-id acc_123 --profile-id prof_456 [--image-url https://...]
  python3 zernio.py post --content "..." --platform linkedin \\
      --account-id acc --profile-id prof \\
      --schedule 2026-07-13T09:00:00 --timezone Asia/Kolkata
  python3 zernio.py usage

Env: ZERNIO_API_KEY (required), ZERNIO_API_BASE (default https://zernio.com/api/v1).
Exit codes: 0 ok, 1 API/network error, 2 bad usage/env.
Smoke test (offline): python3 zernio.py --smoke
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 30
DEFAULT_BASE = "https://zernio.com/api/v1"


def build_post_payload(content: str, platform: str, account_id: str, profile_id: str,
                       image_url: str = None, schedule: str = None, timezone: str = None) -> dict:
    """Pure payload builder for POST /posts (unit-testable offline)."""
    if not content.strip():
        raise ValueError("refusing to post empty content")
    if not account_id or not profile_id:
        raise ValueError("account_id and profile_id are both required (run `zernio.py accounts`)")
    # Shape per https://zernio.com/llms.txt: platforms[] + top-level profileId,
    # mediaItems[] for images, publishNow XOR scheduledFor+timezone.
    payload = {
        "content": content,
        "publishNow": schedule is None,
        "platforms": [{"platform": platform, "accountId": account_id}],
        "profileId": profile_id,
    }
    if image_url:
        payload["mediaItems"] = [{"type": "image", "url": image_url}]
    if schedule:
        payload["scheduledFor"] = schedule
        payload["timezone"] = timezone or "UTC"
    return payload


def _api(method: str, path: str, payload: dict = None) -> dict:
    key = os.environ.get("ZERNIO_API_KEY", "").strip()
    if not key:
        print("error: ZERNIO_API_KEY not set (see narada/.env.example)", file=sys.stderr)
        sys.exit(2)
    base = os.environ.get("ZERNIO_API_BASE", DEFAULT_BASE).rstrip("/")
    req = urllib.request.Request(
        f"{base}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        print(f"error: Zernio API HTTP {e.code} on {path}: {e.read().decode('utf-8', 'replace')[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"error: cannot reach Zernio API: {e.reason}", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        print(f"error: Zernio returned non-JSON: {body[:500]}", file=sys.stderr)
        sys.exit(1)


def cmd_accounts() -> int:
    data = _api("GET", "/accounts")
    # ponytail: tolerate list or {accounts|data: [...]} envelope — API shape unverified until first real call
    accounts = data if isinstance(data, list) else data.get("accounts") or data.get("data") or []
    if not accounts:
        print("no connected accounts (connect one at zernio.com first)")
        return 0
    for a in accounts:
        # Real response (verified): account id is "_id"; profileId may be an
        # expanded object {"_id": ..., "name": ...} or a bare string.
        prof = a.get("profileId")
        prof_id = prof.get("_id", "?") if isinstance(prof, dict) else (prof or "?")
        prof_name = prof.get("name", "") if isinstance(prof, dict) else ""
        print(f"{a.get('platform', '?'):<12} @{a.get('username') or a.get('displayName') or prof_name or '?':<24} "
              f"accountId={a.get('_id') or a.get('accountId') or a.get('id', '?')} "
              f"profileId={prof_id}")
    return 0


_CONTENT_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                  ".gif": "image/gif", ".mp4": "video/mp4", ".webp": "image/webp"}


def cmd_upload(ns) -> int:
    """Presign + upload a local media file; prints the public URL for --image-url."""
    if not os.path.isfile(ns.file):
        print(f"error: file not found: {ns.file}", file=sys.stderr)
        return 2
    ext = os.path.splitext(ns.file)[1].lower()
    ctype = _CONTENT_TYPES.get(ext)
    if not ctype:
        print(f"error: unsupported media type {ext} (use png/jpg/gif/webp/mp4)", file=sys.stderr)
        return 2
    pre = _api("POST", "/media/presign",
               {"filename": os.path.basename(ns.file), "contentType": ctype})
    upload_url = pre.get("uploadUrl") or pre.get("presignedUrl") or pre.get("url")
    public_url = pre.get("publicUrl") or pre.get("public_url")
    if not upload_url:
        print(f"error: no presigned URL in response: {json.dumps(pre)[:300]}", file=sys.stderr)
        return 1
    with open(ns.file, "rb") as f:
        data = f.read()
    req = urllib.request.Request(upload_url, data=data,
                                 headers={"Content-Type": ctype}, method="PUT")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            if resp.status not in (200, 201, 204):
                print(f"error: upload HTTP {resp.status}", file=sys.stderr)
                return 1
    except urllib.error.HTTPError as e:
        print(f"error: upload failed HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:200]}", file=sys.stderr)
        return 1
    print(public_url or "(uploaded — no publicUrl in presign response)")
    return 0


def cmd_post(ns) -> int:
    try:
        payload = build_post_payload(ns.content, ns.platform, ns.account_id, ns.profile_id,
                                     ns.image_url, ns.schedule, ns.timezone)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    result = _api("POST", "/posts", payload)
    print(json.dumps(result))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("accounts", help="list connected social accounts")

    p = sub.add_parser("post", help="publish or schedule a post")
    p.add_argument("--content", required=True, help="final approved copy (verbatim)")
    p.add_argument("--platform", required=True, help="target platform (as reported by `accounts`)")
    p.add_argument("--account-id", required=True)
    p.add_argument("--profile-id", required=True)
    p.add_argument("--image-url", default=None, help="optional public image URL to attach")
    p.add_argument("--schedule", default=None, help="ISO datetime; omit to publish now")
    p.add_argument("--timezone", default=None, help="IANA tz for --schedule (default UTC)")

    sub.add_parser("usage", help="show plan usage stats")
    pu = sub.add_parser("upload", help="upload local media, prints public URL")
    pu.add_argument("--file", required=True)

    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()
    if ns.cmd == "accounts":
        return cmd_accounts()
    if ns.cmd == "post":
        return cmd_post(ns)
    if ns.cmd == "upload":
        return cmd_upload(ns)
    if ns.cmd == "usage":
        print(json.dumps(_api("GET", "/usage-stats")))
        return 0
    parser.print_help()
    return 2


def smoke() -> int:
    p = build_post_payload("hello", "x", "acc", "prof")
    assert p["publishNow"] is True and "scheduledFor" not in p and "mediaItems" not in p
    assert p["platforms"] == [{"platform": "x", "accountId": "acc"}] and p["profileId"] == "prof"
    p = build_post_payload("hello", "linkedin", "acc", "prof",
                           image_url="https://img", schedule="2026-07-13T09:00:00", timezone="Asia/Kolkata")
    assert p["publishNow"] is False and p["scheduledFor"] == "2026-07-13T09:00:00"
    assert p["timezone"] == "Asia/Kolkata" and p["mediaItems"] == [{"type": "image", "url": "https://img"}]
    p = build_post_payload("hi", "x", "acc", "prof", schedule="2026-07-13T09:00:00")
    assert p["timezone"] == "UTC"
    for bad in (("", "x", "a", "p"), ("hi", "x", "", "p"), ("hi", "x", "a", "")):
        try:
            build_post_payload(*bad)
            raise AssertionError("expected ValueError")
        except ValueError:
            pass
    print("zernio smoke OK (payload builder)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
