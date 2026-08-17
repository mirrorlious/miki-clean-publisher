#!/usr/bin/env python3
"""Fail-closed Owner Inbox policy wrapper for Clean Publisher.

The generic sync engine stays reusable. This wrapper adds production-only
source-name policy and stable identities for explicitly approved special lanes.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import sync_owner_inbox as sync

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "miki-publisher.json"
CLEAN_ZH2000_PATH = "zh2000v2.apkg"
MOTHER_CHILD_PATH = "QY于越刑法母子题v4.5记忆卡片_母子题跳转版.apkg"
POLITICS_XUTAO_PATH = "27政治xutao强化课阶段测_水墨青总包_五科01史纲_02思修_03马原_04毛中特_05新思想165题.apkg"
_ORIGINAL_PARSE_FILENAME = sync.parse_filename
_FORBIDDEN_DESCRIPTION = "由 Owner Inbox 自动静态审计并发布。"


def normalize_path(value: str) -> str:
    return sync.normalize_text(str(value or "").replace("\\", "/"))


def is_zh2000_path(path: str) -> bool:
    return "zh2000" in normalize_path(path).casefold()


def validate_candidate_paths(paths: list[str]) -> None:
    for path in paths:
        normalized = normalize_path(path)
        if is_zh2000_path(normalized) and normalized != CLEAN_ZH2000_PATH:
            raise RuntimeError(
                f"ZH2000 source path is not the Owner-approved clean channel: {normalized}"
            )


def parse_filename(path: str) -> dict:
    normalized = normalize_path(path)
    if normalized == CLEAN_ZH2000_PATH:
        return {
            "title": "27法硕 ZH2000 清洗版",
            "familyKey": "zh2000-clean",
            "packId": "zh2000-clean",
            "variantId": "clean",
            "variantLabel": "清洗版",
            "explicitVersion": "",
        }
    if normalized == MOTHER_CHILD_PATH:
        return {
            "title": "QY 于越刑法母子题",
            "familyKey": "qy-yuyue-criminal-law-parent-child",
            "packId": "qy-lsat-criminal-law-parent-child",
            "variantId": "linked",
            "variantLabel": "母子题跳转版",
            "explicitVersion": "4.5",
        }
    if normalized == POLITICS_XUTAO_PATH:
        return {
            "title": "27政治徐涛强化课阶段测",
            "familyKey": "postgrad-politics-xutao-stage-tests",
            "packId": "postgrad-politics-xutao-stage-tests",
            "variantId": "shuimo",
            "variantLabel": "水墨青",
            "explicitVersion": "2027",
        }
    return _ORIGINAL_PARSE_FILENAME(path)


def sanitize_public_metadata(config_path: Path) -> None:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    changed = False
    for pack in config.get("packs", []):
        if str(pack.get("author") or "").strip() in {"Owner", "Owner 上传", "Owner Inbox"}:
            pack["author"] = "社区分享"
            changed = True
        description = str(pack.get("description") or "")
        cleaned = description.replace(f"，{_FORBIDDEN_DESCRIPTION}", "。")
        cleaned = cleaned.replace(_FORBIDDEN_DESCRIPTION, "").strip()
        if cleaned != description:
            pack["description"] = cleaned
            changed = True
    if changed:
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def candidate_paths(config_path: Path, source_dir: Path) -> list[str]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = config.get("sourceInbox") or {}
    repository = str(source.get("repository") or "").strip()
    branch = str(source.get("branch") or "main").strip()
    before = str(source.get("lastSeenCommit") or "").strip().lower()
    if not repository or not sync.HEX40_RE.fullmatch(before):
        raise SystemExit("sourceInbox.repository and 40-hex lastSeenCommit are required")

    sync.ensure_source_repo(source_dir, repository, branch)
    head = sync.resolve_head(source_dir, branch)
    sync.ensure_commit(source_dir, before)

    paths: list[str] = []
    for item in source.get("bootstrap") or []:
        commit = str(item.get("sourceCommit") or "").lower()
        path = normalize_path(item.get("sourcePath") or "")
        if sync.HEX40_RE.fullmatch(commit) and "/" not in path and path.lower().endswith(".apkg"):
            paths.append(path)
    paths.extend(sync.changed_root_apkgs(source_dir, before, head))
    return sorted(set(paths))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(CONFIG_PATH))
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--source-dir", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    config_path = Path(args.config).resolve()
    source_dir = Path(args.source_dir).resolve() if args.source_dir else root / ".miki-owner-inbox"

    paths = candidate_paths(config_path, source_dir)
    validate_candidate_paths(paths)

    sync.parse_filename = parse_filename
    result = sync.sync(config_path, root, source_dir)
    sanitize_public_metadata(config_path)
    sync.emit_outputs(result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Safe Owner Inbox sync: candidates={result['candidateCount']} "
            f"packs={result['packCount']} pending={result['pendingCount']} "
            f"sourceHead={result['sourceHead']}"
        )


if __name__ == "__main__":
    main()
