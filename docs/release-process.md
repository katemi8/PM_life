# Release Process

Этот документ описывает, как изменения попадают в `TA-agent-system`.

Основной читатель: агент и reviewer.

## Status

Active v0 process.

Target GitHub repo is `TrendPM/AI-Skills`: `https://github.com/TrendPM/AI-Skills`.

Initial publication may be pushed directly to `main` after final PM approval. After initial publication, every change must go through a pull request.

## Ownership

Each significant repo block has an owner:

- skill owner for `skills/<skill-name>`;
- MCP server owner for `.mcp/<server-name>`;
- contract owner for changed contracts;
- docs/process owner for changed process docs;
- example owner for changed examples.

Initial owner is the person who created and first pushed the block.

Owner may change by team agreement. Agents must not assign or change owners by themselves.

## Branching

Use these branch names:

- `skill/<skill-name>` for skill changes;
- `contract/<topic>` for process/contract changes;
- `docs/<topic>` for docs-only changes;
- `fix/<topic>` for small fixes.

## Pull Request Requirements

Every PR must include:

- problem being solved;
- files changed;
- affected skills/contracts/docs;
- PM-visible behavior changes;
- write/approval impact;
- validation evidence;
- rollout notes.

## Required Reviewers

Owner review is required.

Rules:

- if one owned block changes, its owner reviews;
- if multiple owned blocks change, all affected owners review;
- if a change touches analytics/metrics behavior, the metrics skill owner reviews;
- if a change touches MCP server code or local setup, the affected MCP server owner reviews;
- if a change touches Notion write approval, the affected skill owner and contract owner review;
- if a change touches release process or manifest rules, the repo/process owner reviews.

For the current initial publication and v0 release, owner/reviewer is `iakovlevi`.

## Required Checks

Run from repo root:

```powershell
python scripts\validate-skills.py
python scripts\smoke-skills.py
python scripts\validate-manifest.py
python scripts\scan-secrets.py
python -m json.tool .mcp.example.json
python -m json.tool .mcp\ktalk-readonly\ktalk-session.example.json
python -m json.tool manifest.json
python -m json.tool manifest.example.json
git diff --check
```

`git diff --check` is required after git initialization.

The same checks are automated in `.github/workflows/validate.yml` for pushes to `main` and pull requests.

After initial publication, repository settings must protect `main` and require the `validate` workflow before merge.

## Merge Rules

Merge is blocked if:

- any required check fails;
- owner review is missing;
- approval rules become weaker;
- MCP server changes introduce secret storage or unsafe external writes;
- raw KTalk transcript storage is introduced;
- Notion source-of-truth boundary is unclear;
- changed skill does not include updated examples or smoke-test expectations when behavior changes;
- manifest is stale for a release.

## Release Model

Every release should have:

- version tag, for example `v0.1.0`;
- release notes;
- updated `manifest.json`;
- commit SHA in GitHub release notes;
- migration notes when behavior changes.

## Manifest Update Rules

For each release:

1. Update root `version` when repo-level behavior changes.
2. Update changed skill versions.
3. Update `source.type` to `github-release`.
4. Set `source.tag` to the release tag.
5. Set `source.publicationStatus` to `released`.
6. Do not put the release commit SHA inside `manifest.json`; record it in GitHub release notes.

The published `main` baseline uses `source.type = github-release`, `source.branch = main`, `source.tag = v0.1.0` and `source.publicationStatus = released`.

## Release Notes

Release notes must mention:

- changed skills;
- changed contracts;
- changed MCP servers;
- changed PM workflow;
- breaking changes;
- required PM action;
- validation evidence.
