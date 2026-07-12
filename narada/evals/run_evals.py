#!/usr/bin/env python3
"""Narada eval runner — programmatic checks over generated marketing copy.

Layout:
  eval_set.jsonl                cases (brief + business_context + expected)
  outputs/<version>/<id>.txt    model output per case, one dir per version
                                (version = git tag or any label, e.g. v1, v2)

Checks (programmatic where possible; honest about the rest):
  has_cta             CTA verb or URL present
  banned_words_absent none of business_context.banned_words appear
  platform_format     length caps + hashtag caps + email subject line rules
  respects_tone       NOT machine-checkable -> reported as MANUAL, excluded
                      from the pass rate (LLM-judge is a later upgrade).

Usage:
  python3 run_evals.py                 # score every version dir, print table
  python3 run_evals.py --version v1    # score one version
  python3 run_evals.py --smoke         # offline self-checks

Exit codes: 0 ran, 2 setup problem (missing outputs/eval set).
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL_SET = HERE / "eval_set.jsonl"
OUTPUTS_DIR = HERE / "outputs"

CTA_PATTERN = re.compile(
    r"(https?://|\b(sign up|signup|book|reply|order|join|subscribe|register|"
    r"download|get started|try|visit|claim|dm us|apply|vote|pre-?order|"
    r"start (your|the)|grab|reserve)\b)",
    re.IGNORECASE,
)
HASHTAG_PATTERN = re.compile(r"(?<!&)#\w+")

# platform -> (max_chars, max_hashtags or None)
PLATFORM_LIMITS = {
    "telegram_channel": (800, None),
    "linkedin": (1300, 3),
    "x": (280, 2),
    "email": (None, None),        # checked via subject rule instead
    "landing_page": (None, None), # checked via H1 rule instead
}


def check_case(case: dict, text: str) -> dict:
    """Return {check_name: True/False/'MANUAL'} for one output."""
    platform = case["platform"]
    banned = case.get("business_context", {}).get("banned_words", [])
    results = {}

    results["has_cta"] = bool(CTA_PATTERN.search(text))

    lowered = text.lower()
    results["banned_words_absent"] = not any(w.lower() in lowered for w in banned)

    ok = True
    max_chars, max_tags = PLATFORM_LIMITS.get(platform, (None, None))
    if max_chars is not None and len(text) > max_chars:
        ok = False
    if max_tags is not None and len(HASHTAG_PATTERN.findall(text)) > max_tags:
        ok = False
    if platform == "email":
        # Convention: first line is "Subject: ..." — required, <= 55 chars.
        first = text.strip().splitlines()[0] if text.strip() else ""
        m = re.match(r"^subject:\s*(.+)$", first, re.IGNORECASE)
        ok = bool(m) and len(m.group(1)) <= 55
    if platform == "landing_page":
        # Must contain exactly one H1 (markdown '# ' or <h1>).
        h1s = len(re.findall(r"(?m)^# [^\n]+$", text)) + len(re.findall(r"<h1[ >]", text, re.IGNORECASE))
        ok = h1s == 1
    results["platform_format"] = ok

    results["respects_tone"] = "MANUAL"
    return results


def load_cases() -> list:
    if not EVAL_SET.exists():
        print(f"error: {EVAL_SET} not found", file=sys.stderr)
        sys.exit(2)
    cases = []
    for i, line in enumerate(EVAL_SET.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            cases.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"error: eval_set.jsonl line {i} is invalid JSON: {e}", file=sys.stderr)
            sys.exit(2)
    return cases


def git_label() -> str:
    try:
        out = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=HERE, capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def score_version(version_dir: Path, cases: list) -> dict:
    """Return {'version', 'per_check': {check: (pass, total)}, 'missing': n, 'cases': {...}}."""
    per_check: dict = {}
    case_rows = {}
    missing = 0
    for case in cases:
        out_file = version_dir / f"{case['id']}.txt"
        if not out_file.exists():
            missing += 1
            case_rows[case["id"]] = None
            continue
        results = check_case(case, out_file.read_text(encoding="utf-8"))
        case_rows[case["id"]] = results
        for name, val in results.items():
            if val == "MANUAL":
                continue
            passed, total = per_check.get(name, (0, 0))
            per_check[name] = (passed + (1 if val else 0), total + 1)
    return {"version": version_dir.name, "per_check": per_check, "missing": missing, "cases": case_rows}


def print_table(scores: list, n_cases: int) -> None:
    checks = ["has_cta", "banned_words_absent", "platform_format"]
    header = f"{'version':<16}" + "".join(f"{c:<22}" for c in checks) + f"{'overall':<10}{'missing':<8}"
    print(f"\ngit: {git_label()}   cases: {n_cases}   (respects_tone: MANUAL — not scored)")
    print(header)
    print("-" * len(header))
    for s in scores:
        row = f"{s['version']:<16}"
        total_pass = total_all = 0
        for c in checks:
            passed, total = s["per_check"].get(c, (0, 0))
            total_pass += passed
            total_all += total
            cell = f"{passed}/{total} ({(100 * passed / total):.0f}%)" if total else "n/a"
            row += f"{cell:<22}"
        overall = f"{(100 * total_pass / total_all):.0f}%" if total_all else "n/a"
        row += f"{overall:<10}{s['missing']:<8}"
        print(row)
    print()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    parser.add_argument("--version", help="score only outputs/<version>")
    parser.add_argument("--details", action="store_true", help="print per-case failures")
    ns = parser.parse_args(argv)

    if ns.smoke:
        return smoke()

    cases = load_cases()
    if not OUTPUTS_DIR.is_dir():
        print(
            f"error: {OUTPUTS_DIR} does not exist yet.\n"
            "Generate outputs first: for each case in eval_set.jsonl, save the\n"
            "model's copy to outputs/<version>/<id>.txt (version = git tag/label).",
            file=sys.stderr,
        )
        return 2

    version_dirs = (
        [OUTPUTS_DIR / ns.version] if ns.version
        else sorted(d for d in OUTPUTS_DIR.iterdir() if d.is_dir())
    )
    version_dirs = [d for d in version_dirs if d.is_dir()]
    if not version_dirs:
        print("error: no version dirs found under outputs/", file=sys.stderr)
        return 2

    scores = [score_version(d, cases) for d in version_dirs]
    print_table(scores, len(cases))

    if ns.details:
        for s in scores:
            for cid, results in s["cases"].items():
                if results is None:
                    print(f"[{s['version']}] {cid}: MISSING OUTPUT")
                    continue
                fails = [k for k, v in results.items() if v is False]
                if fails:
                    print(f"[{s['version']}] {cid}: FAIL {', '.join(fails)}")
    return 0


def smoke() -> int:
    case = {
        "id": "t1", "platform": "linkedin",
        "business_context": {"banned_words": ["synergy"]},
        "expected": {},
    }
    good = "We cut invoice time by 40%.\n\nHere's how.\n\nTry it: https://x.co\n\n#invoicing"
    r = check_case(case, good)
    assert r["has_cta"] and r["banned_words_absent"] and r["platform_format"], r
    bad = ("Synergy! " * 200) + " #a #b #c #d"
    r = check_case(case, bad)
    assert not r["banned_words_absent"] and not r["platform_format"], r

    email_case = {"id": "t2", "platform": "email", "business_context": {"banned_words": []}}
    r = check_case(email_case, "Subject: Your first ledger in 5 minutes\n\nImport now: https://x.co")
    assert r["platform_format"] and r["has_cta"], r
    r = check_case(email_case, "No subject line here, just body text with https://x.co")
    assert not r["platform_format"], r

    lp_case = {"id": "t3", "platform": "landing_page", "business_context": {"banned_words": []}}
    r = check_case(lp_case, "# One promise\n\nSign up today")
    assert r["platform_format"], r
    r = check_case(lp_case, "# One\n\n# Two\n\nSign up")
    assert not r["platform_format"], r

    x_case = {"id": "t4", "platform": "x", "business_context": {"banned_words": []}}
    r = check_case(x_case, "Lifting won't make you bulky. Book a free class: https://x.co")
    assert r["platform_format"], r
    r = check_case(x_case, "x" * 281)
    assert not r["platform_format"], r

    assert check_case(case, "no call to action here at all")["has_cta"] is False
    print("run_evals smoke OK (all check paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
