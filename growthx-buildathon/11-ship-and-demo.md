# 11 · Ship, Submit & Demo Prep

## Ship & submit (2 rules)
1. **Live URL anyone can use** — web app, landing page, or bot link. If a judge can't use it from their own device, it doesn't count.
2. **Submit at growthx.club/hermes-buildathon/submit** before the deadline. Only way. No slides, no zips. Don't leave it to the last 5 minutes.

## Demo format — 4 minutes, live, not recorded

| Segment | Time | What |
|---------|------|------|
| Context | 20 sec | One sentence: who it's for, what it replaces. No padding, no agenda slide, no team intro |
| Live demo | rest of 2 min | Core loop end to end: **one happy path + one edge case**. Doing the job, not a settings tour |
| Proof | 1 min | Numbers ON SCREEN: signups dashboard, Dodo payments, run log with real output. If it isn't on screen, it doesn't count |
| Q&A | 1 min | Judges ask about your **weakest number** — know the answer cold |

## Script-prep prompt (fill brackets, paste to AI)
```
I'm demoing what I built at the Hermes Buildathon. I have 4 minutes on
stage: 2 minutes of live demo, 1 minute of proof on screen, 1 minute of
judges' Q&A. It's live, not recorded. Help me write the script.

My build: [one sentence]
My track: [AI as Agency]
My demo flow: [steps]
My real numbers: [true numbers only]

How I'm scored:
1. Track rubric only; points = (L-1) × weight; root param heaviest.
2. Proof first — full minute of numbers on screen.
3. Numbers verified, not trusted: live DB checks, analytics cross-checks.
4. Power-ups flat +25 each, only for real use a mentor saw working.

Write a tight 4-minute script: 20s context, live demo with one happy
path and one edge case, then the proof minute in order. Flag which
rubric parameter each beat earns, and predict the Q&A question about
my weakest number.
```

## Before walking up
- **Test the setup** — mic, screen share, every surface logged in (product, DB, analytics). Proof minute dies on a login fumble
- **Nail first 30 sec** — who it's for + what it replaces, then straight to demo
- **Backup recording** — record a clean run beforehand; if live dies, switch and keep talking (numbers still verified either way)
- **Practice the full 4 min twice** — over time? Cut words, not speed. Never cut demo or proof

**If it breaks on stage:** narrate intended behavior ("this is where it pulls the record..."), recover or switch to backup, move on. Recovery says more about the build than a perfect run.
