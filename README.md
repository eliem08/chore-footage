<!-- sell-kit:start -->
# Chore Footage

[![CI](https://github.com/eliem08/chore-footage/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/chore-footage/actions/workflows/ci.yml)

> **Collect paid, consented chore videos that robotics teams can actually train on.**

**Who it's for:** Robotics companies and data vendors sourcing egocentric training video.

**The problem:** Robot learning needs huge amounts of real household footage, and sourcing it with consent, quality control and fair pay is slow and messy.

**What you get:** Bounties, consent and quality gates, duplicate-payout protection, quotas, contributor payouts and a buyer-ready manifest.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install chore_footage-0.1.0-py3-none-any.whl
chore-footage bounties
chore-footage demo
```

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
chore-footage-web --port 8000          # then open http://127.0.0.1:8000
docker build -t chore-footage . && docker run -p 8000:8000 -v chore-footage-data:/data chore-footage
```

Endpoints: `POST /api/bounties`, `POST /api/demo`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Pricing

Every plan starts with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Pilot** | $499 per month | 3 active bounties; QA gates and payouts; Buyer manifest |
| **Production** | $1,999 per month | Unlimited bounties; Custom quality rules; Contributor management |
| **Enterprise** | Custom (contact sales) | Managed collection programs; Custom consent flows; Dedicated support |

To start a trial or buy a plan, email **sales@YOUR-DOMAIN.com**.

## Licence

Proprietary. Copyright (c) 2026 eliem08. All rights reserved. Use requires a paid plan or an active trial; see [LICENSE](LICENSE).
<!-- sell-kit:end -->

## What it does

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

## Development

Zero runtime dependencies; Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python -m unittest discover -s tests -t .           # unit + CLI smoke tests
ruff check . && ruff format --check .               # lint + format
```

```
chore_footage/core.py       domain logic (pure, importable, fully tested)
chore_footage/__main__.py   CLI (`chore-footage ...` / `python -m chore_footage ...`)
tests/                unit tests + generated CLI smoke tests
```

CI runs lint and tests on Ubuntu and Windows across Python 3.10, 3.12 and 3.13.
Design, data model, trade-offs and production path: **[ARCHITECTURE.md](ARCHITECTURE.md)**.

Part of the [agent-economy](https://github.com/eliem08/agent-economy) portfolio (idea #12).
