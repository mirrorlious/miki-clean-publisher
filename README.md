# Miki Clean Publisher

Clean public Owner Publisher repository for Miki.

## Policy

- Starts from a clean Git history.
- Does **not** fork or inherit `mirrorlious/ankicardsfo1po` history.
- First version intentionally publishes **no packs**.
- `zh2000` is **NOT PUBLISHED** until a separate copyright-safe re-release is approved.
- Only packs with verified provenance (`OWNER_AUTHORED`, `LICENSED`, or `REDISTRIBUTION_VERIFIED`) may be added.
- `UNKNOWN` provenance packs must not be added to the public feed.

## Layout

- `miki-public/index.json` — immutable Owner Feed (commit-pinned by Miki).
- `miki-publisher.json` — pack authorization registry.
- `.miki-publish-state.json` — generated publisher state.
- `scripts/` — publisher automation and tests.
- `.github/workflows/miki-owner-publisher.yml` — publisher validation/publish workflow.
