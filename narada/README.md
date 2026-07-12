# Narada — AI Marketing Agency on Hermes

*"Every business has a story. Narada makes the three worlds hear it."*

Narada is a marketing agency built entirely on Hermes' extension points — no
Hermes core code is modified. The Hermes main loop is the orchestrator (D9:
no fixed campaign workflow); the marketing brain lives in skills, the hands
live in standalone Python tools, and per-business context comes from Convex
(D10: single profile, open Telegram bot).

```
narada/
├── skills/            narada-manager + 4 specialist ganas (SKILL.md each)
├── tools/             convex_client, zernio (social publishing, primary),
│                      publish_telegram_channel, send_email,
│                      deploy_landing_page, publish_linkedin (stub)
├── config/            hermes-config-snippet.yaml — blocks for ~/.hermes/config.yaml
├── evals/             eval_set.jsonl (20 briefs) + run_evals.py
└── .env.example       every env var Narada reads
```

## Wiring: fresh Hermes install → Narada answering on Telegram

1. **Install Hermes** (this repo) and run `hermes setup` once. Confirm
   `hermes status` works.

2. **Model** — buildathon provider id is `openai-api` (NOT `openai`):
   ```yaml
   # ~/.hermes/config.yaml
   model:
     provider: "openai-api"
     default: "gpt-5.6-sol"
   ```

3. **Load Narada skills** (external, read-only — nothing copied):
   ```yaml
   skills:
     external_dirs:
       - /ABSOLUTE/PATH/TO/REPO/narada/skills
   ```

4. **Delegation** — manager spawns specialists, depth 2 for mid-task
   orchestrator spawns (requires `role="orchestrator"` on the intermediate
   agent, per `tools/delegate_tool.py`):
   ```yaml
   delegation:
     max_spawn_depth: 2
     orchestrator_enabled: true
   ```
   Full merged blocks: `narada/config/hermes-config-snippet.yaml`.

5. **Convex backend** (cloud, convex.dev free tier). Create a deployment with:
   - tables: `businesses` (link_token, telegram_user_id, name), `brand_briefs`,
     `tasks`, `eval_cases`
   - one HTTP action `POST /api/agent` that checks
     `Authorization: Bearer $CONVEX_AGENT_SECRET` and dispatches on the `fn`
     field. The exact fn names + args the client sends are documented in
     `narada/tools/convex_client.py`'s docstring.

6. **Env vars** — copy `narada/.env.example` values into `~/.hermes/.env`.
   `NARADA_TOOLS_DIR` must be the absolute path to `narada/tools`; the skills
   invoke every tool through it.

7. **Open Telegram bot — IMPORTANT, verified against the code.**
   Hermes fails **closed**: with `TELEGRAM_ALLOWED_USERS` unset, unknown DMs
   hit the pairing flow and `gateway/authz_mixin.py::_is_user_authorized`
   denies by default (fail-open removed in #24457/#34515; SECURITY.md §2.6).
   The original D10 note ("unset = unrestricted") is wrong. Opt in explicitly:
   ```
   TELEGRAM_BOT_TOKEN=123456:ABC...
   TELEGRAM_ALLOWED_USERS=*        # or TELEGRAM_ALLOW_ALL_USERS=true
   ```
   Gateway-level auth is then open; business identity is enforced per message
   by the narada-manager skill via Convex lookup.

8. **Start the gateway**: `hermes gateway start`, then message the bot.

9. **Smoke-check the tools** (all offline, no keys needed):
   ```bash
   for t in narada/tools/*.py narada/evals/run_evals.py; do python3 "$t" --smoke; done
   ```

## The /start <token> → business binding flow

1. Web onboarding creates a `businesses` row with a random `link_token` and
   shows the owner `https://t.me/<bot>?start=<link_token>`.
2. Owner taps it; Telegram sends the bot `/start <link_token>`.
3. The gateway passes the message to the agent; the **narada-manager** skill
   sees an unbound sender + token and runs:
   ```bash
   python3 "$NARADA_TOOLS_DIR/convex_client.py" bind-telegram \
     --link-token <TOKEN> --telegram-user-id <SENDER_ID>
   ```
   The Convex action sets `businesses.telegram_user_id` (rejecting used/unknown
   tokens) and returns the business + brief.
4. Every later message: `get-business --telegram-user-id <SENDER_ID>` → brand
   brief loaded as context → chat/tool/delegate as needed.

## Operating rules (enforced by the manager skill)

- **Approval gate**: nothing is published to a real surface without the owner
  approving the exact final copy in chat.
- **Logging**: every completed task → `convex_client.py log-task`.
- **Closed-loop evals**: failures/escalations → `append-eval-case`, and the
  curated set lives in `evals/eval_set.jsonl`.

## Evals

Save model outputs to `narada/evals/outputs/<version>/<id>.txt` (one dir per
git tag / label), then:

```bash
python3 narada/evals/run_evals.py            # pass-rate table across versions
python3 narada/evals/run_evals.py --details  # per-case failures
```

Checks are programmatic where honest (CTA presence, banned words, platform
format incl. email subject and single-H1 rules); `respects_tone` is reported
as MANUAL and excluded from the pass rate — an LLM judge is the upgrade path.

## Surface reliability

| Surface | Tool | Status |
|---|---|---|
| Social (X, LinkedIn, IG… via Zernio) | `zernio.py` | primary, real (needs `ZERNIO_API_KEY`) |
| Telegram channel | `publish_telegram_channel.py` | secondary, real |
| Email (Resend) | `send_email.py` | real |
| Landing page | `deploy_landing_page.py` | writes HTML always; wrangler deploy only when `NARADA_WRANGLER_DEPLOY=true` |
| LinkedIn | `publish_linkedin.py` | STUB — untested, fails loudly (P4) |
