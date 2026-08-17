# 2026-08-17 Owner-approved APKG backfill

Status: ASSET_RELEASE_CANDIDATE

## Approved sources

- `QY于越刑法母子题v4.5记忆卡片_母子题跳转版.apkg`
  - source repository: `mirrorlious/ankicardsfo1po`
  - source commit: `d2d718137426bb693ebdb141c5b7f56c1dbb99cf`
  - intended identity: `qy-lsat-criminal-law-parent-child` / release `4.5` / variant `linked`
- `27政治xutao强化课阶段测_水墨青总包_五科01史纲_02思修_03马原_04毛中特_05新思想165题.apkg`
  - source repository: `mirrorlious/ankicardsfo1po`
  - source commit: `806ed26bd6a1b2e74aaa22f08bc0a3d0c76e65b1`
  - intended identity: `postgrad-politics-xutao-stage-tests` / release `2027` / variant `shuimo`

## Publication boundary

These files predate the Clean Publisher polling cursor and are therefore admitted only through the exact-path + exact-commit approved backfill list in `scripts/sync_owner_inbox_safe.py`.

The normal Clean Publisher static inspection, semantic-content/template fingerprint classification, content-addressed artifact copy, manifest/report generation, SHA-256 identity, immutable feed and digest-bound `latest.json` publication remain mandatory. DYL remains denied and the ZH2000 exact-clean-path restriction remains unchanged.

## User-facing metadata

New and existing Owner-Inbox-derived packs are normalized to author `社区分享`. Internal publication implementation wording such as `Owner 上传` / `Owner Inbox` is not intended for the public catalog.

## Rollback

Rollback is the previous immutable Clean Publisher feed commit referenced by the pre-release `miki-public/latest.json`; no history rewrite or artifact overwrite is required.
