# meeting-context-review

## When to Use

Use when a PM wants to review a KTalk meeting, transcript, summary or prepared meeting review packet.

## Scope

Prepare or review meeting context grouped by decisions, requirements, open questions, risks, follow-ups and rejected options.

Current v0 is read-only. It reviews meeting material and prepares recommendations, but does not write results to Notion.

## Inputs

- KTalk meeting link/title/date or provided meeting material;
- PM review request;
- related official docs, if provided.

## Outputs

- compact review packet;
- items needing PM action;
- suggested confirm/reject/follow-up actions;
- conflicts and open questions.

## Read Sources

- KTalk meeting metadata, summary or transcript through the project-local MCP server;
- provided meeting material;
- related official Notion docs;

If KTalk is used, raw transcript text must not be copied into GitHub or review output by default.

## Read Tools

Use the configured KTalk MCP server `ktalk` for meeting source verification.

Use the official hosted Notion MCP for related official Notion docs. If official Notion MCP is unavailable, report the limitation and skip Notion conflict checks instead of using another Notion connector.

## Write Targets

None by default.

## Approval Rules

Review recommendations are read-only by default.

Changing official docs requires routing to a write-capable skill with preview or diff, explicit approval and readback.

## Workflow

1. Load KTalk meeting material or provided meeting material.
2. Group items by type and required action.
3. Identify repeated points and possible contradictions.
4. Identify conflicts with official docs.
5. Suggest next actions.
6. Keep output compact for PM.
7. Do not write review results to Notion.

## Failure Policy

Report and stop if:

- meeting source cannot be found;
- KTalk verification is required but unavailable;
- review would require storing raw transcript text instead of summary, timestamp or sanitized excerpt.

## Examples

Good request:

```text
Покажи review packet по последней встрече и что требует моего решения.
```

Bad behavior:

```text
Approving all extracted items automatically as final product truth.
```

## Smoke Tests

- Given a meeting with decisions and open questions, agent groups items and shows required PM actions.
- Given conflict with official docs, agent flags conflict and does not resolve silently.
