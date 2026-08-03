# Project MCP Servers

This directory contains project-local MCP servers that are part of `TA-agent-system`.

## Included Servers

- `ktalk-readonly/` - KTalk / Контур.Толк MCP server for reading recordings, summaries and transcripts, plus guarded meeting create/update tools.
- `rag-gateway/` - RAG Gateway MCP server for querying the TrendTech research knowledge base (Qdrant evidence + LLM) and the read-only real-estate catalog warehouse (Postgres `mongosync`).

## Local Config Boundary

Server code and safe examples are committed to the repo.

Real local config is not committed:

- `.mcp.json`;
- `.claude/local/ktalk-session.json`;
- `.claude/local/ktalk-pending/`;
- tokens, browser cookies and raw transcripts.

Use `.mcp.example.json` as the template for the local MCP config.
