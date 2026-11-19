"""Operating commands: clip intake, review, contributor balances and the buyer manifest on a persistent store.

The duplicate check hashes the uploaded file itself, so the same footage cannot be paid twice under a new
name. Quality inputs (hands visible, lighting, bystander faces) come from your capture app or QA pass.
Balances are a ledger: `payout` records that you paid a contributor through your own payment provider.
"""

import hashlib
import json
import os
import time
from collections import defaultdict
from dataclasses import asdict

from . import connect
from .core import RES_ORDER, Bounty, Clip, Marketplace, Review

OPS = ("bounty-add", "submit", "status", "balances", "payout", "manifest", *connect.COMMANDS)
MAX_CLIP_BYTES = 2 * 1024**3


class IntakeError(ValueError):
    pass


def load(path: str) -> Marketplace:
    try:
        with open(path, encoding="utf-8-sig") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        mp = Marketplace()
        mp.paid = []
        return mp
    if not isinstance(doc, dict) or "bounties" not in doc:
        raise IntakeError(f"{path}: not a chore-footage store")
    mp = Marketplace([Bounty(**b) for b in doc["bounties"]])
    mp.accepted = [(Clip(**c), Review(**r)) for c, r in doc.get("accepted", [])]
    mp.rejected = [(Clip(**c), Review(**r)) for c, r in doc.get("rejected", [])]
    mp.minutes_filled = defaultdict(float, doc.get("minutes_filled", {}))
    mp.balances = defaultdict(float, doc.get("balances", {}))
    mp._hashes = {c.content_hash for c, _ in mp.accepted}
    mp._clip_ids = {c.clip_id for c, _ in mp.accepted}
    mp.paid = doc.get("paid", [])
    return mp


def save(mp: Marketplace, path: str):
    doc = {
        "bounties": [asdict(b) for b in mp.bounties.values()],
        "accepted": [[asdict(c), asdict(r)] for c, r in mp.accepted],
        "rejected": [[asdict(c), asdict(r)] for c, r in mp.rejected[-500:]],  # keep recent rejections only
        "minutes_filled": dict(mp.minutes_filled),
        "balances": dict(mp.balances),
        "paid": mp.paid,
    }
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2)
    os.replace(tmp, path)


def file_hash(path: str) -> str:
    if os.path.getsize(path) > MAX_CLIP_BYTES:
        raise IntakeError(f"{path}: clip over {MAX_CLIP_BYTES // 1024**3} GB")
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    if h.digest() == hashlib.sha256(b"").digest():
        raise IntakeError(f"{path}: empty file")
    return h.hexdigest()


def add_ops(sub):
    store = os.environ.get("CHORE_FOOTAGE_STORE", "footage.json")
    p = sub.add_parser("bounty-add", help="post a chore you will pay to have filmed")
    p.add_argument("bounty_id")
    p.add_argument("--task", required=True)
    p.add_argument("--pay-per-minute", type=float, required=True)
    p.add_argument("--min-seconds", type=int, default=60)
    p.add_argument("--max-seconds", type=int, default=900)
    p.add_argument("--view", choices=["egocentric", "third-person"], default="egocentric")
    p.add_argument("--min-resolution", choices=sorted(RES_ORDER, key=RES_ORDER.get), default="1080p")
    p.add_argument("--min-fps", type=int, default=30)
    p.add_argument("--quota-minutes", type=float, default=600)
    p = sub.add_parser("submit", help="a contributor hands in a clip: reviewed and priced on the spot")
    p.add_argument("contributor")
    p.add_argument("bounty_id")
    p.add_argument("clip", help="the video file (hashed to catch duplicates)")
    p.add_argument("--seconds", type=float, required=True)
    p.add_argument("--resolution", choices=sorted(RES_ORDER, key=RES_ORDER.get), required=True)
    p.add_argument("--fps", type=int, required=True)
    p.add_argument("--view", choices=["egocentric", "third-person"], default="egocentric")
    p.add_argument("--hands-visible", type=float, required=True, help="share of frames with hands in view, 0-1")
    p.add_argument("--lighting", type=float, required=True, help="0-1")
    p.add_argument("--consent-signed", action="store_true")
    p.add_argument("--bystander-faces", type=int, default=0)
    sub.add_parser("status", help="each bounty's quota, minutes collected and acceptance rate")
    sub.add_parser("balances", help="what each contributor is owed")
    p = sub.add_parser("payout", help="record that a contributor was paid their balance")
    p.add_argument("contributor")
    p.add_argument("--reference", required=True, help="your payment reference")
    sub.add_parser("manifest", help="the dataset manifest for buyers (JSON lines)")
    connect.add_commands(sub)
    for name in OPS:
        sub.choices[name].add_argument("--store", default=store)


