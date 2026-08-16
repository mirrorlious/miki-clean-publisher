#!/usr/bin/env python3
"""Ingest Owner Inbox APKGs into the trusted Clean Publisher.

The source repository is untrusted input. This module never executes template
JavaScript. It discovers root APKGs with NUL-delimited Git paths, statically
inspects them, deterministically classifies family/release/variant identity,
and copies only accepted bytes into content-addressed Clean Publisher paths.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path, PurePosixPath

import publish_miki_owner_pack as engine

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "miki-publisher.json"
HEX40_RE = re.compile(r"^[0-9a-f]{40}$", re.I)
VERSION_RE = re.compile(r"(?:^|[-_\s])v(\d+(?:\.\d+)*)$", re.I)
STYLE_PATTERNS = (
    (re.compile(r"(?:[-_\s]*)(水墨青)(?:[-_\s]*)$", re.I), "shuimo", "水墨青"),
    (re.compile(r"(?:[-_\s]*)(法典红)(?:[-_\s]*)$", re.I), "fadian-red", "法典红"),
    (re.compile(r"(?:[-_\s]*)(原版|original)(?:[-_\s]*)$", re.I), "original", "原版"),
)
DEFAULT_DENY_TOKENS = ("zh2000", "dyl")


def git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])


def git_text(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, encoding="utf-8"
    )


def normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip()


def parse_filename(path: str) -> dict:
    stem = normalize_text(Path(PurePosixPath(path).name).stem)
    base = stem
    variant_id = "original"
    variant_label = "原版"
    for pattern, candidate_id, candidate_label in STYLE_PATTERNS:
        match = pattern.search(base)
        if match:
            base = base[: match.start()].rstrip("-_ ")
            variant_id = candidate_id
            variant_label = candidate_label
            break

    explicit_version = ""
    version_match = VERSION_RE.search(base)
    if version_match:
        explicit_version = version_match.group(1)
        base = base[: version_match.start()].rstrip("-_ ")

    title = base or stem
    family_key = "".join(char.casefold() for char in title if char.isalnum())
    if not family_key:
        family_key = hashlib.sha256(title.encode("utf-8")).hexdigest()

    ascii_only = all(ord(char) < 128 for char in title)
    if ascii_only:
        pack_id = engine.clean_pack_id(title)
    else:
        digest = hashlib.sha256(family_key.encode("utf-8")).hexdigest()[:12]
        pack_id = f"owner-pack-{digest}"

    return {
        "title": title,
        "familyKey": family_key,
        "packId": pack_id,
        "variantId": variant_id,
        "variantLabel": variant_label,
        "explicitVersion": explicit_version,
    }


def ensure_source_repo(source_dir: Path, repository: str, branch: str) -> None:
    if (source_dir / ".git").exists():
        subprocess.check_call([
            "git", "-C", str(source_dir), "fetch", "--filter=blob:none",
            "--no-tags", "origin", branch,
        ])
        return
    source_dir.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call([
        "git", "clone", "--filter=blob:none", "--no-checkout", "--single-branch",
        "--branch", branch, f"https://github.com/{repository}.git", str(source_dir),
    ])


def ensure_commit(source_dir: Path, commit: str) -> None:
    if not HEX40_RE.fullmatch(commit or ""):
        raise RuntimeError(f"invalid source commit: {commit!r}")
    probe = subprocess.run(
        ["git", "-C", str(source_dir), "cat-file", "-e", f"{commit}^{{commit}}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if probe.returncode == 0:
        return
    subprocess.check_call([
        "git", "-C", str(source_dir), "fetch", "--filter=blob:none",
        "--no-tags", "origin", commit,
    ])


def resolve_head(source_dir: Path, branch: str) -> str:
    value = git_text(source_dir, "rev-parse", f"origin/{branch}").strip().lower()
    if not HEX40_RE.fullmatch(value):
        raise RuntimeError(f"invalid source head: {value!r}")
    return value


def changed_root_apkgs(source_dir: Path, before: str, head: str) -> list[str]:
    if before == head:
        return []
    ensure_commit(source_dir, before)
    raw = git_bytes(
        source_dir, "diff", "--name-only", "-z", "--diff-filter=AM",
        before, head, "--",
    )
    names = []
    for part in raw.split(b"\0"):
        if not part:
            continue
        name = part.decode("utf-8", errors="strict").replace("\\", "/")
        if "/" not in name and name.lower().endswith(".apkg"):
            names.append(name)
    return sorted(set(names))


def latest_path_commit(source_dir: Path, head: str, path: str) -> str:
    value = git_text(source_dir, "log", "-1", "--format=%H", head, "--", path).strip().lower()
    if not HEX40_RE.fullmatch(value):
        raise RuntimeError(f"cannot resolve source commit for {path}")
    return value


def read_blob(source_dir: Path, commit: str, path: str) -> bytes:
    ensure_commit(source_dir, commit)
    return git_bytes(source_dir, "show", f"{commit}:{path}")


def sha_prefixed(value: str) -> str:
    raw = str(value or "")
    return raw if raw.startswith("sha256:") else f"sha256:{raw}"


def release_content_fp(release: dict) -> str:
    evidence = release.get("classificationEvidence") or {}
    value = str(evidence.get("contentFingerprint") or "")
    if value:
        return sha_prefixed(value)
    variants = release.get("variants") or []
    if variants:
        value = str((variants[0].get("autoIdentity") or {}).get("contentFingerprint") or "")
        if value:
            return sha_prefixed(value)
    return ""


def variant_template_fp(variant: dict) -> str:
    value = str((variant.get("autoIdentity") or {}).get("templateFingerprint") or "")
    return sha_prefixed(value) if value else ""


def next_release_id(pack: dict) -> str:
    values = []
    for release in pack.get("releases", []):
        match = re.fullmatch(r"v(\d+)", str(release.get("releaseId") or ""), re.I)
        if match:
            values.append(int(match.group(1)))
    return f"v{max(values, default=0) + 1}"


def unique_variant_id(release: dict, preferred: str, template_fp: str) -> str:
    existing = {str(item.get("variantId") or "") for item in release.get("variants", [])}
    if preferred not in existing:
        return preferred
    suffix = template_fp.removeprefix("sha256:")[:8]
    candidate = f"{preferred}-{suffix}"
    if candidate not in existing:
        return candidate
    index = 2
    while f"{candidate}-{index}" in existing:
        index += 1
    return f"{candidate}-{index}"


def artifact_relative_path(pack_id: str, release_id: str, variant_id: str, sha256: str) -> str:
    return f"artifacts/{pack_id}/{release_id}/{variant_id}-{sha256[:12]}.apkg"


def pending_entry(source_repo: str, commit: str, path: str, reason: str, detail: str) -> dict:
    return {
        "sourceRepository": source_repo,
        "sourceCommit": commit,
        "sourcePath": path,
        "status": "PENDING_CLASSIFICATION",
        "reason": reason,
        "detail": detail,
    }


def upsert_pending(config: dict, entry: dict) -> None:
    config["pendingClassification"] = [
        item for item in config.get("pendingClassification", [])
        if not (
            item.get("sourceRepository") == entry.get("sourceRepository")
            and item.get("sourceCommit") == entry.get("sourceCommit")
            and item.get("sourcePath") == entry.get("sourcePath")
        )
    ] + [entry]


def clear_pending(config: dict, source_repo: str, commit: str, path: str) -> None:
    config["pendingClassification"] = [
        item for item in config.get("pendingClassification", [])
        if not (
            item.get("sourceRepository") == source_repo
            and item.get("sourceCommit") == commit
            and item.get("sourcePath") == path
        )
    ]


def denied(path: str, tokens: list[str]) -> str | None:
    folded = normalize_text(path).casefold()
    for token in tokens:
        if normalize_text(token).casefold() in folded:
            return token
    return None


def find_content_matches(config: dict, content_fp: str) -> list[tuple[dict, dict]]:
    wanted = sha_prefixed(content_fp)
    return [
        (pack, release)
        for pack in config.get("packs", [])
        for release in pack.get("releases", [])
        if release_content_fp(release) == wanted
    ]


def find_family_matches(config: dict, family_key: str) -> list[dict]:
    return [
        pack for pack in config.get("packs", [])
        if str((pack.get("autoIdentity") or {}).get("familyKey") or "") == family_key
    ]


def make_variant(parsed: dict, artifact_path: str, source_repo: str, source_commit: str,
                 source_path: str, provenance: str, content_fp: str, template_fp: str,
                 variant_id: str) -> dict:
    return {
        "variantId": variant_id,
        "label": parsed["variantLabel"],
        "sourcePath": artifact_path,
        "origin": {
            "repository": source_repo,
            "commit": source_commit,
            "path": source_path,
            "provenance": provenance,
        },
        "autoIdentity": {
            "familyKey": parsed["familyKey"],
            "contentFingerprint": sha_prefixed(content_fp),
            "templateFingerprint": sha_prefixed(template_fp),
        },
    }


def write_artifact(root: Path, relative: str, data: bytes) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)


def classify_and_bind(config: dict, root: Path, parsed: dict, inspection: dict,
                      source_repo: str, source_commit: str, source_path: str,
                      provenance: str, artifact_bytes: bytes) -> tuple[str, str]:
    content_fp = sha_prefixed(inspection["contentFingerprint"])
    template_fp = sha_prefixed(inspection["templateFingerprint"])
    content_matches = find_content_matches(config, content_fp)
    family_matches = find_family_matches(config, parsed["familyKey"])
    if len(content_matches) > 1:
        raise ValueError("content fingerprint matches multiple releases")
    if len(family_matches) > 1:
        raise ValueError("family key matches multiple pack families")

    if content_matches:
        pack, release = content_matches[0]
        known_key = str((pack.get("autoIdentity") or {}).get("familyKey") or "")
        if known_key and known_key != parsed["familyKey"]:
            raise ValueError("content fingerprint conflicts with deterministic family key")
        for existing in release.get("variants", []):
            if variant_template_fp(existing) == template_fp:
                return "duplicate", str(existing.get("sourcePath") or "")
        variant_id = unique_variant_id(release, parsed["variantId"], template_fp)
        relative = artifact_relative_path(pack["packId"], release["releaseId"], variant_id, inspection["sha256"])
        write_artifact(root, relative, artifact_bytes)
        release.setdefault("variants", []).append(make_variant(
            parsed, relative, source_repo, source_commit, source_path, provenance,
            content_fp, template_fp, variant_id,
        ))
        return "variant", relative

    if family_matches:
        pack = family_matches[0]
        release_id = next_release_id(pack)
        for release in pack.get("releases", []):
            if str(release.get("status") or "").upper() == "ACTIVE":
                release["status"] = "ARCHIVED"
        variant_id = parsed["variantId"]
        relative = artifact_relative_path(pack["packId"], release_id, variant_id, inspection["sha256"])
        write_artifact(root, relative, artifact_bytes)
        pack.setdefault("releases", []).append({
            "releaseId": release_id,
            "displayVersion": parsed["explicitVersion"] or release_id.removeprefix("v"),
            "status": "ACTIVE",
            "defaultVariantId": variant_id,
            "classificationEvidence": {
                "contentFingerprint": content_fp,
                "templateFingerprint": template_fp,
                "autoDecision": "NEW_CONTENT_RELEASE",
                "basis": "Deterministic Owner Inbox family key matched and semantic content fingerprint changed.",
            },
            "variants": [make_variant(
                parsed, relative, source_repo, source_commit, source_path, provenance,
                content_fp, template_fp, variant_id,
            )],
        })
        pack["currentReleaseId"] = release_id
        return "release", relative

    pack_id = parsed["packId"]
    existing_ids = {str(item.get("packId") or "") for item in config.get("packs", [])}
    if pack_id in existing_ids:
        pack_id = f"{pack_id}-{hashlib.sha256(parsed['familyKey'].encode('utf-8')).hexdigest()[:8]}"
        if pack_id in existing_ids:
            raise ValueError("deterministic packId collision")
    release_id = "v1"
    variant_id = parsed["variantId"]
    relative = artifact_relative_path(pack_id, release_id, variant_id, inspection["sha256"])
    write_artifact(root, relative, artifact_bytes)
    config.setdefault("packs", []).append({
        "packId": pack_id,
        "title": parsed["title"],
        "description": f"{parsed['title']}，由 Owner Inbox 自动静态审计并发布。",
        "author": "Owner 上传",
        "license": "仅供个人学习",
        "subject": "",
        "usageHint": "加入后可在 Miki 公共池中安装。",
        "autoIdentity": {
            "familyKey": parsed["familyKey"],
            "createdBy": "OWNER_INBOX_AUTO_PUBLISH_V1",
        },
        "currentReleaseId": release_id,
        "releases": [{
            "releaseId": release_id,
            "displayVersion": parsed["explicitVersion"] or "1",
            "status": "ACTIVE",
            "defaultVariantId": variant_id,
            "classificationEvidence": {
                "contentFingerprint": content_fp,
                "templateFingerprint": template_fp,
                "autoDecision": "NEW_FAMILY",
                "basis": "No existing semantic-content or deterministic-family-key match.",
            },
            "variants": [make_variant(
                parsed, relative, source_repo, source_commit, source_path, provenance,
                content_fp, template_fp, variant_id,
            )],
        }],
    })
    return "family", relative


def inspect_bytes(data: bytes) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as handle:
        handle.write(data)
        temp_path = Path(handle.name)
    try:
        return engine.inspect_apkg(temp_path)
    finally:
        temp_path.unlink(missing_ok=True)


def process_candidate(config: dict, root: Path, source_dir: Path, source_repo: str,
                      source_commit: str, source_path: str, provenance: str,
                      deny_tokens: list[str]) -> dict:
    token = denied(source_path, deny_tokens)
    if token:
        upsert_pending(config, pending_entry(
            source_repo, source_commit, source_path, "POLICY_DENIED",
            f"Auto-publish deny token matched: {token}. Bytes were not copied into Clean Publisher.",
        ))
        return {"status": "pending", "reason": "POLICY_DENIED", "sourcePath": source_path}

    try:
        parsed = parse_filename(source_path)
        artifact_bytes = read_blob(source_dir, source_commit, source_path)
        inspection = inspect_bytes(artifact_bytes)
        if inspection["sha256"] != hashlib.sha256(artifact_bytes).hexdigest():
            raise ValueError("source byte digest changed during inspection")
        action, artifact_path = classify_and_bind(
            config, root, parsed, inspection, source_repo, source_commit, source_path,
            provenance, artifact_bytes,
        )
        clear_pending(config, source_repo, source_commit, source_path)
        return {
            "status": action,
            "sourcePath": source_path,
            "artifactPath": artifact_path,
            "sha256": inspection["sha256"],
            "cardCount": inspection["cardCount"],
            "noteCount": inspection["noteCount"],
            "deckCount": inspection["deckCount"],
            "contentFingerprint": sha_prefixed(inspection["contentFingerprint"]),
            "templateFingerprint": sha_prefixed(inspection["templateFingerprint"]),
        }
    except Exception as error:
        upsert_pending(config, pending_entry(
            source_repo, source_commit, source_path, "AMBIGUOUS_OR_INVALID",
            f"Static ingestion/classification failed closed: {type(error).__name__}: {error}",
        ))
        return {"status": "pending", "reason": "AMBIGUOUS_OR_INVALID", "sourcePath": source_path}


def sync(config_path: Path, root: Path, source_dir: Path) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source = config.get("sourceInbox") or {}
    source_repo = str(source.get("repository") or "").strip()
    branch = str(source.get("branch") or "main").strip()
    before = str(source.get("lastSeenCommit") or "").strip().lower()
    if not source_repo or not HEX40_RE.fullmatch(before):
        raise SystemExit("sourceInbox.repository and 40-hex lastSeenCommit are required")

    ensure_source_repo(source_dir, source_repo, branch)
    head = resolve_head(source_dir, branch)
    ensure_commit(source_dir, before)
    deny_tokens = [str(item) for item in source.get("denyTokens") or DEFAULT_DENY_TOKENS]

    candidates: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in source.get("bootstrap") or []:
        commit = str(item.get("sourceCommit") or "").lower()
        path = str(item.get("sourcePath") or "").replace("\\", "/")
        provenance = str(item.get("provenance") or "OWNER_UPLOAD_ASSERTION")
        key = (commit, path)
        if HEX40_RE.fullmatch(commit) and "/" not in path and path.lower().endswith(".apkg") and key not in seen:
            candidates.append((commit, path, provenance))
            seen.add(key)

    for path in changed_root_apkgs(source_dir, before, head):
        commit = latest_path_commit(source_dir, head, path)
        key = (commit, path)
        if key not in seen:
            candidates.append((commit, path, "OWNER_UPLOAD_ASSERTION"))
            seen.add(key)

    results = [
        process_candidate(config, root, source_dir, source_repo, commit, path, provenance, deny_tokens)
        for commit, path, provenance in candidates
    ]
    source["lastSeenCommit"] = head
    source["bootstrap"] = []
    config["sourceInbox"] = source
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "changed": bool(candidates) or before != head,
        "sourceHead": head,
        "candidateCount": len(candidates),
        "packCount": len(config.get("packs", [])),
        "pendingCount": len(config.get("pendingClassification", [])),
        "results": results,
    }


def emit_outputs(result: dict) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"changed={'true' if result['changed'] else 'false'}\n")
        handle.write(f"source_head={result['sourceHead']}\n")
        handle.write(f"candidate_count={result['candidateCount']}\n")
        handle.write(f"pack_count={result['packCount']}\n")
        handle.write(f"pending_count={result['pendingCount']}\n")


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
    result = sync(config_path, root, source_dir)
    emit_outputs(result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Owner Inbox sync: candidates={result['candidateCount']} packs={result['packCount']} "
            f"pending={result['pendingCount']} sourceHead={result['sourceHead']}"
        )


if __name__ == "__main__":
    main()
