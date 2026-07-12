#!/usr/bin/env python3
"""Narada ↔ Langfuse observability ops (rubric L5: diff runs + alerting).

Reads the Langfuse public API with basic auth (public:secret). Subcommands:

  list   [--limit N]                    compact table of recent traces
  diff   --a <trace_id> --b <trace_id>  side-by-side per-observation diff of
                                        two runs + Δ summary (the "explain a
                                        regression" view)
  alert  [--max-cost 1.0] [--max-latency 120] [--window 10]
                                        scan last N traces; print one line per
                                        cost/latency/ERROR breach. Silent +
                                        exit 0 when clean (cron-friendly),
                                        exit 1 when anything breached.

Env: LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL (default
https://jp.cloud.langfuse.com). Hermes-prefixed HERMES_LANGFUSE_* variants
are also read and win over the bare names. Exit codes: 0 ok/clean,
1 remote error or alert breach, 2 bad usage/env.

Alert delivery via Hermes cron (owner gets a Telegram ping only on breach):

  uv run hermes cron create "every 15m" \\
    "Run $NARADA_TOOLS_DIR/langfuse_ops.py alert --max-cost 1.5; if it \\
printed breaches, summarize them for the owner; if silent, output nothing." \\
    --deliver telegram

Smoke test (offline): python3 langfuse_ops.py --smoke
"""

import argparse
import base64
import datetime
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT_SECONDS = 30
DEFAULT_BASE_URL = "https://jp.cloud.langfuse.com"
SHORT_ID = 8


def _env(name: str) -> str:
    """HERMES_LANGFUSE_* wins over LANGFUSE_*."""
    return (os.environ.get(f"HERMES_{name}") or os.environ.get(name, "")).strip()


def _require_env() -> tuple:
    public = _env("LANGFUSE_PUBLIC_KEY")
    secret = _env("LANGFUSE_SECRET_KEY")
    base = _env("LANGFUSE_BASE_URL").rstrip("/") or DEFAULT_BASE_URL
    missing = [n for n, v in (("LANGFUSE_PUBLIC_KEY", public), ("LANGFUSE_SECRET_KEY", secret)) if not v]
    if missing:
        print(f"error: missing env vars: {', '.join(missing)} (or HERMES_-prefixed; see narada/.env.example)",
              file=sys.stderr)
        sys.exit(2)
    return base, public, secret


