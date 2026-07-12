# PROJECT.md — NARADA (Marketing OS) · Living Build Doc

**Name:** Narada — the divine messenger, Hermes' Indian counterpart. Built on Hermes; the demo symmetry is the pitch.
**Tagline:** *"Every business has a story. Narada makes the three worlds hear it."*
**Naming system:** manager agent = Narada · specialists = his ganas · daily voice briefing = "Narada's news"

> The single source of truth for how we move. Update after every decision. Everything else in this folder is reference; this is the pointer.

**Status:** Ideation → flows locked for onboarding + surface split. Campaign loop next.
**Track:** AI as Agency (164 base + overflow) · Hermes as base harness (+ coding partner receipts)

---

## 1. Locked decisions ✅

| # | Decision | Why | Ref |
|---|----------|-----|-----|
| D1 | Track = AI as Agency | Hermes ships the rubric as features; strongest proof by 5 PM | [05](05-track-ai-as-agency.md) |
| D2 | Idea = Marketing OS (AI marketing agency for businesses) | Superset of 3 library ideas; full-function replacement | [08](08-idea-marketing-os.md) |
| D3 | Surface split: **Web UI = onboarding + payments + read-only dashboard · Telegram = operations** | UI satisfies live-URL rule + signup capture + proof minute; Telegram = free command center via Hermes gateway | this file §3 |
| D4 | Keep a read-only campaign dashboard page in UI | Proof minute + judges who skip Telegram still see it live | — |
| D5 | Convex = **cloud (convex.dev free tier)**, not self-hosted repo | Zero setup; power-up evidence = Convex dashboard; self-host burns an hour for 0 pts | get-convex/convex-backend = self-host fallback only |
| D6 | Observability = **L5 target** via Hermes' built-in Langfuse plugin (`plugins/observability/langfuse/`) + custom diff page + cron alert to Telegram | Agents product → trace IS the demo; delegation events already carry subagent_id/parent_id/depth | chat log |
| D7 | Evals = **L5 target**, closed-loop | SKILL.md roles in git (versioning free); failed runs auto-append to eval set; v1→v2 pass-rate chart | chat log |
| D8 | Auth = email magic-link, no password | Signup = verifiable email + first-use event (brief approval) | — |
| D9 | **No campaign workflow — general chat + Hermes main loop as orchestrator** | Fixed pipelines = L2 org structure; dynamic per-request planning = L4/L5. Mentor test: two different requests must produce different traces. We build only: (a) skills = manager brain + specialist role prompts (SKILL.md, git-versioned), (b) tools = publish_linkedin, send_email, post_telegram_channel, deploy_landing_page, convex_log. Two skill rules: approval gate before real publish; log every task to Convex | chat log |

## 2. Open problems 🔴 (solve before/at hour 0)

