<!-- sell-kit:start -->
# Chore Footage

[![CI](https://github.com/eliem08/chore-footage/actions/workflows/ci.yml/badge.svg)](https://github.com/eliem08/chore-footage/actions/workflows/ci.yml)

> **Collect paid, consented chore videos that robotics teams can actually train on.**

**Who it's for:** Robotics companies and data vendors sourcing egocentric training video.

**The problem:** Robot learning needs huge amounts of real household footage, and sourcing it with consent, quality control and fair pay is slow and messy.

**What you get:** Bounties, consent and quality gates, duplicate-payout protection, quotas, contributor payouts and a buyer-ready manifest. Payouts go to contributors through Stripe Connect, exactly once.

## Quickstart

Customers receive a release archive with the wheel and the examples. Python 3.10+ and no other dependencies.

```bash
pip install chore_footage-0.1.0-py3-none-any.whl
chore-footage submit ana fold-laundry examples/sample-clip.txt --seconds 120 --resolution 1080p --fps 30 --hands-visible 0.9 --lighting 0.9 --consent-signed --store footage.json
chore-footage status --store footage.json
chore-footage balances --store footage.json
```

## Web app and API

Every command is also a JSON API endpoint and a browser form, served by the built-in web app.

```bash
chore-footage-web --port 8000          # then open http://127.0.0.1:8000
chore-footage-web keys create --label "first customer"   # prints an API key (stored hashed)
docker build -t chore-footage . && docker run -p 8000:8000 -e API_KEYS=sk_... -v chore-footage-data:/data chore-footage
```

Every API call needs `Authorization: Bearer <key>` once any key exists; a server on a public address refuses to start without one. Calls are rate-limited per key (60/min, `--rate`) and metered: `chore-footage-web usage` prints calls per key for billing.

Endpoints: `POST /api/bounties`, `POST /api/demo`, `POST /api/bounty-add`, `POST /api/submit`, `POST /api/status`, `POST /api/balances`, `POST /api/payout`, `POST /api/manifest`, `POST /api/payee-onboard`, `POST /api/payee-status`, `POST /api/payout-send`, plus `GET /healthz` and `GET /api/spec` (machine-readable field list).
Files are sent as `{"name": ..., "content": ...}`, folders as `{"files": [...]}` or a base64 zip.

## Deploy and sell

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/eliem08/chore-footage)

`render.yaml` (one click, above) and `fly.toml` (`fly launch --copy-config`) both run the Dockerfile with a persistent `/data` volume and a `/healthz` check.
To sell self-serve, set four variables and point a Stripe webhook at `https://<your-host>/billing/webhook` (events `checkout.session.completed` and `customer.subscription.deleted`):

| Variable | Example |
|---|---|
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_...` |
| `STRIPE_PRICES` | `team=price_123,business=price_456` |
| `PUBLIC_URL` | `https://chore-footage.example.com` |
| `PLAN_QUOTAS` (optional) | `team=10000,business=250000` successful calls per key per month |

Buyers pick a plan on `/pricing`, pay on Stripe Checkout and see their API key once on the success page. Cancelling the subscription revokes the key. A selling server always requires a key.

## Pricing

Monthly plans start with a 14-day free trial. Prices in USD, billed monthly unless noted.

| Plan | Price | Includes |
|---|---|---|
| **Pilot** | $499 per month | 3 active bounties; QA gates and payouts; Buyer manifest |
| **Production** | $1,999 per month | Unlimited bounties; Per-bounty quality rules; Contributor balances and payout records |
| **Enterprise** | Custom (contact sales) | Managed collection programs; Dedicated support |

To start a trial or buy a plan, [request access](https://github.com/eliem08/chore-footage/issues/new?title=Chore%20Footage%20trial&labels=sales).

Plan note: every plan runs the same software, and every API key unlocks all of it. Monthly call volumes are
enforced when `PLAN_QUOTAS` is set (see Deploy and sell); seat and agent limits are licence terms the code does
not enforce. Support, SLA and done-for-you items are services.

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

## Paying contributors through Stripe Connect

The ledger says what is owed; these commands pay it:

```bash
chore-footage payee-onboard ana --email them@example.com   # creates a Stripe Express account, prints its onboarding link
chore-footage payee-status ana                                # can that account receive transfers yet?
chore-footage payout-send --dry-run                                  # who would be paid what
chore-footage payout-send                                            # pay it
```

- `payout-send` transfers each contributor's unpaid balance, less anything already sent.
- Each transfer's Stripe idempotency key comes from the ledger's state, so running it twice, or retrying after a
  timeout, never pays twice.
- Payees still finishing Stripe's onboarding are skipped and named, and a failed transfer is reported, not
  recorded.
- Transfers are logged in `<store>.connect.json` beside the ledger.
- Set `CONNECT_STRIPE_KEY` to the platform's Stripe secret key. It is kept apart from `STRIPE_SECRET_KEY`,
  which the hosted server uses to sell its own plans. Also set `PUBLIC_URL`, where Stripe sends payees back
  after onboarding.
- Transfers draw on the platform's Stripe balance, so the buyers' money has to be collected there first
  (Checkout, Payment Links or invoices). Stripe refuses a transfer the balance cannot cover.
- It is built to Stripe's Connect API and tested against a stand-in, not yet against a live account.

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
