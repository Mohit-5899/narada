#!/usr/bin/env python3
"""Narada pre-deploy skill gate — static contract checks over the 6 SKILL.md files.

Free, offline, stdlib-only, runs in milliseconds. Run before every deploy:

  python3 narada/evals/check_skills.py           # PASS/FAIL table, exit 0/1
  python3 narada/evals/check_skills.py --smoke   # self-check the checker

What it catches: someone edits a SKILL.md and silently drops a load-bearing
rule (approval gate, 280-char limit, Veo 8s constraint, ...) or renames/removes
a tool the skill shells out to. It does NOT test agent behavior — that's
run_agent_evals.py (costs tokens).

Exit codes: 0 all skills pass, 1 any assertion failed, 2 setup problem.
"""

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS_DIR = HERE.parent / "skills"
TOOLS_DIR = HERE.parent / "tools"

# Per-skill contract: assertion name -> pattern (or list of patterns, all must
# match). Searched over the full SKILL.md text with IGNORECASE | DOTALL.
CONTRACTS = {
    "narada-manager": {
        "qa_gate_checklist": r"QA GATE.*- \[ \]",
        "aarrr_framework": r"\bAARRR\b",
        "bounce_protocol": r"bounce the draft back",
        "identity_resolution": r"Resolve identity.*get-business --telegram-user-id",
        "approval_gate": r"Approval gate.*NEVER publish",
    },
    "narada-researcher": {
        "word_cap_300": r"under ~?300 words",
        "never_raw_dumps": r"NEVER return raw dumps",
        "insight_brief_format": r"INSIGHTS.*AUDIENCE LANGUAGE.*HOOKS TO TRY.*SOURCES",
    },
    "narada-copywriter": {
        "ten_levers_table": [
            r"10 psychology levers",
            r"Social proof", r"Scarcity", r"Loss aversion", r"Reciprocity",
            r"Anchoring", r"Authority", r"Commitment", r"Liking",
            r"Mere-exposure", r"Cognitive fluency",
        ],
        "banned_vocabulary": r"BANNED vocabulary",
        "x_280_char_limit": r"X/Twitter\s*\|[^\n]*280",
    },
    "narada-creative": {
        "brand_colors_first": [r"Brand identity first", r"palette"],
        "platform_hard_limits_table": r"Platform HARD LIMITS",
        "veo_8s_constraint": r"~?8\s?s per generation",
        "zernio_upload_handoff": r"zernio(\.py\"?)? upload",
    },
    "narada-publisher": {
        "accounts_first": r"always list accounts first",
        "approval_before_publish": r"needs owner approval",
        "verbatim_copy_echo": r"final copy verbatim",
    },
    "narada-analyst": {
        "learnings_block": r"LEARNINGS FOR\s+CONTEXT_MD",
        "read_only_rule": r"Read-only:.*never publish",
    },
}

TOOL_REF_PATTERN = re.compile(r"NARADA_TOOLS_DIR/(\w+\.py)")
FLAGS = re.IGNORECASE | re.DOTALL


def check_frontmatter(text: str, skill_name: str) -> list:
    """Return list of failed assertion names for the YAML frontmatter."""
    fails = []
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return ["frontmatter_missing"]
    fm = m.group(1)
    for key in ("name", "description", "version"):
        if not re.search(rf"^{key}:\s*\S", fm, re.MULTILINE):
            fails.append(f"frontmatter_{key}")
    name_m = re.search(r"^name:\s*(\S+)", fm, re.MULTILINE)
    if name_m and name_m.group(1) != skill_name:
        fails.append("frontmatter_name_mismatch")
    return fails


def check_skill(skill_name: str) -> list:
    """Return list of failed assertion names for one skill (empty = PASS)."""
    path = SKILLS_DIR / skill_name / "SKILL.md"
    if not path.exists():
        return ["SKILL.md_missing"]
    text = path.read_text(encoding="utf-8")

    fails = check_frontmatter(text, skill_name)
    for assertion, patterns in CONTRACTS[skill_name].items():
        if isinstance(patterns, str):
            patterns = [patterns]
        if not all(re.search(p, text, FLAGS) for p in patterns):
            fails.append(assertion)
    for tool in sorted(set(TOOL_REF_PATTERN.findall(text))):
        if not (TOOLS_DIR / tool).exists():
            fails.append(f"tool_missing:{tool}")
    return fails


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--smoke", action="store_true", help="run offline self-checks and exit")
    ns = parser.parse_args(argv)
    if ns.smoke:
        return smoke()

    if not SKILLS_DIR.is_dir():
        print(f"error: {SKILLS_DIR} not found", file=sys.stderr)
        return 2

    header = f"{'skill':<22}{'result':<8}failed assertions"
    print(header)
    print("-" * max(len(header), 60))
    any_fail = False
    for skill_name in CONTRACTS:
        fails = check_skill(skill_name)
        result = "FAIL" if fails else "PASS"
        any_fail = any_fail or bool(fails)
        print(f"{skill_name:<22}{result:<8}{', '.join(fails) if fails else '-'}")
    print()
    if any_fail:
        print("FAIL — fix the skill(s) above before deploying.")
        return 1
    print("All 6 skill contracts intact.")
    return 0


def smoke() -> int:
    # Every regex compiles.
    for contract in CONTRACTS.values():
        for patterns in contract.values():
            for p in ([patterns] if isinstance(patterns, str) else patterns):
                re.compile(p, FLAGS)
    # A gutted skill file fails every contract assertion + frontmatter.
    fails = check_frontmatter("no frontmatter here", "narada-manager")
    assert fails == ["frontmatter_missing"], fails
    gutted = "---\nname: narada-manager\ndescription: x\nversion: 1.0.0\n---\nempty body"
    for skill_name, contract in CONTRACTS.items():
        for assertion, patterns in contract.items():
            pats = [patterns] if isinstance(patterns, str) else patterns
            assert not all(re.search(p, gutted, FLAGS) for p in pats), \
                f"{skill_name}.{assertion} matched an empty skill body"
    # Tool ref extraction works.
    refs = TOOL_REF_PATTERN.findall('python3 "$NARADA_TOOLS_DIR/zernio.py" post')
    assert refs == ["zernio.py"], refs
    print("check_skills smoke OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