| # | Problem | Direction | Owner/when |
|---|---------|-----------|-----------|
| P1 | **Web↔Telegram identity link** | Deep link `t.me/<bot>?start=<token>`; token minted at onboarding, stored in Convex `businesses.link_token`; bot matches on /start → binds `telegram_user_id` to business | Design done, build hour 1 |
| ~~P2~~ | ~~Multi-user Telegram gateway~~ | **RESOLVED → D10 (CORRECTED)**: single profile, open bot — but unset `TELEGRAM_ALLOWED_USERS` **fails CLOSED** (verified: `gateway/authz_mixin.py:264` default-deny; fail-open removed in #24457/#34515). Must opt in explicitly: **`TELEGRAM_ALLOWED_USERS=*` or `GATEWAY_ALLOW_ALL_USERS=true`** (documented in narada/config + .env.example). Business identity per-message: telegram_user_id → Convex lookup | done ✅ |
| ~~P3~~ | ~~Campaign loop flow~~ | **RESOLVED → D9**: no workflow; general chat + main loop + skills + tools | done |
| P4 | Which real publish surfaces? X API flaky risk | Primary: LinkedIn + email (Resend) + Telegram channel; X if keys work | decide hour 1 |

## 2.5 Live infrastructure 🔌

| Service | Value |
|---------|-------|
| Convex deployment | `dev:agile-marlin-826` (US East, project "marketing-os", branch dev/mohit-mandawat) |
| Convex client URL | `https://agile-marlin-826.convex.cloud` → `VITE_CONVEX_URL` in narada-web |
| Convex HTTP Actions URL | `https://agile-marlin-826.convex.site` → base URL for `POST /api/agent` (backend convex_client.py points HERE, not .cloud) |

Integration steps (once UI worktree merges):
```bash
cd narada-web
npx convex login          # one-time browser auth
npx convex dev            # links to agile-marlin-826, pushes schema+functions, watches
# .env.local:  CONVEX_DEPLOYMENT=dev:agile-marlin-826
#              VITE_CONVEX_URL=https://agile-marlin-826.convex.cloud
```
Backend env: `CONVEX_SITE_URL=https://agile-marlin-826.convex.site` + `AGENT_SHARED_SECRET=<generate>` (same value in Convex env via `npx convex env set`).

## 3. Architecture (current)

```
User → Web UI (Cloudflare Pages)                    ← signups, Dodo checkout
         │  onboarding: name + URL (+logo/images)
         ▼
       Onboarding crew (Hermes delegate_task, parallel)
         Site Analyst · Market Researcher (LinkUp) · Brand Analyst
         │  → Brand Brief → user approves/edits (first-use event!)
         ▼
       Convex (cloud): businesses · brand_briefs · campaigns · tasks · eval_cases
         + Hermes memory: brand rules layer (L5 memory #3)
         ▼
       Deep link t.me/<bot>?start=<token>  →  Telegram = command center
         │  "launch a campaign for X"
         ▼
       Manager agent → spawns specialists (researcher/copywriter/publisher/analyst)
         → real surfaces (LinkedIn, email, Telegram channel, landing pages)
         → traces to Langfuse · alerts via cron → Telegram
         ▼
       Read-only dashboard page (Convex-powered) ← THE PROOF MINUTE SCREEN
```

## 4. Onboarding flow (locked)
1. **Capture** (30s): business name + website URL required; logo/images/one-liner optional. Email magic-link.
2. **Analyze** (60–90s, live progress shown): 3 parallel agents — site analyst, LinkUp researcher, brand analyst.
3. **Brand Brief** (aha): offering/audience/tone/competitors/colors + 5 ready campaign ideas → user edits → ✅ approves (= first-use event).
4. **Persist**: Convex rows + brand rules → Hermes memory.
5. **Handoff**: Telegram deep link + "fire your first campaign" (pre-filled idea).

Edge cases: no website → 3 chat questions fallback · unreachable site → partial brief, flagged · huge site → cap: home + about + pricing + 2 product pages · wrong analysis → edit step catches.

## 5. Rubric targets (running tally)

| Param | Weight | Target | Pts |
|-------|--------|--------|-----|
| Real output | 20x | L5 + overflow (+20/task during judging — keep 5–6 briefs queued) | 80+ |
| Org structure | 5x | L5 (`max_spawn_depth: 2`, orchestrator; show mid-task role spawn) | 20 |
| Observability | 7x | **L5** (Langfuse tree + diff page + fired alert + search) | 28 |
| Evals | 5x | **L5** (closed-loop, git-tagged versions, pass-rate chart) | 20 |
| Memory | 2x | L5 (session + client past + brand rules) | 8 |
| Cost/latency | 1x | L4 (cheap model for specialists) | 3 |
| Management UI | 1x | L4 (Telegram natural language; L5 volunteer test if time) | 3 |
| **Base** | | | **~162** |
| Power-ups | | LinkUp · ElevenLabs · Convex · Cloudflare · Dodo · Wispr | +150 |
| Cross-track | | self-launch campaign → visitors 5x, signups 12.5x | +30–50 |

## 6. Build order (8h — see [08](08-idea-marketing-os.md) for detail, this supersedes)

| Hr | Do |
|----|----|
| 0–1 | Hermes setup ([09](09-setup.md) checklist) · **P2 multi-user spike** · Convex project · orchestrator config |
| 1–3 | Onboarding: UI form → crew → Brand Brief → Convex → deep-link handoff (P1) · specialist skills (manager/researcher/copywriter/publisher/analyst) |
| 3–4 | Langfuse plugin on, verify trace tree · memory layers wired |
| 4–5 | Eval set (20 briefs) + closed-loop hook + v1 baseline · Dodo checkout · dashboard page |
| 5–6 | Diff page + cron alert · publish surfaces hardened |
| 6–7 | v2 eval run (chart the gain) · self-launch campaign (cross-track) · proof collection: 3+ logged runs, Wispr screenshot, read-only accesses |
| 7–8 | Submit at growthx.club/hermes-buildathon/submit · demo prep ([11](11-ship-and-demo.md)) · rehearse ×2 |

## 7. Pre-event checklist (TONIGHT)
- [ ] Claim perks — OpenAI org ID especially ([02](02-prizes.md))
- [ ] Hermes installed, Telegram answering ([09](09-setup.md) checklist)
- [ ] Read `multi-profile-gateways.md` (P2)
- [ ] Accounts ready: Convex, Cloudflare, Dodo, LinkUp, ElevenLabs, Wispr, Resend, Langfuse
- [ ] Analytics pick: Datafast or Plausible, read-only share link tested
- [ ] 5–6 real campaign briefs drafted (overflow ammo)

## 8. Decision log (append-only)
- 2026-07-12: D1–D8 locked during ideation with Claude. P1 design settled (deep-link token). P2 flagged for spike.
- 2026-07-12: D9 locked — no campaign workflow. General chat + Hermes main loop as orchestrator; skills carry the marketing brain, tools carry the hands. P3 closed.
- 2026-07-12: D10 locked — single profile + open Telegram bot; per-business context via Convex lookup by telegram_user_id. Multi-profile rejected for live signups. P2 closed (10-min verify at hour 0). Global MEMORY.md = agency-level rules only; brand rules per business in Convex.
- 2026-07-12: D11 — business model split: event day sells HOSTED service (Dodo $9/mo, no guide needed — we run the gateway). Self-host deployment guide = post-event week-1 work, open-core play (guide + skills free, hosted paid). Event-day version: 30-min repo README at hour 7 (architecture + run steps).
- 2026-07-12: D12 — name = NARADA. Tagline: "Every business has a story. Narada makes the three worlds hear it." TODO tonight: check handles (naradaos.com, getnarada.com, narada.marketing, @narada bot username on Telegram, X handle).
- 2026-07-12: D15 — two-layer memory: Hermes memory (MEMORY.md/SOUL.md/skill self-improvement) = NARADA's system self-memory — how the agency operates, learns, fixes itself; NOT per-business. Convex (brief + context_md + tasks) = per-business memory, loaded per message. Hermes background-review loop = the Marketing OS improving itself across stages.
- 2026-07-12: D14 — onboarding takes PDFs (≤3, Convex file storage, same upload path as images; `businesses.pdfs`). Agent context = `brand_briefs.context_md`: ONE markdown blob the onboarding crew distills from website+images+PDFs; manager loads it per turn via get-business. NO Vercel/extra vendor — Convex is the single storage brain (1 GiB free). Backend deployed; UI file input lands after design-agent harvest.
- 2026-07-12: D13 — auth switched to email+password (Convex Auth Password provider, name captured at signup; guest/Anonymous kept for demos). Supersedes D8 magic link — user wants classic sign-up-once/sign-in-after; Resend key stays set but unused by auth.
- 2026-07-12: MVP harvested from both worktree agents → committed d6c61a9. D10 CORRECTED: open bot needs explicit `TELEGRAM_ALLOWED_USERS=*` (gateway fails closed by default). Known gaps from agent reports: (1) Convex-side /api/agent dispatcher exists in narada-web but convex_client.py fn-contract must be verified against it hour 1; (2) npm install + smoke tests never ran (sandbox denied) — first thing to verify; (3) LinkedIn tool is honest stub (P4); (4) NARADA_TOOLS_DIR must be absolute + exported to gateway process; (5) manager skill must pass brand brief into every delegate_task (children don't inherit context).
- 2026-07-12: D16 — bot stays OPEN (`TELEGRAM_ALLOWED_USERS=*`) as the product through the event; close/restrict + rotate all chat-pasted keys (Resend, bot token, Anthropic, Gemini, Zernio, LinkUp, Langfuse) AFTER the event. Anthropic spend limit recommended meanwhile.
- 2026-07-12: D17 — PERFORMANCE SLO: basic task ≤10s, complex interactive task ≤60s (background pipelines like onboarding cron exempt — user is not waiting). Levers applied: SOUL speed rules (identity cached/session, zero-tool greetings), space-free NARADA_TOOLS_DIR symlink (killed silent retries), ganas on claude-haiku-4-5 (manager stays sonnet-5). Scoreboard = Langfuse latency per trace.
- 2026-07-12: D17 — PERFORMANCE SLO: basic ≤10s, complex interactive ≤60s (background cron pipelines exempt). Levers: SOUL speed rules, space-free tools symlink, ganas on claude-haiku-4-5 fallback (manager stays claude-sonnet-5). Scoreboard = Langfuse latency.
- 2026-07-12 (evening): ElevenLabs key → gateway env (Hermes built-in tts_tool reads ELEVENLABS_API_KEY — zero code). Dodo: product pdt_0Nj13OjtcRdHTFRSEX287 ($9/mo Narada Hosted, TEST mode) + live checkout page deployed. Pitch deck growthx-buildathon/narada-deck.html. Binding bug fixed (space-path broke original /start bind; bound directly + SOUL cache-exception). Eval --live baseline + langfuse_ops diff/alert in flight.
