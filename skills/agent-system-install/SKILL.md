# agent-system-install

## When to Use

Use when a PM has cloned `TrendPM/AI-Skills` and wants the agent to set up the project for first use in their local workspace.

## Scope

Guide first-run setup for the shared agent system.

This skill verifies that the cloned repo is usable, checks local skills/contracts/docs/MCP server code, validates Notion MCP access, guides PM through project-local KTalk MCP setup, runs local checks and returns an installation report.

This skill does not publish the repo, change product documentation, create Notion pages or store credentials.

## Inputs

- cloned repo root path (`AI-Skills` by default, or another local folder name);
- PM workspace where the agent will use the shared rules;
- optional Notion page/database/view links for access preflight;
- optional KTalk meeting link/title/date for read-only preflight;
- whether KTalk meeting workflows are needed now.

## Outputs

- install status: ready, partial or blocked;
- available skills and contracts;
- validation check results;
- Notion MCP status;
- KTalk MCP status;
- missing setup steps.

## Read Sources

- local `manifest.json`;
- local `AGENTS.md`;
- local `.mcp/`, `skills/`, `contracts/`, `notion-template-contracts/`, `docs/`;
- official Notion MCP preflight results;
- KTalk MCP preflight results.

If KTalk is used, raw transcript text must not be copied into GitHub, examples, generated artifacts or setup output.

## Write Targets

None in tracked shared repo files during first-run setup.

Allowed local side effects only with PM confirmation:

- local `.mcp.json` created from `.mcp.example.json`;
- local `.claude/local/ktalk-session.json` created from `.mcp/ktalk-readonly/ktalk-session.example.json`;
- local agent session restart if needed;
- local ignored configuration created by the MCP server itself.

No official Notion docs may be written by this skill.

## Approval Rules

This skill must not write official Notion docs.

Official Notion writes still require preview or diff, explicit approval for the concrete change and readback. Installation must not bypass that rule.

If setup requires a local configuration change, explain the action and ask PM to perform or confirm it.

Do not ask PM to paste `sessionToken`, bearer token, browser storage or other credentials into chat.

If no approved Notion write-capable tool is available, stop after preview/diff and report that writes cannot be performed in this session.

## Workflow

1. Locate the cloned repo root (`AI-Skills` by default, or another local folder name).
2. Read `manifest.json` and verify target repo is `TrendPM/AI-Skills`.
3. Verify required folders and files exist: `AGENTS.md`, `.mcp/ktalk-readonly/server.py`, `.mcp.example.json`, `skills/`, `contracts/`, `notion-template-contracts/`, `docs/`, `scripts/`.
4. List available skills from `manifest.json` and `skills/`.
5. Run local checks:
   - `python scripts\validate-skills.py`;
   - `python scripts\smoke-skills.py`;
   - `python scripts\validate-manifest.py`;
   - `python scripts\scan-secrets.py`;
   - `python -m json.tool .mcp.example.json`;
   - `python -m json.tool .mcp\ktalk-readonly\ktalk-session.example.json`;
   - `python -m json.tool manifest.json`;
   - `python -m json.tool manifest.example.json`;
   - `git diff --check` only after git is initialized.
6. Verify official Notion MCP:
   - if server `notion` is not configured, guide PM to run `codex mcp add notion --url https://mcp.notion.com/mcp`;
   - ask PM to run `codex mcp login notion` when OAuth is missing;
   - confirm `mcp__notion__` tools or equivalent official MCP tools are available;
   - ask PM to authenticate with their own Notion account if needed;
   - verify access to provided pages/databases/views before relying on them.
7. Guide project-local KTalk MCP setup if meeting workflows are needed:
   - check whether KTalk MCP server `ktalk` is available;
   - if missing, verify `.mcp/ktalk-readonly/server.py` and `.mcp.example.json`;
   - guide PM to create local `.mcp.json` from `.mcp.example.json`;
   - guide PM to create local `.claude/local/ktalk-session.json` from `.mcp/ktalk-readonly/ktalk-session.example.json`;
   - ask PM to complete local MCP authentication/configuration without pasting credentials into chat;
   - confirm expected read tools are available: `ktalk_list_recordings`, `ktalk_get_recording`, `ktalk_get_transcript`, `ktalk_get_summary`, `ktalk_get_summary_by_type`, `ktalk_list_calendar_events`;
   - run read-only preflight for a provided meeting/source;
   - report KTalk status as ready, partial or blocked.
8. Run the smoke prompt:
   - list available skills;
   - explain Notion source-of-truth boundary;
   - explain KTalk raw-source boundary.
9. Return final install report with exact blockers and next actions.

## Failure Policy

Stop and report blocked status if:

- repo path cannot be found;
- required files are missing;
- local checks fail;
- official Notion MCP is unavailable and the requested setup needs Notion access;
- KTalk MCP setup is needed but local server/config is unavailable or unauthorized;
- PM asks to paste credentials into chat;
- setup would require writing product docs.

Return partial status if:

- repo checks pass but Notion access is not verified;
- KTalk metadata works but summary/transcript access is unavailable;
- KTalk is not needed for current PM workflows.

## Examples

Good request:

```text
Я склонировал TrendPM/AI-Skills. Используй skills/agent-system-install/SKILL.md и настрой этот проект для моей работы.
```

Good behavior:

```text
Agent verifies repo files, runs checks, guides Notion OAuth and project-local KTalk MCP setup, then reports ready/partial/blocked without printing credentials.
```

Bad behavior:

```text
Agent asks PM to paste KTalk sessionToken into chat or writes product docs during installation.
```

## Smoke Tests

- Given a cloned repo, agent lists all skills and runs validation checks.
- Given missing Notion MCP, agent guides PM to authenticate and reports status.
- Given missing KTalk MCP, agent guides PM to configure local `.mcp.json` and `.claude/local/ktalk-session.json`, then reports ready/partial/blocked.
- Given a credential pasted into chat, agent stops and tells PM to rotate/refresh local access.