def run_ops(a) -> int:
    if a.cmd in connect.COMMANDS:
        return connect.run_command(a, _unpaid, "chore-footage", _settle)
    try:
        mp = load(a.store)
        code = _run(mp, a)
        save(mp, a.store)
        return code
    except ValueError as e:
        print(f"refused: {e}")
        return 1


def _run(mp: Marketplace, a) -> int:
    c = a.cmd
    if c == "bounty-add":
        if a.bounty_id in mp.bounties:
            raise IntakeError(f"bounty {a.bounty_id!r} already exists")
        if not (a.pay_per_minute > 0 and 0 < a.min_seconds <= a.max_seconds and a.quota_minutes > 0):
            raise IntakeError("need pay > 0, 0 < min-seconds <= max-seconds and quota > 0")
        mp.bounties[a.bounty_id] = Bounty(
            a.bounty_id,
            a.task,
            a.pay_per_minute,
            a.min_seconds,
            a.max_seconds,
            a.view,
            a.min_resolution,
            a.min_fps,
            a.quota_minutes,
        )
        print(f"{a.bounty_id}: ${a.pay_per_minute:.2f}/min, up to {a.quota_minutes:g} minutes")
    elif c == "submit":
        digest = file_hash(a.clip)
        clip = Clip(
            f"clip-{digest[:12]}",
            a.contributor,
            a.bounty_id,
            a.seconds,
            a.resolution,
            a.fps,
            a.view,
            a.hands_visible,
            a.lighting,
            a.consent_signed,
            a.bystander_faces,
            digest,
        )
        rev = mp.review(clip)
        if rev.accepted:
            print(f"ACCEPTED {clip.clip_id}  quality {rev.quality}  ${rev.payout:.2f}  ({rev.reasons[0]})")
            return 0
        print(f"REJECTED {clip.clip_id}  quality {rev.quality}")
        for reason in rev.reasons:
            print(f"  - {reason}")
        return 1
    elif c == "status":
        for b in mp.bounties.values():
            ok = sum(1 for cl, _ in mp.accepted if cl.bounty_id == b.bounty_id)
            no = sum(1 for cl, _ in mp.rejected if cl.bounty_id == b.bounty_id)
            rate = f"{ok / (ok + no):.0%} accepted" if ok + no else "no clips yet"
            print(f"{b.bounty_id:<18}{mp.minutes_filled[b.bounty_id]:>7.1f} of {b.quota_minutes:g} min  {rate}")
    elif c == "balances":
        owed = {k: v for k, v in mp.balances.items() if v > 0}
        for who, amount in sorted(owed.items()):
            print(f"{who:<20} ${amount:,.2f}")
        print(f"total owed: ${sum(owed.values()):,.2f}; paid to date: ${sum(p['amount'] for p in mp.paid):,.2f}")
    elif c == "payout":
        amount = round(mp.balances.get(a.contributor, 0.0), 2)
        if amount <= 0:
            raise IntakeError(f"{a.contributor} has no balance to pay")
        mp.paid.append(
            {"contributor": a.contributor, "amount": amount, "reference": a.reference, "ts": int(time.time())}
        )
        mp.balances[a.contributor] = 0.0
        print(f"recorded ${amount:,.2f} paid to {a.contributor} ({a.reference})")
    else:
        text = mp.export_manifest()
        print(text if text else "no accepted clips yet")
    return 0


def _unpaid(store: str) -> dict:
    """Each contributor's unpaid balance (manual `payout` and Connect payouts both lower it)."""
    return {c: v for c, v in load(store).balances.items() if v > 0}


def _settle(store: str, contributor: str, amount: float, transfer_id: str):
    """A Connect transfer is a payout in this ledger too, so `payout` can never pay it again."""
    mp = load(store)
    mp.balances[contributor] = round(mp.balances.get(contributor, 0.0) - amount, 2)
    mp.paid.append({"contributor": contributor, "amount": amount, "reference": transfer_id, "ts": int(time.time())})
    save(mp, store)
