## Problem

## What Changed

## Affected Skills / Contracts / MCP Servers / Docs

## Owners / Reviewers

## PM-Visible Behavior

## Notion / KTalk / Approval Impact

## Validation Evidence

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

## Rollout Notes

## Breaking Changes
