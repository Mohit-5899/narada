# CLAUDE.md — Narada Build Guide

> **Narada** — an AI marketing agency built on Hermes for the GrowthX × Hermes Buildathon.
> *"Every business has a story. Narada makes the three worlds hear it."*
> Track: **AI as Agency**. Repo: fork of NousResearch/hermes-agent (upstream `@4281151ae`, MIT preserved).

**Note on file precedence:** the Hermes *runtime* reads `.hermes.md` → `AGENTS.md` → `CLAUDE.md` (first found wins) — so this file is **never** seen by the Hermes agent (`AGENTS.md` wins). This file is for **Claude Code only**: it defines how we build, not how the agent behaves.

## Your role

You are the build partner for this hackathon. The source of truth for every decision is **`growthx-buildathon/project.md`** (decisions D1–D12, open problems, rubric targets, build order). When we make a new decision, append it to that file's decision log. Never silently contradict a locked decision — flag it, discuss, then update the log.

## Architecture — the four zones

| Zone | What | Touch policy |
|------|------|--------------|
| `narada-web/` | Vite+React+TS UI + Convex backend (schema, auth, `/api/agent` endpoint, dashboard) | ours — edit freely |
| `narada/` | Agent layer: skills (manager + researcher/copywriter/publisher/analyst), tools (5 Python scripts), evals, Hermes config snippet | ours — edit freely |
| `growthx-buildathon/` | War-room docs, rubrics, **project.md** (living build doc) | ours — keep current |
| Everything else | **Stock Hermes — DO NOT MODIFY.** We extend only via skills, tools, and config (`narada/config/hermes-config-snippet.yaml`) | read-only |

## Live infrastructure

- **Convex:** deployment `dev:agile-marlin-826` (project "marketing-os")
  - Browser/client URL: `https://agile-marlin-826.convex.cloud` (`VITE_CONVEX_URL`)
  - HTTP Actions URL: `https://agile-marlin-826.convex.site` — the Python tools POST here (`CONVEX_URL`), **not** `.cloud`
  - Deployment env vars set: `AGENT_SHARED_SECRET`, `AUTH_RESEND_KEY`, `JWT_PRIVATE_KEY`, `JWKS`, `SITE_URL`
  - ⚠️ The Resend key was pasted in chat once — rotate it after the event
- **GitHub:** `Mohit-5899/narada` (public, `main`)
- **Telegram bot:** **@NaradaMarketingbot** (display name "Narada", created via BotFather). Token lives in `narada/.env.local` (`TELEGRAM_BOT_TOKEN`) — never in git or chat. Open bot requires explicit `TELEGRAM_ALLOWED_USERS=*` — Hermes gateway **fails closed** by default (verified: `gateway/authz_mixin.py:264`)

## Commands

```bash
# UI dev server
cd narada-web && npm run dev                  # http://localhost:5173

# Push Convex schema/functions after editing convex/
cd narada-web && npx convex dev --once

# Offline smoke tests (run after ANY tool edit)
for t in narada/tools/*.py narada/evals/run_evals.py; do python3 "$t" --smoke; done

# Production build check
cd narada-web && npm run build

# Live wire test (client → real deployment)
CONVEX_URL=https://agile-marlin-826.convex.site CONVEX_AGENT_SECRET=<secret> \
  python3 narada/tools/convex_client.py get-business --telegram-user-id 999
```

## Working principles

1. **Never touch Hermes core.** Extension points only: skills dir, tools as standalone scripts, config snippet.
2. **One contract.** The `/api/agent` wire shape is defined in `narada-web/convex/http.ts` — it is the single source of truth. `narada/tools/convex_client.py` follows it (`x-agent-secret` header, `type`-dispatched flat payloads). Change the contract in http.ts first, client second, redeploy, wire-test.
3. **Small steps, verified steps.** Build one feature → manually verify it (checklist below) → commit → next. Never stack a second unverified feature on a first.
4. **Real surfaces only** for publishing (sandbox output caps rubric parameter 1 at L3). Stubs must be honest: exit non-zero with a clear message, never fake success.
5. **Log everything.** Every completed agent task → `convex_client.py log-task` → appears on the dashboard. The dashboard is the judge-facing proof screen; an unlogged task is an unscored task.
6. **Commit style:** conventional commits (`feat:`, `fix:`, `docs:`), small and topical. Push to `main`.

## Manual verification checklist (run before calling any feature "done")

| Feature | Hand-check | Expected |
|---------|-----------|----------|
| Auth (guest) | Landing → "Continue as guest" | Lands on `/start` onboarding, no error |
| Auth (magic link) | Enter email → send | Email arrives via Resend; link signs in |
| Onboarding | Submit a real business | Row in Convex `businesses` table; `brand_briefs` row status `analyzing`; 3 agent cards render |
| Brief pipe | POST `/api/agent` `type=brief, status=ready` with the business's `link_token` | Analyzing screen flips to editable brief **without refresh** (Convex reactivity) |
| Brief approval | Edit a field, click "✅ That's us" | `approved_at` set; Telegram handoff screen shows |
| Telegram handoff | Inspect the deep link | URL is `t.me/<bot>?start=<link_token>` with the real token |
| Dashboard | `convex_client.py log-task ...` for the business | Task appears under "General" campaign live, no refresh |
| Wire auth | POST `/api/agent` **without** `x-agent-secret` | `401 {"ok":false,"error":"unauthorized"}` |
| Tools | `--smoke` on all 5 tools + eval runner | All print `smoke OK`, exit 0 |

## Status (update as we go)

**Verified ✅:** npm install · vite build · all smoke tests · schema live on Convex · wire auth 401 · authed `get_business` round-trip · guest auth JWT keys set · Resend key set.
**Pending ⏳:** Telegram bot @NaradaMarketingbot created — token goes in narada/.env.local · gateway wiring per `narada/README.md` (env: `TELEGRAM_ALLOWED_USERS=*`, `NARADA_TOOLS_DIR` absolute) · onboarding→crew trigger (how Hermes learns a new business signed up) · Dodo checkout page (stub) · LinkedIn publisher (honest stub, P4) · Langfuse observability wiring · magic-link end-to-end test.
