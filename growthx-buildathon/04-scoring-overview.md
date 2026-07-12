# 04 · Scoring Overview

## Eligibility (only rule): use Hermes one of two ways
1. **As coding partner** — Hermes built your product. Keep session receipts (prompt history, commits mid-session). Mentor scrolls 30 seconds, nods, qualified.
2. **As base harness** — product runs on Hermes, end users interact with it. Show ≥1 Hermes capability doing real work (e.g. judge texts it on Telegram, memory recall, cron fires live).

Either qualifies. Both allowed.

## The L1–L5 rubric
| Level | Meaning |
|-------|---------|
| L1 | Floor — didn't attempt. **Always 0 points** |
| L2 | Baseline — attempted, missing the core |
| L3 | Working — does what it claims |
| L4 | Strong — real quality, stands out |
| L5 | Exceptional — reachable if you ship well; overflow stacks on top |

**Formula: `points = (L − 1) × weight`** — same everywhere.
L5 on a 20x parameter = 80 pts. L3 on it = 40. L1 = 0 (participation doesn't score).

## Score composition
| Component | Points |
|-----------|--------|
| Core track base | 164–208 (track rubric, L1–L5 per parameter) |
| Overflow | **Uncapped** — past L5 on flagged parameters, every increment keeps paying |
| Power-ups | **+25 flat per partner, no cap** (all six = +150) |
| Cross-track bonus | Wins in another track at **half weight, capped 50** |

## Power-ups (all tracks, +25 each, mentor must see it working)
| Partner | Counts when | Evidence |
|---------|-------------|----------|
| Wispr Flow | 500+ words dictated during event | Wispr stats screenshot |
| ElevenLabs | Voice does real work in product | Live demo |
| Convex | Stores real product state / main backend | Repo + Convex dashboard |
| LinkUp | Live search doing real work | Code + live query |
| Dodo Payments | Live checkout in product | Dashboard + live checkout |
| Cloudflare | Hosting/Workers doing real work | Live URL + CF dashboard |

## Cross-track bonus table (half weight, 50 cap, same proof, nothing paid twice)
| Source track | Parameter | Bonus weight | Max |
|---|---|---|---|
| Virality | Signups | 12.5x | 50 |
| Virality | Visitors | 5x | 20 |
| Virality | Reactions+comments | 1x | 4 |
| Revenue | Signups | 10x | 40 |
| Revenue | Product quality | 4x | 16 |
| Revenue | Revenue | 6x | 24 |
| AI as Agency | Real output | 10x | 40 |
| AI as Agency | Observability | 3.5x | 14 |

## How verification works
- Signups checked **live in your database** (not screenshots)
- Traffic cross-checked against signups (ratios must make sense)
- Customers get called; signup emails bounce-tested; unpublished checks too
- Spoofed number = parameter zeroed
- **Anti-spoof ratios (virality):** impressions→visitors max 10% CTR; visitors→signups max 50% conversion. Breach = L1 on that parameter unless proven otherwise
