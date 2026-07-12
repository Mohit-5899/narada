# Narada Web

Web UI for **Narada** — the AI marketing agency built on Hermes.
*"Every business has a story. Narada makes the three worlds hear it."*

Vite + React + TypeScript, Convex backend, Convex Auth (email magic link).

## Run it (no backend needed)

```sh
npm install
npm run dev
```

Landing page, pricing, and checkout stub work immediately. Authed pages show
a "backend not connected" notice until you activate Convex.

## Activation checklist (3 commands)

```sh
# 1. Create/attach a Convex deployment (interactive login on first run).
#    Also regenerates convex/_generated and starts the function watcher.
npx convex dev

# 2. Point the frontend at it: copy .env.example → .env.local and set
#    VITE_CONVEX_URL to the URL printed by step 1, plus your bot name.
cp .env.example .env.local

# 3. Deployment env vars (magic links + agent endpoint auth):
npx convex env set SITE_URL http://localhost:5173
npx convex env set AUTH_RESEND_KEY re_...          # from resend.com
npx convex env set AGENT_SHARED_SECRET $(openssl rand -hex 24)
```

Then `npm run dev` in a second terminal. Convex Auth also needs its JWT keys
on first setup — if sign-in complains, run `npx @convex-dev/auth` once (it
sets `JWT_PRIVATE_KEY`/`JWKS` on the deployment).

Until `AUTH_RESEND_KEY` is set, use **"Continue as guest"** (Anonymous
provider) — the whole flow works with it.

## Flow

1. `/` landing → Get started
2. Sign in (magic link or guest)
3. `/start` onboarding form → creates `businesses` + `brand_briefs(analyzing)`
   → live "analyzing" screen (3 agent cards, reactive — no polling code,
   Convex pushes the status change)
4. `/brief` review → every field editable, saves on blur → **✅ That's us**
   sets `approved_at`
5. `/telegram` handoff → `https://t.me/$VITE_TELEGRAM_BOT?start=<link_token>`
6. `/dashboard` read-only campaigns + tasks, live via Convex reactivity

## Agent endpoint (for the Hermes backend)

`POST {CONVEX_SITE_URL}/api/agent` (the `.convex.site` URL, not `.convex.cloud`)
with header `x-agent-secret: $AGENT_SHARED_SECRET`. All writes are keyed by
the business `link_token` (same token as the Telegram deep link).

```jsonc
// flip the brief to ready with results
{ "type": "brief", "link_token": "…", "status": "ready",
  "offering": "…", "audience": "…", "tone": ["warm"],
  "competitors": ["…"], "colors": ["#FF9933"], "campaign_ideas": ["…"] }

// bind a Telegram user after /start deep link
{ "type": "telegram_link", "link_token": "…", "telegram_user_id": "12345" }

// create a campaign (response: {"campaign_id": "..."}); pass campaign_id to update
{ "type": "campaign", "link_token": "…", "title": "Diwali push", "status": "running" }

// create/update a task (response: {"task_id": "..."})
{ "type": "task", "campaign_id": "…", "agent_role": "copywriter",
  "description": "Draft LinkedIn post", "status": "running",
  "cost_usd": 0.012, "trace_url": "https://langfuse…" }
```

## Stubbed / deliberate shortcuts

- **Checkout** is a placeholder page for Dodo Payments.
- **`briefs.devSeed`** mutation + "load a sample brief" button: demo fallback
  while the Hermes crew isn't wired; remove once `/api/agent` is live.
- **`convex/_generated/` is committed** so install+dev works with zero
  credentials; `npx convex dev` regenerates identical files.
- Hash-based routing (`#/dashboard`) — no router dependency, works on any
  static host.
