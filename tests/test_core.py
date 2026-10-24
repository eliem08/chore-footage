import json
import unittest

from chore_footage import Bounty, Clip, Marketplace


def clip(**kw):
    base = dict(
        clip_id="c",
        contributor="u",
        bounty_id="b",
        seconds=120,
        resolution="1080p",
        fps=30,
        view="egocentric",
        hands_visible_ratio=1.0,
        lighting=1.0,
        consent_signed=True,
        content_hash="",
    )
    base.update(kw)
    return Clip(**base)


class Tests(unittest.TestCase):
    def setUp(self):
        self.m = Marketplace([Bounty("b", "fold", 1.0, 60, 600, quota_minutes=3)])

    def test_accept_with_bonus(self):
        r = self.m.review(clip())
        self.assertTrue(r.accepted)
        self.assertEqual(r.payout, 2.5)  # 2 min x $1 x 1.25

    def test_hard_rejections(self):
        r = self.m.review(
            clip(consent_signed=False, bystander_faces=2, seconds=10, resolution="480p", fps=24, view="third-person")
        )
        self.assertFalse(r.accepted)
        self.assertEqual(len(r.reasons), 6)

    def test_duplicate_and_quota(self):
        self.m.review(clip(content_hash="x"))
        self.assertIn("duplicate submission", self.m.review(clip(content_hash="x")).reasons)
        r = self.m.review(clip(content_hash="y"))  # only 1 min of quota left
        self.assertEqual(r.payout, 1.25)
        self.assertIn("bounty quota filled", self.m.review(clip(content_hash="z")).reasons)

    def test_low_quality_and_manifest(self):
        self.assertFalse(self.m.review(clip(hands_visible_ratio=0.2, lighting=0.3)).accepted)
        self.m.review(clip(clip_id="ok"))
        rows = [json.loads(l) for l in self.m.export_manifest().splitlines()]
        self.assertEqual([r["clip_id"] for r in rows], ["ok"])


if __name__ == "__main__":
    unittest.main()
