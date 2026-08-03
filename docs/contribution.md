# Contribution

Этот документ описывает, как PM и агенты могут улучшать `TA-agent-system`.

Основной читатель: агент, который помогает PM подготовить изменение.

## Status

Active v0 process.

Initial publication may be pushed directly to `main` after final PM approval. After initial publication, every change must go through PR, owner review and required checks from `docs/release-process.md`.

## What Can Be Changed

PMs can propose changes to:

- skills;
- contracts;
- Notion template contracts;
- examples;
- docs;
- project-local MCP server code;
- validation scripts.

## What Must Not Be Added

Do not add:

- raw KTalk transcripts;
- real secrets or tokens;
- private `.mcp.json`;
- dynamic product documentation as source of truth;
- personal PM notes;
- unapproved Notion exports.

## Change Flow

1. PM describes the repeated problem or desired improvement.
2. Agent identifies affected files.
3. Agent identifies affected owners.
4. Agent drafts a change proposal.
5. PM confirms scope.
6. Agent prepares a branch and PR according to `docs/release-process.md`.
7. Owner reviews the PR.
8. After checks and review pass, the PR may be merged.

## PR Description Template

Use `.github/pull_request_template.md`.

```md
## Problem

## What changed

## Affected skills/contracts

## Owners / reviewers

## PM-visible behavior

## Write/approval impact

## Validation evidence

## Rollout notes
```

## Review Focus

Reviewers should check:

- does this make the agent more reliable?
- are approval rules preserved?
- does it keep Notion as source of truth?
- does it avoid raw KTalk transcript storage?
- are examples updated when behavior changes?
- can PMs understand the workflow through the agent?

## Ownership Changes

Owner may change only by team agreement.

Agent behavior:

- do not assign a new owner independently;
- do not infer owner changes from file edits;
- if ownership should change, prepare a proposal and ask PM/team to confirm.
