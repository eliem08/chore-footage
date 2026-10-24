# chore-footage

> **Shutterstock for robot training videos** — get paid to film yourself doing chores.

Humanoid and home-robot companies are starved for egocentric video of real
people folding laundry, loading dishwashers and making beds. `chore-footage`
is the marketplace back end: bounties for specific tasks, automated
submission QA, consent tracking and contributor payouts.

## What the MVP does

- **Bounty catalogue**: task, pay per accepted minute, min/max clip length,
  required camera view (egocentric / third-person), min resolution & fps, quota
- **Submission validation** from clip metadata (what a phone app would upload):
  duration, resolution, fps, view, hands-visible ratio, lighting score,
  consent signed, bystander faces detected, duplicate hash
- **Quality score** 0–100 → accept / reject with reasons, and a quality bonus
- **Ledger**: payouts per contributor, quota tracking per bounty
- Buyer-side **dataset export manifest** (JSONL) of accepted clips with labels

## Quickstart

```bash
pip install -e .
chore-footage bounties
chore-footage demo
```

## Roadmap

- Mobile capture app with on-device QA (hand tracking, blur, framing)
- Face / PII auto-blur pipeline, household-member consent flow
- Action segmentation labels (start/end of each sub-step) via labeller marketplace
- Buyer licensing tiers (exclusive vs. non-exclusive)
