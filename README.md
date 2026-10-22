# Miki Clean Publisher

Clean public Owner Publisher repository for Miki.

## Policy

- Starts from a clean Git history and does **not** fork or inherit `mirrorlious/ankicardsfo1po` history.
- `mirrorlious/ankicardsfo1po` is an **Owner Inbox**, not a Miki trust source. Miki never consumes its feed or APKG URLs directly.
- Root `.apkg` files uploaded to the configured Owner Inbox after the stored cursor are polled automatically. Accepted bytes are copied into content-addressed `artifacts/**` paths in this clean repository before publication.
- `OWNER_UPLOAD_ASSERTION` means the configured Owner deliberately uploaded that artifact for publication. It is an Owner publication assertion, **not an independent copyright-verification claim**.
- `UNKNOWN`, conflicting, invalid or ambiguous artifacts fail closed to `pendingClassification`; their bytes are not copied into the trusted artifact tree.
- `zh2000` and `dyl` are hard-denied from Owner Inbox automatic ingestion. ZH2000 remains **NOT PUBLISHED** until a separate copyright-safe release is explicitly approved; DYL remains on its private distribution path.
- Template JavaScript is never executed by the publisher. Existing fields-only / SHA256 / immutable provenance / raw-JavaScript-disabled gates remain mandatory.

## Automatic identity

The stable model remains:

```text
Pack Family → Content Release → Skin/Template Variant → immutable APKG
```

Automatic classification uses semantic content fingerprint + template fingerprint + a persisted deterministic family key derived from the presentation filename after removing known skin/version suffixes.

- same semantic content + different template → new variant in the same release;
- same deterministic family + changed semantic content → new ACTIVE release, previous ACTIVE release becomes ARCHIVED;
- no existing semantic/family match → new family v1;
- conflicting/multiple matches → pending, never guessed into the public feed.

Filename is only a deterministic family-name candidate; it is not artifact identity. Artifact identity is the clean content-addressed path + SHA256 + immutable Git provenance.

## Automatic discovery pointer

`miki-public/latest.json` is a mutable **discovery pointer only**. It contains:

- trusted repository id;
- a full 40-hex immutable feed commit;
- exact `miki-public/index.json` path;
- SHA256 of those feed bytes.

Miki must fetch the feed at that immutable commit and verify its digest before parsing it. Miki must never trust `miki-public/index.json` from mutable `main` directly.

## Layout

- `artifacts/**` — content-addressed accepted APKG bytes copied into Clean Publisher.
- `miki-public/index.json` — generated Owner Feed; each published snapshot is consumed through an immutable commit.
- `miki-public/latest.json` — mutable digest-bound locator for the latest immutable feed snapshot.
- `miki-publisher.json` — pack authorization/identity registry + Owner Inbox cursor.
- `.miki-publish-state.json` — generated publisher state.
- `scripts/sync_owner_inbox.py` — static Owner Inbox ingestion/classification.
- `scripts/publish_latest_pointer.py` — latest-pointer generator.
- `.github/workflows/miki-owner-publisher.yml` — PR validation, five-minute polling and publication workflow.
<!-- manual-owner-inbox-refresh: 2026-10-09-juexiao-5000 -->

## Bounded Public Pool previews

The remote workflow materializes presentation-only preview files through an
immutable revision of Miki's existing APKG parser and static renderer. It never
executes source template JavaScript. Only current ACTIVE variants get samples;
the original APKG bytes, fingerprints and access semantics are unchanged.

Each content-addressed `miki-public/previews/<sha256>.preview.json` has 3–5
sample cards, at most 128 KiB, and an actual deck-derived chapter directory
(at most 128 top-level groups). Samples identify their chapter and are chosen
across chapters; opening the directory never fetches full chapter bodies.
Shared template CSS is stored once. The Feed descriptor carries exact size,
SHA256, card count and a path pinned to the same commit as its manifest.

The generated sample is validated again before Feed construction: source
pack/resource identity, byte length, digest, finite sample count, bounded
chapters and presentation-only fields must match. Existing immutable samples
are retained for rollback; a different payload cannot overwrite their path.
The manifest/sample snapshot is committed before the Feed, and the existing
digest-bound latest pointer advances only after that Feed commit exists.

The Owner confirmed the current public catalog edition is 2027 on 2026-10-22;
`defaults.versionYear` records this separately from publication dates and
content coverage. Future pack-specific `versionYear` may override it.

## 27肖1000政治anki卡组

五科1172题，统一名称；同一发布版本提供“纯文字解析”和“图片解析”，默认纯文字。两版题目、选项、答案和笔记GUID一致，解析呈现不同，分别保留真实内容指纹及文件SHA256。史纲“苹命”已修正为“革命”。校验记录见 [文字校验记录](audits/xiao1000-2027/text-verification.json)。
