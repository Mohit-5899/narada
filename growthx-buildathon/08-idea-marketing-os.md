# 08 · THE PLAN — Marketing OS on Hermes

**One-liner:** An AI marketing agency. A manager agent plans campaigns; specialist agents (researcher, copywriter, publisher, analyst) execute them on real surfaces — real X/LinkedIn posts, real emails, real landing pages. A non-engineer assigns work from Telegram or a web dashboard.

**Track: AI as Agency** (164 base + uncapped overflow). Hermes qualifies as **base harness** (its capabilities do the real work) — we can double-dip as coding partner too (keep session receipts).

## Why this wins: Hermes ships the rubric as features

| Rubric parameter | Hermes built-in we exploit | Where in code |
|---|---|---|
| Org structure (5x) | `delegate_task` with `role="orchestrator"`, `max_spawn_depth=2` → manager **spawns sub-specialists on the fly** = L5 "emergent org" | `tools/delegate_tool.py` (MAX_DEPTH, orchestrator_ok) |
| Handoffs & memory (2x) | MEMORY.md (business rules) + USER.md (user past) + session context (current task) = **exactly the three L5 memory layers** | `hermes_state.py`, memory tool |
| Management UI (1x) | Telegram gateway = non-eng control surface; skills define agent roles in plain markdown → volunteer creates a role in <10 min | `gateway/`, `skills/` |
| Eval & iteration (5x) | Background review fork already improves skills after complex tasks; we add a named eval set | `agent/background_review.py` |
| Real output (20x) | Terminal + browser tools post to real X/LinkedIn APIs, send real email, deploy real pages | `tools/` |

Nobody else in the room gets L5 org structure for a config flag. We know this codebase.

## Parameter-by-parameter target

| # | Parameter | Weight | Target | How |
|---|-----------|--------|--------|-----|
| 1 | Real output | 20x | **L5 + overflow** | Real surfaces only: post via X API, LinkedIn API, real Resend/Gmail email, deploy landing page to Cloudflare Pages. 3+ repeated runs logged. During judging: keep feeding it real tasks — **each completed task = +20 pts overflow** |
| 2 | Org structure | 5x | **L5** | Hermes config: `delegation.max_spawn_depth: 2`, orchestrator enabled. Manager plans per-request, spawns specialists, reviews outputs. Show a trace where a role (e.g. "meme-specialist") didn't exist at kickoff |
| 3 | Observability | 7x | **L4** | Trace tree from delegation logs: who called whom, tokens+cost per step, filter by agent. (L5 diff-view only if time permits — L4=21pts is the efficient stop) |
| 4 | Eval & iteration | 5x | **L3–L4** | 20 named marketing tasks with expected outcomes (brief→post quality checks). Run before/after prompt changes. L4 if we wire it into a script that gates changes |
| 5 | Handoffs & memory | 2x | **L5** | MEMORY.md holds brand rules ("never post before 9am", tone guide); USER.md holds the client; session = current campaign. Demo: second campaign remembers the first's results |
| 6 | Cost & latency | 1x | **L4** | Haiku/cheap model for specialists; single post task in 1–5 min at $0.10–0.50 |
| 7 | Management UI | 1x | **L4–L5** | Telegram = assign work in natural language. L5 test: volunteer writes a new SKILL.md role via chat in <10 min |

**Base target: ~80+20+21+15+8+3+3 ≈ 150/164** before overflow.

## Power-ups — all six, +150

| Partner | Integration in Marketing OS |
|---------|------------------------------|
| LinkUp | Researcher agent uses LinkUp live search for competitor/trend research (natural fit!) |
| ElevenLabs | Analyst agent delivers the daily campaign report as a voice briefing |
| Convex | Campaign state store (campaigns, tasks, results) + powers the dashboard |
| Cloudflare | Landing pages the publisher agent deploys + our own product page |
| Dodo | Live checkout: "Hire the agency — $9/mo" on our landing page |
| Wispr | Dictate 500+ words during the build (prompts, copy) — screenshot stats |

## Cross-track bonus (up to +50)
Publisher agent launches **our own product** as its first real campaign — meta-demo! The launch post drives visitors (5x bonus) + signups (12.5x bonus) to our landing page. Analytics: Datafast/Plausible with read-only access ready.

## 8-hour build schedule

| Hour | Work |
|------|------|
| 0–1 | Hermes setup: install, Telegram gateway, orchestrator config (`max_spawn_depth: 2`), model keys. Convex project + landing page skeleton |
| 1–3 | Core roles as skills: manager (campaign planner), researcher (LinkUp), copywriter, publisher (X/LinkedIn API + email), analyst. First end-to-end campaign on real surfaces |
| 3–4 | Memory layers: brand rules → MEMORY.md, client profile → USER.md. Observability: trace view (who-called-whom + cost per step) |
| 4–5 | Eval set (20 tasks). Management dashboard (Convex-backed). Dodo checkout on landing page |
| 5–6 | ElevenLabs voice briefing. Cloudflare deploy. Polish |
| 6–7 | **Proof collection**: 3+ repeated runs logged, launch our own product via the agency (cross-track), screenshot Wispr stats, verify all dashboards accessible read-only |
| 7–8 | Submission + demo prep. Rehearse the 2-min demo twice |

## The 2-min demo script
1. (0:00) Judge texts the agency on Telegram: "launch a campaign for X" — from their phone
2. (0:20) Live trace: manager plans, spawns researcher + copywriter + publisher; one draft bounced back for revision
3. (1:00) Real post appears on real X/LinkedIn; real email lands; landing page live on Cloudflare
4. (1:30) Voice briefing (ElevenLabs) summarizes results; dashboard shows cost per task
5. (1:50) Kicker: "Its first client was itself — here's the live signup count from its own launch campaign"

**Proof minute:** live Convex DB, live analytics, trace tree, 3 logged runs, Wispr screenshot, Dodo dashboard.

## Risks & cuts (if behind)
- Cut first: L5 observability diff-view (keep L4), automated eval CI (keep manual L3), voice briefing
- Never cut: real surfaces (L3 ceiling on sandboxes kills parameter 1), repeated-run logs, read-only dashboard access (verification requires it)
- X API access can be flaky — backup real surface: LinkedIn + email + a real Discord/Telegram channel post
