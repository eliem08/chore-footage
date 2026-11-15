import contextlib
import io
import json
import os
import tempfile
import unittest

from chore_footage.__main__ import main
from chore_footage.ops import load

GOOD = ["--seconds", "120", "--resolution", "1080p", "--fps", "30", "--hands-visible", "0.9", "--lighting", "0.9"]


def run(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = main(list(argv))
    return code, out.getvalue()


class IntakeOpsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "footage.json")
        self.s = ["--store", self.path]

    def tearDown(self):
        self.tmp.cleanup()

    def clip(self, name, data):
        path = os.path.join(self.tmp.name, name)
        with open(path, "wb") as fh:
            fh.write(data)
        return path

    def ok(self, *argv):
        code, out = run(*argv, *self.s)
        self.assertEqual(code, 0, out)
        return out

    def test_accepted_clip_pays_and_the_same_file_is_never_paid_twice(self):
        a = self.clip("a.mp4", b"video-bytes-1")
        out = self.ok("submit", "ana", "fold-laundry", a, *GOOD, "--consent-signed")
        self.assertIn("ACCEPTED", out)
        self.assertIn("$3.75", out)  # 2 min x $1.50 x 1.25 quality bonus
        renamed = self.clip("totally-new-name.mp4", b"video-bytes-1")
        code, out = run("submit", "ana", "fold-laundry", renamed, *GOOD, "--consent-signed", *self.s)
        self.assertEqual(code, 1)
        self.assertIn("already submitted", out)
        self.assertEqual(load(self.path).balances["ana"], 3.75)

    def test_consent_and_bystanders_are_hard_stops(self):
        a = self.clip("a.mp4", b"video-bytes-2")
        self.assertIn("consent not signed", run("submit", "bo", "fold-laundry", a, *GOOD, *self.s)[1])
        b = self.clip("b.mp4", b"video-bytes-3")
        argv = ["submit", "bo", "fold-laundry", b, *GOOD, "--consent-signed", "--bystander-faces", "1"]
        self.assertEqual(run(*argv, *self.s)[0], 1)
        self.assertEqual(load(self.path).balances.get("bo", 0), 0)

    def test_payout_zeroes_the_balance_and_manifest_lists_only_accepted_clips(self):
        self.ok("submit", "ana", "fold-laundry", self.clip("a.mp4", b"v1"), *GOOD, "--consent-signed")
        self.assertIn("recorded $3.75 paid to ana", self.ok("payout", "ana", "--reference", "wise-123"))
        self.assertEqual(run("payout", "ana", "--reference", "again", *self.s)[0], 1)
        self.assertIn("paid to date: $3.75", self.ok("balances"))
        rows = [json.loads(line) for line in self.ok("manifest").splitlines()]
        self.assertEqual((len(rows), rows[0]["consent"]), (1, True))

    def test_custom_bounty_and_refusals(self):
        self.ok("bounty-add", "water-plants", "--task", "Water house plants", "--pay-per-minute", "2")
        self.assertIn("water-plants", self.ok("status"))
        for argv in (
            ["bounty-add", "water-plants", "--task", "x", "--pay-per-minute", "2"],
            ["bounty-add", "bad", "--task", "x", "--pay-per-minute", "-1"],
            ["submit", "ana", "fold-laundry", self.clip("empty.mp4", b""), *GOOD, "--consent-signed"],
            ["submit", "ana", "no-such-bounty", self.clip("c.mp4", b"v9"), *GOOD, "--consent-signed"],
        ):
            with self.subTest(argv=argv[:3]):
                self.assertEqual(run(*argv, *self.s)[0], 1)


if __name__ == "__main__":
    unittest.main()
