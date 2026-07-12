# 05 · Track 03: AI as Agency — OUR TRACK (164 base + overflow)

**The framework:** a team of AI agents replaces a full human function. A manager agent plans, specialists execute, handoffs pass work, memory persists across tasks, and a control surface lets a non-engineer assign work. *"If an agency was run with agents instead of humans, how would it work?"*

## Parameter 1 · Working product shipping real output — 20x, max 80 ⭐ ROOT
Real surface = a system a paying customer could use tomorrow. **Staged/sandbox surfaces cap at L3.**

| L | Bar |
|---|-----|
| L1 | Demo only, canned responses, 0 completed tasks |
| L2 | Agents run but output broken/hallucinated; <30% task success |
| L3 | Working output on **staged/test surfaces**; 50–70% success (ceiling for sandboxes) |
| L4 | Real output on **real surfaces**, human approves every step; 70–85% success |
| L5 | **End-to-end on real live surfaces, 85%+ success across 3+ repeated runs, escalates by exception only** |

**Overflow: +1pt × 20x per additional real task completed autonomously during judging** ← the biggest point mine in the whole event.

## Parameter 2 · Agent org structure — 5x, max 20
| L | Bar |
|---|-----|
| L1 | One monolithic agent, one giant prompt |
| L2 | 2–3 agents, hardcoded handoffs, no manager |
| L3 | Manager + named specialists, static routing table |
| L4 | **Dynamic: manager plans subtasks per request, delegates, reviews outputs, bounces bad drafts back** |
| L5 | **Emergent: manager spawns sub-specialists on the fly, stuck agents escalate with concrete blockers, roles self-adjust** — trace must show a role that didn't exist at kickoff |

## Parameter 3 · Observability — 7x, max 28 (tool-agnostic)
| L | Bar |
|---|-----|
| L1 | console.log/print only |
| L2 | Structured logs to file (JSONL/DB rows), no UI |
| L3 | Pull up a specific run, see each agent's steps (any tool: custom, OSS, SaaS, OTel) |
| L4 | **Trace tree across agents (who called whom), token + cost per step, filter by agent/task** |
| L5 | Production-grade: diff two runs side by side, alerts on failure/cost spike, search across runs |

## Parameter 4 · Evaluation and iteration — 5x, max 20
| L | Bar |
|---|-----|
| L1 | No evals — "it feels better" |
| L2 | Manual spot-checks of favorite runs |
| L3 | **Named eval set with expected outcomes, run manually to compare versions** |
| L4 | Automated CI-style pipeline; quality drop blocks release |
| L5 | Closed-loop: failed runs auto-feed a growing eval set, version-controlled prompts, measurable gains across versions |

## Parameter 5 · Agent handoffs and memory — 2x, max 8
| L | Bar |
|---|-----|
| L1 | Remembers nothing; every turn from zero |
| L2 | One or two basic fields (identity only) |
| L3 | Context within a single task; lost at handoff |
| L4 | Context across task + 1–2 handoffs; user history informs decisions |
| L5 | **Three memory layers: current task + this user's past + business rules/policy — survives all handoffs** |

## Parameter 6 · Cost and latency per task — 1x, max 4 (worse measure governs)
| L | Bar |
|---|-----|
| L1 | >30 min OR >$5 |
| L2 | 10–30 min OR $2–5 |
| L3 | 5–10 min OR $0.50–2 |
| L4 | 1–5 min OR $0.10–0.50 |
| L5 | **<1 min AND <$0.10** (both must hold) |

## Parameter 7 · Management UI — 1x, max 4
| L | Bar |
|---|-----|
| L1 | CLI or code only |
| L2 | Basic web UI, dev-only |
| L3 | Functional UI a PM could operate with docs |
| L4 | Clean UI; non-eng operates after one walkthrough |
| L5 | **Tested live: non-eng volunteer creates a new agent role (job, tools, guardrails) in <10 min unassisted** |

## Total
80 + 20 + 28 + 20 + 8 + 4 + 4 = **164 base**. Real-output overflow on top, uncapped.

> Observability is tool-agnostic: Langfuse, Braintrust, OTel, homebrewed dashboard over Postgres — all score the same. The question is what you can SEE, not the logo.
