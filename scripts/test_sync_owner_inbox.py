from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import sync_owner_inbox as sync


class FilenameIdentityTest(unittest.TestCase):
    def test_chinese_shuimo_filename_has_stable_family(self):
        value = sync.parse_filename("2027法硕法基强化题-水墨青.apkg")
        self.assertEqual(value["title"], "2027法硕法基强化题")
        self.assertEqual(value["variantId"], "shuimo")
        self.assertEqual(value["variantLabel"], "水墨青")
        self.assertEqual(value["familyKey"], "2027法硕法基强化题")
        self.assertTrue(value["packId"].startswith("owner-pack-"))

    def test_version_is_removed_after_skin(self):
        value = sync.parse_filename("2027法硕法基强化题-v2-法典红.apkg")
        self.assertEqual(value["title"], "2027法硕法基强化题")
        self.assertEqual(value["explicitVersion"], "2")
        self.assertEqual(value["variantId"], "fadian-red")

    def test_zh2000_and_dyl_are_denied(self):
        self.assertEqual(sync.denied("ZH2000-v3.apkg", ["zh2000", "dyl"]), "zh2000")
        self.assertEqual(sync.denied("DYL强化题.apkg", ["zh2000", "dyl"]), "dyl")


class UnicodeGitDiscoveryTest(unittest.TestCase):
    def test_nul_diff_preserves_chinese_and_spaces(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        subprocess.check_call(["git", "init", "-q", str(root)])
        subprocess.check_call(["git", "-C", str(root), "config", "user.email", "test@example.invalid"])
        subprocess.check_call(["git", "-C", str(root), "config", "user.name", "test"])
        (root / "README.md").write_text("base", encoding="utf-8")
        subprocess.check_call(["git", "-C", str(root), "add", "README.md"])
        subprocess.check_call(["git", "-C", str(root), "commit", "-qm", "base"])
        before = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        filename = "2027 法硕法基强化题-水墨青.apkg"
        (root / filename).write_bytes(b"fixture")
        subprocess.check_call(["git", "-C", str(root), "add", "--", filename])
        subprocess.check_call(["git", "-C", str(root), "commit", "-qm", "asset"])
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        self.assertEqual(sync.changed_root_apkgs(root, before, head), [filename])


class ClassificationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base_inspection = {
            "sha256": "a" * 64,
            "contentFingerprint": "c" * 64,
            "templateFingerprint": "t" * 64,
        }
        self.origin = ("mirrorlious/ankicardsfo1po", "1" * 40, "2027法硕法基强化题-水墨青.apkg", "OWNER_UPLOAD_ASSERTION")

    def bind(self, config, parsed, inspection=None, data=b"x"):
        repo, commit, path, provenance = self.origin
        return sync.classify_and_bind(
            config, self.root, parsed, inspection or dict(self.base_inspection),
            repo, commit, path, provenance, data,
        )

    def test_new_family_then_new_skin_variant(self):
        config = {"packs": [], "pendingClassification": []}
        parsed = sync.parse_filename("2027法硕法基强化题-水墨青.apkg")
        action, artifact = self.bind(config, parsed)
        self.assertEqual(action, "family")
        self.assertTrue((self.root / artifact).is_file())
        pack = config["packs"][0]
        self.assertEqual(pack["currentReleaseId"], "v1")
        self.assertEqual(pack["releases"][0]["classificationEvidence"]["contentFingerprint"], "sha256:" + "c" * 64)

        other = dict(self.base_inspection, sha256="b" * 64, templateFingerprint="u" * 64)
        parsed2 = sync.parse_filename("2027法硕法基强化题-法典红.apkg")
        action, _ = self.bind(config, parsed2, other, b"y")
        self.assertEqual(action, "variant")
        self.assertEqual(len(pack["releases"][0]["variants"]), 2)

    def test_same_family_changed_content_creates_release_and_archives_old(self):
        config = {"packs": [], "pendingClassification": []}
        parsed = sync.parse_filename("2027法硕法基强化题-水墨青.apkg")
        self.bind(config, parsed)
        changed = dict(self.base_inspection, sha256="b" * 64, contentFingerprint="d" * 64)
        action, _ = self.bind(config, parsed, changed, b"y")
        pack = config["packs"][0]
        self.assertEqual(action, "release")
        self.assertEqual(pack["currentReleaseId"], "v2")
        self.assertEqual(pack["releases"][0]["status"], "ARCHIVED")
        self.assertEqual(pack["releases"][1]["status"], "ACTIVE")

    def test_same_content_and_template_is_duplicate(self):
        config = {"packs": [], "pendingClassification": []}
        parsed = sync.parse_filename("2027法硕法基强化题-水墨青.apkg")
        self.bind(config, parsed)
        action, _ = self.bind(config, parsed, dict(self.base_inspection, sha256="b" * 64), b"y")
        self.assertEqual(action, "duplicate")
        self.assertEqual(len(config["packs"][0]["releases"][0]["variants"]), 1)

    def test_content_match_with_conflicting_family_key_fails_closed(self):
        config = {"packs": [], "pendingClassification": []}
        parsed = sync.parse_filename("2027法硕法基强化题-水墨青.apkg")
        self.bind(config, parsed)
        conflicting = sync.parse_filename("完全不同资料-法典红.apkg")
        with self.assertRaises(ValueError):
            self.bind(config, conflicting, dict(self.base_inspection, sha256="b" * 64), b"y")

    def test_artifact_path_is_content_addressed(self):
        path = sync.artifact_relative_path("family", "v2", "shuimo", "abcdef123456" + "0" * 52)
        self.assertEqual(path, "artifacts/family/v2/shuimo-abcdef123456.apkg")


if __name__ == "__main__":
    unittest.main()
