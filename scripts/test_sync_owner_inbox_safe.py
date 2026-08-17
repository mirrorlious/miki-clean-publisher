from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sync_owner_inbox_safe as safe


class CleanZh2000PolicyTest(unittest.TestCase):
    def test_exact_clean_path_is_allowed(self):
        safe.validate_candidate_paths(["zh2000v2.apkg"])

    def test_legacy_zh2000_paths_are_denied(self):
        for path in (
            "ZH2000_apkg.apkg",
            "ZH2000_apkg-v2.apkg",
            "ZH2000-v3.apkg",
            "zh2000_other.apkg",
        ):
            with self.subTest(path=path):
                with self.assertRaises(RuntimeError):
                    safe.validate_candidate_paths([path])

    def test_clean_path_gets_stable_safe_identity(self):
        parsed = safe.parse_filename("zh2000v2.apkg")
        self.assertEqual(parsed["title"], "27法硕 ZH2000 清洗版")
        self.assertEqual(parsed["familyKey"], "zh2000-clean")
        self.assertEqual(parsed["packId"], "zh2000-clean")
        self.assertEqual(parsed["variantId"], "clean")
        self.assertEqual(parsed["variantLabel"], "清洗版")

    def test_mother_child_backfill_gets_stable_identity(self):
        parsed = safe.parse_filename(safe.MOTHER_CHILD_PATH)
        self.assertEqual(parsed["title"], "QY 于越刑法母子题")
        self.assertEqual(parsed["packId"], "qy-lsat-criminal-law-parent-child")
        self.assertEqual(parsed["variantId"], "linked")
        self.assertEqual(parsed["explicitVersion"], "4.5")

    def test_politics_backfill_gets_stable_identity(self):
        parsed = safe.parse_filename(safe.POLITICS_XUTAO_PATH)
        self.assertEqual(parsed["title"], "27政治徐涛强化课阶段测")
        self.assertEqual(parsed["packId"], "postgrad-politics-xutao-stage-tests")
        self.assertEqual(parsed["variantId"], "shuimo")

    def test_approved_backfills_are_added_once_and_skip_published_origins(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "miki-publisher.json"
            path.write_text(json.dumps({
                "sourceInbox": {"bootstrap": []},
                "packs": [{
                    "releases": [{
                        "variants": [{"origin": {"path": safe.POLITICS_XUTAO_PATH}}]
                    }]
                }],
            }, ensure_ascii=False), encoding="utf-8")
            safe.ensure_approved_backfills(path)
            config = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(config["sourceInbox"]["bootstrap"]), 1)
            self.assertEqual(config["sourceInbox"]["bootstrap"][0]["sourcePath"], safe.MOTHER_CHILD_PATH)
            safe.ensure_approved_backfills(path)
            config = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(config["sourceInbox"]["bootstrap"]), 1)

    def test_public_metadata_hides_internal_owner_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "miki-publisher.json"
            path.write_text(json.dumps({
                "packs": [{
                    "title": "测试卡组",
                    "author": "Owner 上传",
                    "description": "测试卡组，由 Owner Inbox 自动静态审计并发布。",
                }]
            }, ensure_ascii=False), encoding="utf-8")
            safe.sanitize_public_metadata(path)
            pack = json.loads(path.read_text(encoding="utf-8"))["packs"][0]
            self.assertEqual(pack["author"], "社区分享")
            self.assertNotIn("Owner", pack["description"])
            self.assertNotIn("Inbox", pack["description"])

    def test_non_special_path_keeps_generic_parser(self):
        parsed = safe.parse_filename("2027法硕法基强化题-水墨青.apkg")
        self.assertEqual(parsed["title"], "2027法硕法基强化题")
        self.assertEqual(parsed["variantId"], "shuimo")


if __name__ == "__main__":
    unittest.main()
