# Narada 🪷

> **Every business has a story. Narada makes the three worlds hear it.**

**Narada is an AI marketing agency** — a team of AI agents that runs marketing for your business end to end. A manager agent plans; specialist *ganas* (researcher, copywriter, creative, publisher, analyst) execute on **real platforms** — LinkedIn, Instagram, X, YouTube. You approve everything from Telegram. It learns your brand and gets sharper with every task.

Named for the divine messenger of Indian mythology, built on [Hermes](https://github.com/NousResearch/hermes-agent) — his Greek counterpart. A product by **Quanta AI Labs**.

**🌍 Live:** [narada-2i1.pages.dev](https://narada-2i1.pages.dev) · **🤖 Bot:** [t.me/NaradaMarketingbot](https://t.me/NaradaMarketingbot) · **💳 $9/mo**

---

## How it works

```
1. Onboard on the web (~2 min)   → business name + website + logo/images/PDFs
2. The crew analyzes you         → live site + market research + competitors
                                   → Brand Brief + context_md (your brand's memory)
3. Approve the brief             → every field editable; you own the truth
4. One tap → Telegram            → your marketing team lives in your pocket
5. Talk like a colleague         → "write a LinkedIn post about our launch"
   → manager plans → gana executes → QA gate → YOUR approval → real publish
   → logged to the live dashboard → analyst learns → context_md improves
```

**Nothing publishes without your "ship it."** Ever.

## The team — 6 agents · 12 skills · 7 tools

| Agent | Job |
|-------|-----|
| **Narada** (manager) | Triage, planning, QA gate (bounces off-brand/dishonest drafts), approvals, logging |
| 🔍 Researcher | Live market/competitor intel via LinkUp → ≤300-word insight briefs |
| ✍️ Copywriter | Platform-native copy — 10 psychology levers, honesty rules (banned fake-urgency vocabulary) |
| 🎨 Creative | Images (Nano Banana Pro) + video (Veo 3.1 fast) + premium (Higgsfield) in your brand identity |
| 📣 Publisher | Real-surface posting via Zernio (LinkedIn/IG/X/YouTube), email, Telegram channels |
| 📊 Analyst | Performance review → learnings written back to your brand memory |

Agents are Hermes delegations (dynamic per-request planning, `max_spawn_depth: 2` — the manager can invent new roles mid-task). Skills are git-versioned markdown; tools are stdlib-only Python scripts with offline smoke tests.

## Verified, not vibes (day-one numbers)

| Metric | Result |
|--------|--------|
| Live agent evals | **15/15 checks · 6/6 agents PASS** (skills-as-system-prompt, direct Anthropic API) |
| Static pre-deploy gate | **6/6 skill contracts** (`check_skills.py`, seconds, free) |
| Observability | Every turn traced to Langfuse with per-step cost; 26-observation delegation trees; eval scores pushed as Langfuse scores per git version |
| Alerts | Cost >$2 / latency breaches → Telegram (15-min cron); run-diff tooling (`langfuse_ops.py`) |
| Performance SLO | basic ≤10s · complex interactive ≤60s (measured: full campaign draft 59s/$0.80) |
| Real output | Real LinkedIn posts published through the approval gate; every task logged live to the dashboard |
| Self-improvement | The system wrote itself a new skill (`web-research-fallback`) when a tool failed — unprompted |

## Architecture

```
Business owner
   │ web (Cloudflare Pages)              │ Telegram (@NaradaMarketingbot)
   ▼                                     ▼
narada-web/  ── Vite+React UI ──► Convex (businesses, briefs, context_md,
   │  onboarding · brief · dashboard      campaigns, tasks, eval_cases)
   │  password auth · Dodo checkout            ▲ POST /api/agent (shared secret)
   ▼                                           │
Hermes gateway (always-on) ── Narada SOUL + skills ── narada/tools/
   ├─ per-message identity: telegram_user_id → business + brand memory
   ├─ cron: auto-onboarding poller · cost alerts
   └─ traces → Langfuse (JP)
```

Three memory layers: session (now) · per-business `context_md` in Convex (client history + brand rules) · Hermes MEMORY.md (the system's own operating lessons).

## Repo layout

| Path | What |
|------|------|
| `narada/` | The product's agent layer: `skills/` (6 SKILL.md roles) · `tools/` (convex_client, zernio, linkup, gemini_media, langfuse_ops, email, telegram, landing-page) · `evals/` (static gate + live per-agent evals + Langfuse score push) · `config/` |
| `narada-web/` | Web app: Vite + React + Convex (schema, auth, `/api/agent` HTTP contract, live dashboard) |
| `growthx-buildathon/` | Build docs — `project.md` is the living decision log (D1–D17) |
| everything else | Stock [Hermes](https://github.com/NousResearch/hermes-agent) runtime — unmodified; Narada plugs in via skills/tools/config only |

## Run it yourself (self-host sketch)

```bash
uv sync                                   # Hermes from this repo's source
# ~/.hermes/config.yaml  ← narada/config/hermes-config-snippet.yaml (model,
#                          skills.external_dirs, delegation)
# ~/.hermes/.env         ← narada/.env.example (Telegram bot token,
#                          TELEGRAM_ALLOWED_USERS=*, Convex, Zernio, LinkUp,
#                          Gemini, ElevenLabs, Langfuse keys)
cd narada-web && npx convex dev           # push schema to your Convex project
npm run dev                               # UI on :5173
uv run hermes gateway                     # the agency comes online

# Pre-deploy gate (run before ANY skill change ships):
python3 narada/evals/check_skills.py            # free, seconds
python3 narada/evals/run_agent_evals.py --live  # ~$0.30, pushes scores to Langfuse
```

## Stack

[Hermes](https://github.com/NousResearch/hermes-agent) (agent runtime) · Claude Sonnet 5 (manager) + Haiku 4.5 (ganas) · [Convex](https://convex.dev) (state + reactive dashboard) · [Cloudflare Pages](https://pages.cloudflare.com) (UI) · [Zernio](https://zernio.com) (multi-platform publishing) · [LinkUp](https://linkup.so) (live search) · Gemini (Nano Banana Pro images, Veo 3.1 video) · [ElevenLabs](https://elevenlabs.io) (voice briefings) · [Langfuse](https://langfuse.com) (traces, evals, alerts) · [Dodo Payments](https://dodopayments.com) (checkout)

## Credits & license

Built on [hermes-agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) — the runtime, gateway, delegation, memory, and cron are Hermes. Narada adds the marketing agency on top. Marketing skill frameworks adapted in part from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) (MIT).

MIT — see [LICENSE](LICENSE).

*The messenger is listening.* 🪷