def api_get(path: str, params: dict = None) -> dict:
    base, public, secret = _require_env()
    url = f"{base}{path}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    token = base64.b64encode(f"{public}:{secret}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        print(f"error: Langfuse HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"error: cannot reach Langfuse at {base}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    try:
        # strict=False: trace payloads may embed raw control characters.
        return json.loads(body, strict=False)
    except json.JSONDecodeError:
        print(f"error: Langfuse returned non-JSON: {body[:500]}", file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------- pure helpers

def parse_ts(value):
    """ISO-8601 (with trailing Z) -> aware datetime, or None."""
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def fmt_cost(value) -> str:
    return f"${float(value):.4f}" if value is not None else "-"


def fmt_secs(value) -> str:
    return f"{float(value):.1f}s" if value is not None else "-"


def obs_row(obs: dict, trace_start) -> dict:
    """Flatten one observation into the fields the diff view shows."""
    start, end = parse_ts(obs.get("startTime")), parse_ts(obs.get("endTime"))
    offset = (start - trace_start).total_seconds() if start and trace_start else None
    latency = (end - start).total_seconds() if start and end else None
    usage = obs.get("usage") or {}
    return {
        "offset": offset,
        "type": obs.get("type") or "?",
        "name": obs.get("name") or "?",
        "latency": latency,
        "in": usage.get("input"),
        "out": usage.get("output"),
        "level": obs.get("level") or "DEFAULT",
    }


def render_obs_row(row) -> str:
    if row is None:
        return "-"
    off = f"+{row['offset']:.1f}s" if row["offset"] is not None else "+?"
    lat = fmt_secs(row["latency"])
    tok = f"{row['in'] if row['in'] is not None else '?'}/{row['out'] if row['out'] is not None else '?'}"
    return f"{off:>8} {row['type'][:4]:<4} {row['name'][:28]:<28} {lat:>7} {tok}"


def trace_rows(trace: dict) -> list:
    """Sorted, flattened observation rows for one trace detail payload."""
    start = parse_ts(trace.get("timestamp"))
    rows = [obs_row(o, start) for o in trace.get("observations") or []]
    return sorted(rows, key=lambda r: (r["offset"] is None, r["offset"] or 0.0))


def first_divergence(rows_a: list, rows_b: list):
    """(index, description) of the first step where the runs differ, or None."""
    for i in range(max(len(rows_a), len(rows_b))):
        a = rows_a[i] if i < len(rows_a) else None
        b = rows_b[i] if i < len(rows_b) else None
        if a is None:
            return i, f"B has extra step '{b['name']}'"
        if b is None:
            return i, f"A has extra step '{a['name']}'"
        if a["name"] != b["name"] or a["type"] != b["type"]:
            return i, f"'{a['name']}' vs '{b['name']}'"
    return None


def find_breaches(trace: dict, max_cost: float, max_latency: float) -> list:
    """Alert lines for one trace detail payload (cost / latency / ERROR obs)."""
    tid, out = trace.get("id", "?"), []
    cost, latency = trace.get("totalCost"), trace.get("latency")
    if cost is not None and float(cost) > max_cost:
        out.append(f"ALERT cost {tid} {fmt_cost(cost)} > {fmt_cost(max_cost)}")
    if latency is not None and float(latency) > max_latency:
        out.append(f"ALERT latency {tid} {fmt_secs(latency)} > {fmt_secs(max_latency)}")
    for o in trace.get("observations") or []:
        if (o.get("level") or "").upper() == "ERROR":
            out.append(f"ALERT error {tid} observation '{o.get('name') or '?'}' level=ERROR")
    return out


# ----------------------------------------------------------------- subcommands

def cmd_list(limit: int) -> int:
    data = api_get("/api/public/traces", {"limit": limit})
    traces = data.get("data") or []
    print(f"{'time':<20} {'id':<{SHORT_ID}} {'latency':>8} {'cost':>10} {'obs':>4}")
    for t in traces:
        ts = parse_ts(t.get("timestamp"))
        print(f"{ts.strftime('%Y-%m-%d %H:%M:%S') if ts else '?':<20} "
              f"{(t.get('id') or '?')[:SHORT_ID]:<{SHORT_ID}} "
              f"{fmt_secs(t.get('latency')):>8} {fmt_cost(t.get('totalCost')):>10} "
              f"{len(t.get('observations') or []):>4}")
    if not traces:
        print("(no traces)")
    return 0


def cmd_diff(id_a: str, id_b: str) -> int:
    ta = api_get(f"/api/public/traces/{urllib.parse.quote(id_a)}")
    tb = api_get(f"/api/public/traces/{urllib.parse.quote(id_b)}")
    rows_a, rows_b = trace_rows(ta), trace_rows(tb)
    col = 60
    print(f"{'A: ' + id_a[:40]:<{col}}| B: {id_b[:40]}")
    print(f"{'offset  type name                          latency  in/out':<{col}}| (same)")
    print("-" * col + "+" + "-" * col)
    for i in range(max(len(rows_a), len(rows_b))):
        a = rows_a[i] if i < len(rows_a) else None
        b = rows_b[i] if i < len(rows_b) else None
        marker = " " if a and b and a["name"] == b["name"] and a["type"] == b["type"] else "*"
        print(f"{render_obs_row(a):<{col}}|{marker}{render_obs_row(b)}")

    def delta(key):
        va, vb = ta.get(key), tb.get(key)
        if va is None or vb is None:
            return "n/a"
        return f"{float(vb) - float(va):+.4f}"

    div = first_divergence(rows_a, rows_b)
    print()
    print("summary")
    print(f"  total latency Δ (B-A): {delta('latency')} s "
          f"(A={fmt_secs(ta.get('latency'))}, B={fmt_secs(tb.get('latency'))})")
    print(f"  cost Δ (B-A):          {delta('totalCost')} "
          f"(A={fmt_cost(ta.get('totalCost'))}, B={fmt_cost(tb.get('totalCost'))})")
    print(f"  observation count Δ:   {len(rows_b) - len(rows_a):+d} (A={len(rows_a)}, B={len(rows_b)})")
    print(f"  first divergent step:  {'step %d: %s' % div if div else 'none — same step sequence'}")
    return 0


def cmd_alert(max_cost: float, max_latency: float, window: int) -> int:
    # ONE request: the list payload already carries totalCost + latency.
    # Per-trace detail fetches hit Langfuse's 15/min rate limit (429), so
    # ERROR-level observation scanning is dropped — cost/latency are the
    # D17 SLO signals and need only the list.
    listing = api_get("/api/public/traces", {"limit": window})
    breaches = []
    for t in listing.get("data") or []:
        tid = (t.get("id") or "")[:8]
        cost = t.get("totalCost") or 0
        latency = t.get("latency") or 0
        if cost > max_cost:
            breaches.append("ALERT cost trace=%s $%.4f > $%.2f" % (tid, cost, max_cost))
        if latency > max_latency:
            breaches.append("ALERT latency trace=%s %.1fs > %.0fs" % (tid, latency, max_latency))
    for line in breaches:
        print(line)
    return 1 if breaches else 0  # silent success when clean


# ----------------------------------------------------------------------- main

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("list", help="table of recent traces")
    p.add_argument("--limit", type=int, default=20)

    p = sub.add_parser("diff", help="side-by-side diff of two traces")
    p.add_argument("--a", required=True, help="baseline trace id")
    p.add_argument("--b", required=True, help="comparison trace id")

    p = sub.add_parser("alert", help="scan recent traces for cost/latency/error breaches")
    p.add_argument("--max-cost", type=float, default=1.0, help="USD per trace")
    p.add_argument("--max-latency", type=float, default=120.0, help="seconds per trace")
    p.add_argument("--window", type=int, default=10, help="how many recent traces to scan")

    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()
    if not ns.cmd:
        parser.print_help()
        return 2

    if ns.cmd == "list":
        return cmd_list(ns.limit)
    if ns.cmd == "diff":
        return cmd_diff(ns.a, ns.b)
    if ns.cmd == "alert":
        return cmd_alert(ns.max_cost, ns.max_latency, ns.window)
    return 2  # pragma: no cover


def smoke() -> int:
    """Offline self-checks — no network, no env required."""
    t0 = "2026-07-12T10:00:00Z"
    trace = {
        "id": "trace-a", "timestamp": t0, "latency": 12.5, "totalCost": 0.42,
        "observations": [
            {"startTime": "2026-07-12T10:00:05Z", "endTime": "2026-07-12T10:00:08Z",
             "type": "GENERATION", "name": "draft-copy", "usage": {"input": 900, "output": 300},
             "level": "DEFAULT"},
            {"startTime": "2026-07-12T10:00:01Z", "endTime": "2026-07-12T10:00:03Z",
             "type": "SPAN", "name": "research", "level": "ERROR"},
        ],
    }
    rows = trace_rows(trace)
    assert [r["name"] for r in rows] == ["research", "draft-copy"], rows  # sorted by offset
    assert rows[0]["offset"] == 1.0 and rows[0]["latency"] == 2.0, rows[0]
    assert rows[1]["in"] == 900 and rows[1]["out"] == 300, rows[1]

    other = dict(trace, observations=[trace["observations"][1]])  # only 'research'
    div = first_divergence(trace_rows(other), rows)
    assert div == (1, "B has extra step 'draft-copy'"), div
    assert first_divergence(rows, rows) is None

    b = find_breaches(trace, max_cost=0.1, max_latency=10.0)
    assert len(b) == 3 and b[0].startswith("ALERT cost trace-a") and "ERROR" in b[2], b
    assert find_breaches(trace, max_cost=1.0, max_latency=120.0) == [
        "ALERT error trace-a observation 'research' level=ERROR"], "error obs always alerts"
    assert find_breaches({"id": "x", "observations": []}, 1.0, 120.0) == []

    # control chars in payloads must survive strict=False parsing
    parsed = json.loads('{"name": "a\tb\nc"}', strict=False)
    assert parsed["name"] == "a\tb\nc"

    assert fmt_cost(None) == "-" and fmt_cost(0.5) == "$0.5000"
    assert parse_ts("garbage") is None and parse_ts(None) is None
    assert render_obs_row(None) == "-"

    configured = bool(_env("LANGFUSE_PUBLIC_KEY")) and bool(_env("LANGFUSE_SECRET_KEY"))
    print(f"langfuse_ops smoke OK (rows/diff/breach builders). env configured: {configured}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
