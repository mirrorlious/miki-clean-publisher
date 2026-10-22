import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from public_pool_preview import candidate_fields, verified_preview


class PublicPoolPreviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = {"schemaVersion": 1, "packId": "sample", "resourceVersion": "v1", "chapters": [{"id": "chapter-1", "title": "第一章", "cardCount": 10}], "cards": [{"front": "题", "back": "答案", "chapterId": "chapter-1"} for _ in range(3)]}
        self.item = {"packId": "sample", "resourceVersion": "v1"}

    def write_sample(self):
        data = json.dumps(self.payload, ensure_ascii=False).encode()
        digest = hashlib.sha256(data).hexdigest()
        relative = f"miki-public/previews/{digest}.preview.json"
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        self.item["preview"] = {"url": relative, "sizeBytes": len(data), "sha256": digest, "cardCount": 3}
        return target

    def test_legacy_has_no_preview_and_valid_sample_is_identity_bound(self):
        self.assertIsNone(verified_preview(self.root, self.item))
        self.write_sample()
        self.assertEqual(verified_preview(self.root, self.item), self.item["preview"])
        self.item["resourceVersion"] = "other"
        with self.assertRaises(ValueError):
            verified_preview(self.root, self.item)

    def test_corruption_oversize_and_traversal_fail_closed(self):
        target = self.write_sample()
        target.write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            verified_preview(self.root, self.item)
        self.write_sample()
        for patch in [{"url": "../escape.preview.json"}, {"sizeBytes": 131073}, {"cardCount": 6}]:
            old = dict(self.item["preview"])
            self.item["preview"].update(patch)
            with self.assertRaises(ValueError):
                verified_preview(self.root, self.item)
            self.item["preview"] = old

    def test_personal_state_and_unbounded_directory_are_rejected(self):
        self.payload["cards"][0]["review"] = {}
        self.write_sample()
        with self.assertRaises(ValueError):
            verified_preview(self.root, self.item)

        del self.payload["cards"][0]["review"]
        self.payload["chapters"] *= 129
        self.write_sample()
        with self.assertRaises(ValueError):
            verified_preview(self.root, self.item)

    def test_candidate_binds_exact_source_release_variant_and_renderer(self):
        self.write_sample()
        self.item.update(releaseId="v1", variantId="original", sourceSha256="b" * 64)
        registry = {"schemaVersion": 1, "renderer": {"repository": "mirrorlious/miki-", "commit": "a" * 40}, "entries": [dict(self.item)]}
        target = self.root / "miki-preview-candidates.json"
        target.write_text(json.dumps(registry), encoding="utf-8")
        self.assertEqual(candidate_fields(self.root, self.item)["preview"], self.item["preview"])
        self.assertEqual(candidate_fields(self.root, {**self.item, "sourceSha256": "c" * 64}), {})
        self.assertEqual(candidate_fields(self.root, {**self.item, "variantId": "other"}), {})
        registry["entries"] *= 2
        target.write_text(json.dumps(registry), encoding="utf-8")
        with self.assertRaises(ValueError):
            candidate_fields(self.root, self.item)
