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
