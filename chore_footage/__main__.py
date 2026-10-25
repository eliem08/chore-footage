import argparse
import csv
import os
import sys

from .core import DEFAULT_BOUNTIES, Clip, Marketplace


def build_parser():
    ap = argparse.ArgumentParser(prog="chore-footage")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("bounties")
    sub.add_parser("demo")
    return ap


def _run(argv=None):
    ap = build_parser()
    a = ap.parse_args(argv)
    if a.cmd == "bounties":
        for b in DEFAULT_BOUNTIES:
            print(
                f"{b.bounty_id:<16} ${b.pay_per_minute:.2f}/min  {b.min_seconds}-{b.max_seconds}s  {b.view:<12} {b.min_resolution}@{b.min_fps}fps  {b.task}"
            )
        return 0
    m = Marketplace()
    clips = [
        Clip("c1", "maria", "fold-laundry", 480, "1080p", 30, "egocentric", 0.95, 0.9, True, content_hash="h1"),
        Clip("c2", "maria", "fold-laundry", 480, "1080p", 30, "egocentric", 0.95, 0.9, True, content_hash="h1"),
        Clip("c3", "dev", "make-bed", 300, "720p", 30, "egocentric", 0.8, 0.7, True, content_hash="h3"),
        Clip(
            "c4",
            "dev",
            "load-dishwasher",
            240,
            "4k",
            60,
            "egocentric",
            0.7,
            0.6,
            True,
            bystander_faces=1,
            content_hash="h4",
        ),
        Clip("c5", "sam", "tidy-room", 600, "1080p", 30, "third-person", 0.6, 0.8, True, content_hash="h5"),
    ]
    for c in clips:
        r = m.review(c)
        print(
            f"{c.clip_id} {c.bounty_id:<16} {'ACCEPT' if r.accepted else 'REJECT'} q={r.quality:<3} ${r.payout:.2f}  {'; '.join(r.reasons)}"
        )
    print("balances:", dict(m.balances))
    return 0


def main(argv=None):
    """Run the CLI; a bad input file or argument exits 2 with a one-line error instead of a traceback.

    Set AGENT_ECONOMY_DEBUG=1 to see the full traceback.
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    try:
        return _run(argv)
    except (OSError, ValueError, KeyError, csv.Error) as e:
        if os.environ.get("AGENT_ECONOMY_DEBUG"):
            raise
        msg = e.args[0] if isinstance(e, KeyError) and e.args else e
        print(f"error: {msg}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
