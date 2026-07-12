#!/usr/bin/env python3
"""Deploy a landing page: write HTML into a pages dir, optionally publish via
Cloudflare `wrangler pages deploy`.

The wrangler call is gated behind NARADA_WRANGLER_DEPLOY=true so the tool is
honest without Cloudflare credentials: by default it ONLY writes the file and
says so — it never claims a live URL it didn't create.

Env: NARADA_PAGES_DIR (default ./narada-pages), NARADA_WRANGLER_DEPLOY
     (true/false, default false), NARADA_PAGES_PROJECT (wrangler project name,
     required when deploying).

Usage:
  python3 deploy_landing_page.py --slug spring-sale --html-file /tmp/page.html

Exit codes: 0 ok, 1 wrangler failed, 2 bad usage/env.
Smoke test (offline, writes to a temp dir): python3 deploy_landing_page.py --smoke
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


def write_page(pages_dir: Path, slug: str, html: str) -> Path:
    """Validate inputs and write <pages_dir>/<slug>/index.html."""
    if not SLUG_RE.match(slug):
        raise ValueError(f"invalid slug {slug!r}: lowercase letters, digits, hyphens only")
    if "<html" not in html.lower():
        raise ValueError("html file does not look like a full HTML document (no <html tag)")
    out_dir = pages_dir / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"
    out_file.write_text(html, encoding="utf-8")
    return out_file


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    parser.add_argument("--slug", help="url path segment, e.g. spring-sale")
    parser.add_argument("--html-file", help="full HTML document to deploy")
    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()
    if not ns.slug or not ns.html_file:
        print("error: --slug and --html-file are required", file=sys.stderr)
        return 2

    pages_dir = Path(os.environ.get("NARADA_PAGES_DIR", "./narada-pages")).expanduser()
    with open(ns.html_file, "r", encoding="utf-8") as f:
        html = f.read()
    try:
        out_file = write_page(pages_dir, ns.slug, html)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"wrote {out_file}")

    deploy_flag = os.environ.get("NARADA_WRANGLER_DEPLOY", "").strip().lower() in {"true", "1", "yes"}
    if not deploy_flag:
        # ponytail: honest stub — file written, nothing is live yet.
        print("NOT DEPLOYED: NARADA_WRANGLER_DEPLOY is not 'true'. Page exists only on disk.")
        return 0

    project = os.environ.get("NARADA_PAGES_PROJECT", "").strip()
    if not project:
        print("error: NARADA_WRANGLER_DEPLOY=true but NARADA_PAGES_PROJECT unset", file=sys.stderr)
        return 2
    if shutil.which("wrangler") is None:
        print("error: wrangler CLI not found on PATH (npm i -g wrangler)", file=sys.stderr)
        return 2

    cmd = ["wrangler", "pages", "deploy", str(pages_dir), "--project-name", project]
    print(f"running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode != 0:
        print(f"error: wrangler exited {result.returncode}", file=sys.stderr)
        return 1
    return 0


def smoke() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        out = write_page(Path(td), "test-page", "<html><body><h1>Hi</h1></body></html>")
        assert out.exists() and out.read_text().startswith("<html")
        for bad in ("Bad Slug!", "-lead", ""):
            try:
                write_page(Path(td), bad, "<html></html>")
                raise AssertionError("expected ValueError")
            except ValueError:
                pass
        try:
            write_page(Path(td), "ok", "not html")
            raise AssertionError("expected ValueError for non-HTML")
        except ValueError:
            pass
    print("deploy_landing_page smoke OK (write_page)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
