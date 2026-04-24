# Versioning Policy

## Strategy

This repository uses Semantic Versioning:

- `MAJOR`: incompatible API or data model changes
- `MINOR`: backward-compatible feature additions
- `PATCH`: backward-compatible fixes, docs, or non-breaking tooling updates

## Current baseline

- Repository version: `0.1.0`
- Backend package version: `0.1.0`

## Release rules

- Every user-visible change must appear in `CHANGELOG.md`.
- `VERSION` and `backend/pyproject.toml` stay in sync.
- Release tags follow the format `vX.Y.Z`.

## Examples

- Add a new endpoint without breaking existing behavior: bump `MINOR`
- Fix a broken dry-run validation path: bump `PATCH`
- Rename stable API fields or change schema contracts: bump `MAJOR`

## Release steps

1. Update `CHANGELOG.md`
2. Bump version metadata
3. Commit the release change
4. Create tag `vX.Y.Z`
5. Push branch and tag to GitHub
6. Publish release notes from the changelog

## Helper script

Use the release helper:

```powershell
.\scripts\release.ps1 -Version 0.1.1
```

Or calculate by bump type:

```powershell
.\scripts\release.ps1 -Bump patch
```

