# 09 · Setup — Get Hermes Running (do BEFORE 10 AM)

## 1. LLM access (provider is NOT scored — pick for strength/cost)

| Option | Cost | Notes |
|--------|------|-------|
| **OpenAI GPT-5.6 Sol** (recommended, partner) | $200 credits already ours (if org ID given at registration) | Strongest model driving Hermes today |
| OpenRouter | $10 credit | Cheapest way in, same models |
| Nous Portal | $20/mo | Managed Tool Gateway: web search, image gen, TTS, browser automation pre-wired |

### OpenAI config
`~/.hermes/.env`:
```
OPENAI_API_KEY=sk-...
```
`~/.hermes/config.yaml` — **provider id is `openai-api`, NOT `openai`**:
```yaml
model:
  provider: "openai-api"
  default: "gpt-5.6-sol"
```
One-liner alternative: `hermes chat --provider openai-api --model gpt-5.6-sol`

## 2. Port Claude Code setup → Hermes (5 min, before sprint)

| Asset | Effort | How |
|-------|--------|-----|
| Project file | Already works | Hermes reads `.hermes.md` → `AGENTS.md` → `CLAUDE.md` (first found wins — keep ONE) |
| Skills | One line | `skills:\n  external_dirs:\n    - ~/.claude/skills` in config.yaml → all become /slash commands |
| Global instructions | By hand | `~/.claude/CLAUDE.md` NOT read. Move behavior → `~/.hermes/SOUL.md`, facts → `~/.hermes/memories/MEMORY.md` (**capped ~2,200 chars**) |
| Commands/subagents | Rewrite as skills | No `.claude/commands` equivalent; each command = a skill. Subagents spawn at runtime |
| MCP servers | Translate | `mcpServers` JSON → `mcp_servers:` block in config.yaml |

Porting prompt (give to Hermes in the repo):
> Read my ~/.claude folder and this repo's CLAUDE.md, then port them to Hermes. Turn each command in .claude/commands into a skill under ~/.hermes/skills/. Translate my MCP servers into the mcp_servers: block in ~/.hermes/config.yaml. Summarise my global CLAUDE.md into ~/.hermes/SOUL.md and memories/MEMORY.md. Tell me what you could not carry over and why.

Then verify: `hermes skills browse`

## 3. First-run install
```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
hermes model     # pick provider
hermes status    # verify
```

## 4. Telegram gateway (remote control — do Telegram first, not WhatsApp)
1. `@BotFather` → `/newbot` → save token
2. `@userinfobot` → get **numeric** user ID (username doesn't matter)
3. `hermes gateway setup` → Telegram → paste token + numeric ID
4. `hermes gateway` (leave running) → DM the bot: "Hello Hermes. Reply in one sentence and tell me what tools are active."

Wizard fails? `~/.hermes/.env`:
```
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_ALLOWED_USERS=<numeric-id>
```

## 5. Memory + skills (only after Telegram answers)
- Tier 0: USER.md + MEMORY.md — injected every turn
- Tier 1: session .jsonl + SQLite FTS5 cross-session search
- Tier 2: pluggable — Holographic (local, free) OR Honcho (self-improving user model). **Only one active**
```bash
hermes memory setup
hermes skills browse
```

## 6. Pre-build checklist
- [ ] `hermes status` shows provider/model
- [ ] Telegram DM responds
- [ ] Web-search prompt works
- [ ] Image test works (Telegram or URL fallback)
- [ ] `hermes memory status` clear
- [ ] Final test DM: "Give me a one-paragraph setup report: model, tool route, channel, memory, and one thing still missing."

## 7. Common breaks
| Symptom | Fix |
|---------|-----|
| Model not answering | `hermes model` again, finish login; check key in `.env`, no trailing spaces |
| OpenAI misconfig | provider is `openai-api` (not `openai`); model is `gpt-5.6-sol` |
| Gateway token issue | `hermes gateway setup`, re-paste |
| Wrong user ID | numeric ID from @userinfobot, re-run setup |
| Bot silent in groups | BotFather `/setprivacy` or make bot group admin; remove + re-add bot |
| Image paste fails | Send via Telegram or URL: "Analyze this image URL: <url>" |
| Two memory providers | Only one external provider active — pick one, `hermes memory status` |
| Ollama | Needs ≥64K context: `num_ctx: 65536` via Modelfile |
| MCP changes ignored | Restart Hermes or `/reload-mcp` in chat |
