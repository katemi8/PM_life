# Skill Quality Gates

Every skill must be explicit enough for an agent to use without hidden context.

## Required Sections

Each `SKILL.md` must include:

- `# <skill-name>`;
- `## When to Use`;
- `## Scope`;
- `## Inputs`;
- `## Outputs`;
- `## Read Sources`;
- `## Write Targets`;
- `## Approval Rules`;
- `## Workflow`;
- `## Failure Policy`;
- `## Examples`;
- `## Smoke Tests`.

## Write Safety

Skills that write to Notion or external systems must require:

- preview for new content;
- diff with old and new content for existing document updates;
- explicit approval for the concrete change;
- readback verification after write.

Preview alone is not enough for official Notion documentation writes.

## KTalk Safety

Skills that process KTalk must state:

- KTalk is raw source;
- raw transcripts must not be copied into GitHub;
- raw transcript text should not be stored in examples or generated artifacts;
- meeting review packets should use short sanitized excerpts or timestamps;
- meeting context is not final product truth.

## Examples and Smoke Tests

Every behavior-changing PR must update examples or smoke-test expectations unless the change is purely wording.
