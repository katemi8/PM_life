# RAG Gateway MCP

Project-local MCP server that connects the agent to the TrendTech research
knowledge base and the real-estate catalog warehouse. The agent can pull
research evidence and hard catalog numbers on its own, mid-task — without Slack
and without manual copy-paste.

It is a thin stdio server over a live n8n RAG pipeline (Qdrant evidence index +
LLM) and a read-only Postgres warehouse. Only the MCP SDK is required as a
dependency.

## Tools

| Tool | What it does | Time |
|---|---|---|
| `research_confirm_hypothesis` | Validates a product hypothesis against the research-evidence base. Returns a verdict (confirmed / not confirmed), summary, key patterns, counter-arguments, gaps and the supporting / contradicting / mixed / neutral evidence list. | ~1–3 min |
| `research_exploratory_slice` | Explores a topic in the base. Returns thematic clusters with summaries and evidence examples plus an overall slice summary. | ~4–5 min |
| `research_search_evidence` | **Not the default.** Raw Qdrant search without LLM post-processing. Returns evidence with full metadata (`page_id`, `notion_url`, `source`, `source_date`, `status`, `owner`, `region`, `importance`, timestamps, parsed sections) plus diagnostics. Supports metadata filters. Use when the agent wants to scroll evidence itself or run its own pipeline. | ~5–15 s |
| `research_data_query` | Read-only SQL analytics over the real-estate warehouse (Postgres `mongosync`). For **quantitative** catalog questions — counts, sums, averages, distributions, top-N, group-by over residential complexes (ЖК), buildings, sections, risers, floor plans, finishings, mortgage programs and their dictionaries/bridges. Accepts one `SELECT` / `WITH … SELECT`; writes/DDL/multi-statement are rejected. `search_path` = `entity, stage, dict, bridge, datamarts`, 30s timeout, up to 500 rows. The full schema field map is embedded in the tool description. | ~seconds |
| `research_get_result` | Fetches the result of a previously started request by `execution_id`. Needed when a tool returned `{status:"pending", execution_id}` (MCP clients cut calls at ~120s, Stage 3 runs 4–5 min). The agent re-calls this every ~30–60s until `status` is `"done"`. | instant |

## How it works

The server talks to the n8n workflow «RAG MCP Gateway» (`trendagent.app.n8n.cloud`).
The gateway is **async**: the webhook accepts instantly and returns an
`execution_id`, then runs the RAG pipeline in the background. The server polls
the n8n Executions API until completion and returns the result.

```
Agent → MCP server (stdio)
  → POST /webhook/rag-mcp-gateway  (instant accept + execution_id)
  → poll GET /executions/{id}      (every 5s, timeout 10 min)
  → return result JSON
```

`research_data_query` runs a guarded read-only SQL node against the warehouse —
SELECT/WITH only, statement timeout, row cap, granted-tables subset.

## Local config

This server reads two secrets from the process environment (or an ignored local
`.env` next to `server.js`):

| Var | Required | Default |
|---|---|---|
| `RAG_GATEWAY_TOKEN` | ✅ | — |
| `N8N_API_KEY` | ✅ | — |
| `RAG_GATEWAY_URL` | no | `https://trendagent.app.n8n.cloud/webhook/rag-mcp-gateway` |
| `N8N_API_BASE` | no | `https://trendagent.app.n8n.cloud/api/v1` |
| `RAG_POLL_INTERVAL_MS` | no | `5000` |
| `RAG_CALL_BUDGET_MS` | no | `100000` (must be below the MCP client timeout) |

Copy `.env.example` to a local ignored `.env`, or pass the two tokens through the
MCP client `env` block (see root `.mcp.example.json`). **Never commit real
tokens.** Request `RAG_GATEWAY_TOKEN` and `N8N_API_KEY` from **Александр Фенин**
(@afenin).

## Install

```bash
cd .mcp/rag-gateway
npm install
```

Expected server name in the MCP config: `rag_gateway`.

Verify it starts (prints `mcp-rag-gateway: ready on stdio`):

```bash
RAG_GATEWAY_TOKEN=... N8N_API_KEY=... node server.js
```

## Notes

- `N8N_API_KEY` is a full n8n API key, used here only to read execution status
  and data. Keep it in local config, never commit it.
- On an execution error the tool returns `isError: true` with a link to the n8n
  execution for debugging.
- Canonical upstream source: `gitverse.ru/afenin/trendtech-rag-bot-mcp`. This
  copy is vendored into `TA-agent-system` so the whole team gets the tools with
  the repo.
