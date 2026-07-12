# Narada ☸

> **Every business has a story. Narada makes the three worlds hear it.**

**Narada is an AI marketing agency** — a team of AI agents that runs marketing for your business. A manager agent (Narada) plans your campaigns; specialist agents (his *ganas* — researcher, copywriter, publisher, analyst) execute them on real surfaces: real social posts, real emails, real landing pages. You run your whole marketing team from Telegram.

Named for the divine messenger of Indian mythology — and built on [Hermes](https://github.com/NousResearch/hermes-agent), his Greek counterpart.

## How it works

```
1. Onboard on the web  →  business name + website URL
2. Narada's crew analyzes your site, market, and brand  →  Brand Brief (~90s)
3. Approve the brief  →  get your Telegram link
4. Chat: "launch a campaign for Diwali"  →  the agents plan, draft,
   get your approval, and publish — for real
```

- **No workflows to configure** — you talk, the manager plans per-request and spawns the specialists each job needs
- **It remembers** — your brand rules, your past campaigns, your voice
- **Fully traced** — every agent step, token, and cost is observable
- **Always on** — scheduled posts and daily voice briefings, unattended

## Architecture

| Layer | What |
|-------|------|
| Web UI | Onboarding, brand brief approval, read-only campaign dashboard, checkout |
| Telegram | The command center — assign work in natural language |
| Agent core | [Hermes](https://github.com/NousResearch/hermes-agent) main loop as orchestrator + dynamic subagent delegation |
| Marketing brain | Skills (versioned markdown roles: manager, researcher, copywriter, publisher, analyst) |
| Hands | Tools: publish to LinkedIn/email/Telegram channels, deploy landing pages |
| State | Convex (businesses, brand briefs, campaigns, tasks, evals) |
| Observability | Langfuse trace trees, run diffs, cost alerts |

## Project docs

Build plan, decisions, and roadmap live in [`growthx-buildathon/project.md`](growthx-buildathon/project.md).

Built for the **GrowthX × Hermes Buildathon**.

## Credits & license

Narada is built on [hermes-agent](https://github.com/NousResearch/hermes-agent) by [Nous Research](https://nousresearch.com) (MIT). This repository preserves the original [LICENSE](LICENSE). The agent runtime, gateway, tools, and skills infrastructure are Hermes; Narada adds the marketing agency layer on top.

MIT — see [LICENSE](LICENSE).
