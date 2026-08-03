# Update

Этот документ описывает, как обновлять `TA-agent-system`.

Основной читатель: агент. PM может спросить агента, что изменилось и нужно ли обновляться.

## Status

Published v0 update process for `TrendPM/AI-Skills`: `https://github.com/TrendPM/AI-Skills`.

After the initial `main` publication, updates go through PR, owner review, required checks and versioned release tags.

## Update Principles

- Не обновлять рабочие skills из случайной локальной копии.
- Обновлять только из явно указанного источника.
- Перед обновлением показать PM, что изменилось.
- После обновления прогнать проверки.

## Update Flow

1. Agent identifies current local folder and current `manifest.json`.
2. Agent identifies target source explicitly provided by PM.
3. Agent compares changed files:
   - changed skills;
   - changed contracts;
   - changed MCP servers;
   - changed Notion/KTalk rules;
   - changed install/update instructions;
   - breaking changes;
   - migration steps.
4. Agent shows a preview of the update and affected files.
5. PM confirms the update.
6. Agent applies update according to workspace rules.
7. Agent runs checks.
8. Agent reports what changed and which checks passed.

## Required Checks After Update

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

If checks fail, agent must stop and report the failed file/rule.

## Manual Diff Checklist

Before applying an update, agent must inspect:

- `AGENTS.md` for changed global behavior;
- `skills/*/SKILL.md` for changed triggers, writes and approvals;
- `contracts/` for changed system rules;
- `.mcp/` and `.mcp.example.json` for changed MCP server setup;
- `notion-template-contracts/` for changed template assumptions;
- `scripts/` for changed checks;
- `docs/install.md` and `docs/update.md` for changed operational steps.

## Breaking Changes

A change is breaking if it changes:

- approval rules;
- Notion write targets;
- project-local MCP server behavior;
- skill trigger behavior;
- install/update process.

## Release Mode

Update flow uses reviewed PRs, versioned releases and manifest provenance based on GitHub tag plus commit SHA in GitHub release notes.

The published `manifest.json` must describe the released baseline or the next release candidate; it must not be left in an unpublished local-source state.
