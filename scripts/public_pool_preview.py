"""Verify bounded, immutable presentation samples before exposing them in Feed."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


def verified_preview(root: Path, item: dict) -> dict | None:
    descriptor = item.get("preview")
    if descriptor is None:
        return None
    digest = descriptor.get("sha256", "")
    size = descriptor.get("sizeBytes")
    count = descriptor.get("cardCount")
    expected_path = f"miki-public/previews/{digest}.preview.json"
    if (not re.fullmatch(r"[a-f0-9]{64}", digest)
            or type(size) is not int or not 0 < size <= 128 * 1024
            or type(count) is not int or not 3 <= count <= 5
            or descriptor.get("url") != expected_path):
        raise ValueError("Invalid bounded preview descriptor")
    data = (root / expected_path).read_bytes()
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError("Preview integrity mismatch")
    payload = json.loads(data)
    if (payload.get("schemaVersion") != 1 or payload.get("packId") != item["packId"]
            or payload.get("resourceVersion") != item["resourceVersion"]
            or not isinstance(payload.get("cards"), list) or len(payload["cards"]) != count
            or set(payload) - {"schemaVersion", "packId", "resourceVersion", "chapters", "cardCss", "cards"}):
        raise ValueError("Preview source identity mismatch")
    chapters = payload.get("chapters", [])
    if not isinstance(chapters, list) or len(chapters) > 128:
        raise ValueError("Preview chapter limit exceeded")
    ids = set()
    for chapter in chapters:
        if (not isinstance(chapter, dict) or set(chapter) != {"id", "title", "cardCount"}
                or not re.fullmatch(r"[a-z0-9-]{1,64}", chapter.get("id", ""))
                or chapter["id"] in ids or not isinstance(chapter.get("title"), str)
                or not 0 < len(chapter["title"]) <= 200
                or type(chapter.get("cardCount")) is not int or chapter["cardCount"] < 1):
            raise ValueError("Invalid preview chapter metadata")
        ids.add(chapter["id"])
    if not isinstance(payload.get("cardCss", ""), str):
        raise ValueError("Invalid preview stylesheet")
    for card in payload["cards"]:
        if (not isinstance(card, dict)
                or set(card) - {"chapterId", "front", "back", "frontHtml", "backHtml", "cardCss"}
                or any(not isinstance(value, str) for value in card.values())
                or not (card.get("front") or card.get("frontHtml"))
                or not (card.get("back") or card.get("backHtml"))
                or ("chapterId" in card and card["chapterId"] not in ids)):
            raise ValueError("Invalid presentation-only sample")
    return {"url": expected_path, "sizeBytes": size, "sha256": digest, "cardCount": count}
