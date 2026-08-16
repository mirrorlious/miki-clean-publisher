from __future__ import annotations

import hashlib
import unittest

import publish_latest_pointer as latest


class LatestPointerTest(unittest.TestCase):
    def test_pointer_binds_exact_feed_commit_and_digest(self):
        feed = b'{"schemaVersion":1,"packs":[]}\n'
        commit = "a" * 40
        value = latest.build_pointer(commit, feed)
        self.assertEqual(value["schemaVersion"], 1)
        self.assertEqual(value["repository"], "mirrorlious/miki-clean-publisher")
        self.assertEqual(value["feedCommit"], commit)
        self.assertEqual(value["feedPath"], "miki-public/index.json")
        self.assertEqual(value["feedSha256"], hashlib.sha256(feed).hexdigest())

    def test_short_commit_is_rejected(self):
        with self.assertRaises(SystemExit):
            latest.build_pointer("abc", b"{}")


if __name__ == "__main__":
    unittest.main()
