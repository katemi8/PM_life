# AGENTS.md

These instructions define how the agent should work for the TrendAgent product team.

## Available Skills

Use project skills from `skills/` when the user asks for:

- first-run setup or installation after cloning repo: `agent-system-install`;
- product analytics markup: `metrics-markup`;
- product context search: `product-context-search`;
- meeting context review: `meeting-context-review`.

## Source of Truth

- Notion is the source of truth for product documentation.
- Actual document templates live in Notion.
- KTalk / Контур.Толк is the raw source for meeting recordings, transcripts and summaries.
- Target GitHub repository is `TrendPM/AI-Skills`: `https://github.com/TrendPM/AI-Skills`.
- The repository stores skills, rules, contracts, project-local MCP server code, examples and checks.
- Published v0 baseline is expected in `TrendPM/AI-Skills` on `main` with release tag `v0.1.0`.

## Repo Process

- Initial publication may be pushed directly to `main` after final PM approval.
- After initial publication, every change must go through PR.
- Use branch naming from `docs/release-process.md`.
- Changes require owner review.
- Agent must not assign or change owners independently.
- Required checks are listed in `manifest.json` and `docs/release-process.md`.

## Notion Rules

- Read access is allowed when the user asks for product context.
- Use the official hosted Notion MCP for reads. In Codex fresh sessions this appears as `mcp__notion__`.
- Use `notion_fetch` for pages/databases/schemas, `notion_query_database_view` for existing database views, and `notion_search` plus `notion_fetch` as fallback.
- For structured database views such as `Метрики ver_10`, use the official Notion MCP view query flow.
- Before relying on a Notion page/database/view, verify that the official Notion MCP can actually read it.
- Do not update official Notion documentation without explicit user approval for the concrete change.
- Always separate official documentation from captured meeting context.

## KTalk Rules

- Use KTalk as the raw source for meeting context.
- KTalk access goes through the project-local KTalk MCP server in `.mcp/ktalk-readonly`.
- KTalk credentials are local ignored MCP config, not committed repo content.
- Never print, commit or paste `sessionToken`.
- During install or first run, guide PM through local `.mcp.json` and `.claude/local/ktalk-session.json` setup until access is ready, partial or blocked.
- Before using KTalk context, run a read-only access preflight for the requested source.
- Do not copy raw KTalk transcripts into GitHub.
- Extract only significant, deduplicated and action-worthy points for a review packet.
- Treat a meeting as a source, not as product truth.
- Do not write KTalk-derived context into Notion or GitHub as stored context records.

## Write Approval

The agent must not modify official product documentation without explicit approval.

When a write is requested, show:

- target page/database;
- exact content or properties to change;
- diff with old and new content when updating an existing document;
- source context used;
- risks or assumptions;
- expected readback check after write.

Then wait for explicit approval for the concrete change.

After an approved write, reread the target page/database and report whether the written content matches the approved preview.

If no approved Notion write-capable tool is available in the current agent environment, stop after preview/diff and report that the write cannot be performed in this session.

## PM Workflow

When the PM asks for product work:

1. Identify the product, area and artifact type.
2. Verify access and read relevant official Notion docs through the official Notion MCP.
3. Use KTalk only as a raw source when meeting context is relevant.
4. Separate official facts from meeting-derived candidates, assumptions and open questions.
5. Highlight conflicts, open questions and missing context.
6. Use the relevant skill to draft the artifact.
7. Show preview or diff before writing to official docs.
8. Request explicit approval for the concrete change.
9. Write only after approval and verify by readback.
