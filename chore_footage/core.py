"""Bounties, clip QA, consent and payouts for chore-video data collection."""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field

__all__ = ["Bounty", "Clip", "Review", "Marketplace", "DEFAULT_BOUNTIES"]

RES_ORDER = {"480p": 480, "720p": 720, "1080p": 1080, "4k": 2160}


@dataclass
class Bounty:
    bounty_id: str
    task: str
    pay_per_minute: float
    min_seconds: int
    max_seconds: int
    view: str = "egocentric"
    min_resolution: str = "1080p"
    min_fps: int = 30
    quota_minutes: float = 600


@dataclass
class Clip:
    clip_id: str
    contributor: str
    bounty_id: str
    seconds: float
    resolution: str
    fps: int
    view: str
    hands_visible_ratio: float
    lighting: float  # 0..1
    consent_signed: bool
    bystander_faces: int = 0
    content_hash: str = ""


@dataclass
class Review:
    accepted: bool
    quality: int
    payout: float
    reasons: list = field(default_factory=list)


DEFAULT_BOUNTIES = [
    Bounty("fold-laundry", "Fold a basket of mixed laundry", 1.50, 60, 900),
    Bounty("load-dishwasher", "Load a dishwasher from a full sink", 1.20, 60, 600),
    Bounty("make-bed", "Strip and make a bed with fresh sheets", 1.80, 120, 900),
    Bounty("tidy-room", "Tidy a cluttered room (third-person tripod)", 1.00, 120, 1200, view="third-person", min_resolution="720p"),
]


class Marketplace:
    def __init__(self, bounties: list[Bounty] | None = None):
        self.bounties = {b.bounty_id: b for b in (bounties or DEFAULT_BOUNTIES)}
        self.accepted: list[tuple[Clip, Review]] = []
        self.rejected: list[tuple[Clip, Review]] = []
        self.minutes_filled: dict[str, float] = defaultdict(float)
        self.balances: dict[str, float] = defaultdict(float)
        self._hashes: set[str] = set()

    def review(self, clip: Clip) -> Review:
        b = self.bounties.get(clip.bounty_id)
        if not b:
            return self._reject(clip, ["unknown bounty"])
        hard = []
        if not clip.consent_signed:
            hard.append("contributor consent not signed")
        if clip.bystander_faces:
            hard.append(f"{clip.bystander_faces} bystander face(s) without consent - blur or reshoot")
        if not (b.min_seconds <= clip.seconds <= b.max_seconds):
            hard.append(f"duration {clip.seconds:.0f}s outside {b.min_seconds}-{b.max_seconds}s")
        if RES_ORDER.get(clip.resolution, 0) < RES_ORDER[b.min_resolution]:
            hard.append(f"resolution {clip.resolution} below {b.min_resolution}")
        if clip.fps < b.min_fps:
            hard.append(f"fps {clip.fps} below {b.min_fps}")
        if clip.view != b.view:
            hard.append(f"view {clip.view} but bounty requires {b.view}")
        if clip.content_hash and clip.content_hash in self._hashes:
            hard.append("duplicate submission")
        if self.minutes_filled[b.bounty_id] >= b.quota_minutes:
            hard.append("bounty quota filled")

        quality = round(100 * (0.6 * clip.hands_visible_ratio + 0.4 * clip.lighting))
        if quality < 50:
            hard.append(f"quality {quality} below 50 (hands visible {clip.hands_visible_ratio:.0%}, lighting {clip.lighting:.0%})")
        if hard:
            return self._reject(clip, hard, quality)

        minutes = min(clip.seconds / 60, b.quota_minutes - self.minutes_filled[b.bounty_id])
        bonus = 1.25 if quality >= 90 else 1.10 if quality >= 75 else 1.0
        payout = round(minutes * b.pay_per_minute * bonus, 2)
        reasons = [f"{minutes:.2f} min x ${b.pay_per_minute:.2f}" + (f" x {bonus} quality bonus" if bonus > 1 else "")]
        rev = Review(True, quality, payout, reasons)
        self.accepted.append((clip, rev))
        self.minutes_filled[b.bounty_id] += minutes
        self.balances[clip.contributor] += payout
        if clip.content_hash:
            self._hashes.add(clip.content_hash)
        return rev

    def _reject(self, clip, reasons, quality=0):
        rev = Review(False, quality, 0.0, reasons)
        self.rejected.append((clip, rev))
        return rev

    def export_manifest(self) -> str:
        lines = []
        for clip, rev in self.accepted:
            b = self.bounties[clip.bounty_id]
            lines.append(json.dumps({"clip_id": clip.clip_id, "task": b.task, "bounty": b.bounty_id, "seconds": clip.seconds,
                                     "view": clip.view, "resolution": clip.resolution, "fps": clip.fps, "quality": rev.quality,
                                     "consent": True}))
        return "\n".join(lines)
