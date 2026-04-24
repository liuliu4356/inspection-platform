# Development Workflow

## Goal

Keep delivery predictable while the platform evolves from MVP to production.

## Iteration flow

1. Confirm the scope of the iteration.
2. Break the work into API, model, execution, and UI slices.
3. Implement the smallest end-to-end slice first.
4. Run local validation before commit.
5. Open a pull request with a clear change summary and rollout notes.
6. Merge to `main` only after CI passes.
7. Tag a release when the changelog and version metadata are updated.

## Branch strategy

- `main`: always releasable
- `feature/<topic>`: normal feature work
- `fix/<topic>`: production or regression fixes
- `chore/<topic>`: tooling, docs, CI, housekeeping

## Commit convention

Use Conventional Commits:

- `feat: add prometheus query validator`
- `fix: handle datasource test timeout`
- `docs: document release workflow`
- `chore: update CI job`

## Pull request checklist

- Scope is limited to one logical change.
- API, schema, and model changes are aligned.
- `CHANGELOG.md` is updated for user-visible changes.
- Local checks were run.
- Risk and rollback notes are included in the PR description.

## Definition of done

- Code is committed on a topic branch.
- CI passes.
- Docs and changelog reflect the change.
- Version bump decision is explicit.
- Merge or release note is recorded.

## Suggested milestones

1. Backend foundation and persistence
2. Datasource connectivity and rule management
3. Job execution engine and findings
4. Report generation and historical comparison
5. Frontend control plane
6. Observability, hardening, and release automation

