# 06 · Track 01: Virality (164 base + overflow) — our cross-track bonus source

Narrative matters, platform doesn't (X/LinkedIn/YouTube/IG count the same). **Ads discounted to 25% of face value.** 4 of 5 parameters overflow.

## Parameters (thresholds per level)

### Impressions & views — 1x, max 4
| L1 | L2 | L3 | L4 | L5 |
|----|----|----|----|----|
| <100 | 101–1k | 1k–2.5k | 2.5k–5k | 5k–7.5k |

Overflow: +1pt × 1x per additional 1,000 impressions. Verified via native analytics on builder's device.

### Reactions & comments — 2x, max 8
| L1 | L2 | L3 | L4 | L5 |
|----|----|----|----|----|
| <3 | 3–10 | 11–25 | 26–50 | 51–100 |

Overflow: +1pt × 2x per additional 10 reactions. Team engagement excluded.

### Amplification quality — 3x, max 12 (whose accounts, not volume)
| L1 | L2 | L3 | L4 | L5 |
|----|----|----|----|----|
| None | 1–2 peer builders | 3+ peers OR 1 sub-10k founder | 1 notable (10k+) reshare | Multiple notables / PH feature / press / investor |

### Visitors to product — 10x, max 40
| L1 | L2 | L3 | L4 | L5 |
|----|----|----|----|----|
| <10 | 11–50 | 51–250 | 251–1,000 | 1,000+ |

Overflow: +1pt × 10x per additional 100 visitors. **Read-only analytics access required (Datafast/PostHog/Plausible/GA4) or capped at L2.**

### Signups / meaningful actions — 25x, max 100 ⭐ heaviest
| L1 | L2 | L3 | L4 | L5 |
|----|----|----|----|----|
| ≤5 | 6–25 | 26–100 | 101–250 | 251–1,000 |

Overflow: +1pt × 25x per additional 50 signups. Team members don't count; verified in live backend.

## Anti-spoof checks (this track only)
- **Impressions → visitors: max 10% CTR** — breach = visitors parameter drops to L1
- **Visitors → signups: max 50% conversion** — breach = signups parameter drops to L1
- Both flags = manual review

## Why this matters to us (AI as Agency track)
Cross-track bonus at half weight, 50 cap: our launch post's **signups earn 12.5x** and **visitors 5x**. A modest 20 signups + 100 visitors from the launch ≈ meaningful bonus points on top of our track score. Same proof requirements (live DB, analytics access).
