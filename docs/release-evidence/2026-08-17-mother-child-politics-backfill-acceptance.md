# Acceptance checklist

- Exact source commits and root APKG paths are allowlisted only for this approved backlog.
- Generic DYL deny and ZH2000 exact-clean-path protections remain intact.
- Static APKG inspection and SHA-256/content/template fingerprints run before publication.
- Accepted bytes materialize only under content-addressed `artifacts/**`.
- Feed remains commit-pinned and `latest.json` remains digest-bound.
- Public metadata uses `社区分享` and excludes internal Owner-Inbox implementation copy.
- Rollback uses the previous immutable feed referenced before this release.
