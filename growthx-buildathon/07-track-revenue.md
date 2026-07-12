# 07 · Track 02: Revenue (208 base + overflow) — reference

Real demand in 8 hours is rare, so observable signals weigh most: signups, product quality, real money. VC-lens parameters stay in at low weight. **100% live product. No decks.**

## Parameters

### Signups — 20x, max 80 ⭐ root (email + first-use event; team doesn't count)
| L1 | L2 | L3 | L4 | L5 |
|----|----|----|----|----|
| 0 | 1–25 | 26–100 | 101–250 | 251+ |

Overflow: +1pt × 20x per additional 50 signups.

### Live product quality — 8x, max 32
| L1 | L2 | L3 | L4 | L5 |
|----|----|----|----|----|
| Broken | Rough MVP, happy path only | Working, does what it claims | Polished, beats alternatives | 10x product, can't tell it was built in 8h |

Mentor tests on their own device, cold, unassisted.

### Revenue generated (USD) — 12x, max 48 (real money moved; not services)
| L1 | L2 | L3 | L4 | L5 |
|----|----|----|----|----|
| $0 | ≤$25 | $25–100 | $100–500 | $500+ |

Overflow: +1pt × 12x per additional $100. Teammate/friend payments don't count. **The removal test: kill the product tomorrow — does the revenue stop? If yes, it counts.**

### Waitlist — 4x, max 16 (email only, hasn't touched product)
| L1 | L2 | L3 | L4 | L5 |
|----|----|----|----|----|
| 0 | 1–50 | 51–250 | 251–1,000 | 1,000+ |

Overflow: +1pt × 4x per additional 250 entries.

### VC-lens (directional, low weight)
| Parameter | Weight | L5 bar |
|-----------|--------|--------|
| Business impact | 4x, max 16 | 30%+ movement on a top metric, path to material impact |
| Right to win | 2x, max 8 | Founder-market fit visible in the build itself (proprietary data/distribution) |
| Why now | 1x, max 4 | Window opened <6 months ago, visible in the product |
| Moat | 1x, max 4 | Compounding: proprietary data + network effects + switching costs, live today |

## Total
80 + 32 + 48 + 16 + 16 + 8 + 4 + 4 = **208 base**. Signups, revenue, waitlist overflow uncapped.

## What counts as revenue
✅ Paid signups (Stripe/Razorpay/Dodo, one-time or subscription), API/usage fees, paid digital goods, premium upgrades
❌ Consulting/agency/done-for-you fees, manual human-in-the-loop work, teammate/friend payments, gifts reframed as revenue
