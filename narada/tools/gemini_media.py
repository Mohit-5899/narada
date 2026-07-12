#!/usr/bin/env python3
"""Brand media generation for Narada via the Gemini API.

  models                              list image/video models this key can use
  image --prompt "..." --out f.png    Nano Banana Pro (gemini-3-pro-image)
  video --prompt "..." --out f.mp4    Veo 3.1 fast (async, polls until done)

Env: GEMINI_API_KEY (required); GEMINI_IMAGE_MODEL / GEMINI_VIDEO_MODEL override
defaults. Exit codes: 0 ok, 1 API error, 2 usage/env.
Smoke (offline): python3 gemini_media.py --smoke
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = "https://generativelanguage.googleapis.com/v1beta"
IMAGE_MODEL = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image")
VIDEO_MODEL = os.environ.get("GEMINI_VIDEO_MODEL", "veo-3.1-fast-generate-preview")
POLL_SECONDS = 10
POLL_MAX = 60  # 10 minutes


def _key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        print("error: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(2)
    return key


def _call(path: str, payload: dict = None, method: str = None) -> dict:
    url = f"{BASE}{path}{'&' if '?' in path else '?'}key={_key()}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Content-Type": "application/json"},
        method=method or ("POST" if payload is not None else "GET"),
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"error: Gemini HTTP {e.code}: {e.read().decode('utf-8','replace')[:400]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"error: cannot reach Gemini API: {e.reason}", file=sys.stderr)
        sys.exit(1)


def build_image_payload(prompt: str) -> dict:
    if not prompt.strip():
        raise ValueError("empty prompt")
    return {"contents": [{"parts": [{"text": prompt}]}]}


def build_video_payload(prompt: str, aspect: str = "16:9") -> dict:
    if not prompt.strip():
        raise ValueError("empty prompt")
    return {"instances": [{"prompt": prompt}], "parameters": {"aspectRatio": aspect}}


def cmd_image(ns) -> int:
    data = _call(f"/models/{ns.model}:generateContent", build_image_payload(ns.prompt))
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        blob = part.get("inlineData") or part.get("inline_data")
        if blob and blob.get("data"):
            with open(ns.out, "wb") as f:
                f.write(base64.b64decode(blob["data"]))
            print(f"image saved: {ns.out} ({os.path.getsize(ns.out)} bytes, model={ns.model})")
            return 0
    print("error: no image in response (model returned text only?)", file=sys.stderr)
    sys.exit(1)


def cmd_video(ns) -> int:
    op = _call(f"/models/{ns.model}:predictLongRunning", build_video_payload(ns.prompt, ns.aspect))
    name = op.get("name")
    if not name:
        print(f"error: no operation returned: {json.dumps(op)[:300]}", file=sys.stderr)
        sys.exit(1)
    print(f"video generating (operation {name.split('/')[-1]}, model={ns.model})…")
    for _ in range(POLL_MAX):
        time.sleep(POLL_SECONDS)
        st = _call(f"/{name}")
        if st.get("done"):
            if st.get("error"):
                print(f"error: generation failed: {st['error'].get('message')}", file=sys.stderr)
                sys.exit(1)
            resp = st.get("response", {})
            vids = (resp.get("generateVideoResponse", {}).get("generatedSamples")
                    or resp.get("generatedVideos") or [])
            uri = None
            if vids:
                v = vids[0]
                uri = (v.get("video", {}) or {}).get("uri") or v.get("uri")
            if not uri:
                print(f"error: done but no video uri: {json.dumps(resp)[:300]}", file=sys.stderr)
                sys.exit(1)
            sep = "&" if "?" in uri else "?"
            with urllib.request.urlopen(f"{uri}{sep}key={_key()}", timeout=300) as r, open(ns.out, "wb") as f:
                f.write(r.read())
            print(f"video saved: {ns.out} ({os.path.getsize(ns.out)} bytes)")
            return 0
    print("error: timed out waiting for video (10 min)", file=sys.stderr)
    sys.exit(1)


def cmd_models() -> int:
    d = _call("/models?pageSize=50")
    for m in d.get("models", []):
        n = m["name"].replace("models/", "")
        if any(k in n for k in ("image", "veo", "banana", "imagen")):
            print(n)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--smoke", action="store_true")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("models", help="list usable image/video models")
    pi = sub.add_parser("image", help="generate a brand image")
    pi.add_argument("--prompt", required=True)
    pi.add_argument("--out", required=True)
    pi.add_argument("--model", default=IMAGE_MODEL)
    pv = sub.add_parser("video", help="generate a brand video (async)")
    pv.add_argument("--prompt", required=True)
    pv.add_argument("--out", required=True)
    pv.add_argument("--model", default=VIDEO_MODEL)
    pv.add_argument("--aspect", default="16:9", choices=["16:9", "9:16"])
    ns = p.parse_args(argv)
    if ns.smoke:
        return smoke()
    if ns.cmd == "models":
        return cmd_models()
    if ns.cmd == "image":
        return cmd_image(ns)
    if ns.cmd == "video":
        return cmd_video(ns)
    p.print_help()
    return 2


def smoke() -> int:
    assert build_image_payload("x") == {"contents": [{"parts": [{"text": "x"}]}]}
    v = build_video_payload("y", "9:16")
    assert v["instances"][0]["prompt"] == "y" and v["parameters"]["aspectRatio"] == "9:16"
    for bad in ("", "  "):
        try:
            build_image_payload(bad)
            raise AssertionError("empty prompt should raise")
        except ValueError:
            pass
    print("gemini_media smoke OK (payload builders)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
