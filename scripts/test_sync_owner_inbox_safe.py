from __future__ import annotations

import unittest

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

    def test_non_zh_path_keeps_generic_parser(self):
        parsed = safe.parse_filename("2027法硕法基强化题-水墨青.apkg")
        self.assertEqual(parsed["title"], "2027法硕法基强化题")
        self.assertEqual(parsed["variantId"], "shuimo")


if __name__ == "__main__":
    unittest.main()
