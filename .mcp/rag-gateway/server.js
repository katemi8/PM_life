#!/usr/bin/env node
/**
 * MCP server for the TrendTech research RAG bot.
 *
 * Exposes tools that an agent can call directly:
 *   - research_confirm_hypothesis : Stage 2 confirmatory RAG over the evidence index
 *   - research_exploratory_slice  : Stage 3 exploratory clustering RAG over the evidence index
 *   - research_search_evidence    : raw Qdrant evidence retrieval
 *   - research_data_query         : read-only SQL analytics over the `mongosync` real-estate warehouse
 *
 * Both run against the n8n "RAG MCP Gateway" workflow. The gateway is async:
 * the webhook accepts the request instantly and returns an execution id; this
 * server then polls the n8n public API until the run finishes and extracts the
 * stage output from the execution run data. This sidesteps the Cloudflare ~100s
 * edge timeout (Stage 3 runs ~4-5 min).
 *
 * Config (env vars):
 *   RAG_GATEWAY_URL    webhook url   (default: https://trendagent.app.n8n.cloud/webhook/rag-mcp-gateway)
 *   RAG_GATEWAY_TOKEN  required      header token for the gateway webhook
 *   N8N_API_BASE       api base      (default: https://trendagent.app.n8n.cloud/api/v1)
 *   N8N_API_KEY        required      n8n public API key, used only to poll executions
 *   RAG_POLL_INTERVAL_MS  optional   default 5000
 *   RAG_CALL_BUDGET_MS    optional   default 100000 — per-tool-call poll budget
 *                                    (must stay under MCP client timeout; Codex = 120s).
 *                                    If the execution isn't done within this budget, the
 *                                    tool returns {status:"pending", execution_id, ...} and
 *                                    the agent is expected to re-poll via research_get_result.
 */
import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

const GATEWAY_URL =
  process.env.RAG_GATEWAY_URL ||
  "https://trendagent.app.n8n.cloud/webhook/rag-mcp-gateway";
const GATEWAY_TOKEN = process.env.RAG_GATEWAY_TOKEN;
const API_BASE =
  process.env.N8N_API_BASE || "https://trendagent.app.n8n.cloud/api/v1";
const API_KEY = process.env.N8N_API_KEY;
const POLL_INTERVAL_MS = Number(process.env.RAG_POLL_INTERVAL_MS || 5000);
const CALL_BUDGET_MS = Number(process.env.RAG_CALL_BUDGET_MS || 100000);

const TOOL_TO_NODE = {
  confirm_hypothesis: "Run Stage 2",
  exploratory_slice: "Run Stage 3",
  search_evidence: "Run Search",
  data_query: "Run Data Analysis",
};
const TOOL_TO_NAME = {
  confirm_hypothesis: "research_confirm_hypothesis",
  exploratory_slice: "research_exploratory_slice",
  search_evidence: "research_search_evidence",
  data_query: "research_data_query",
};

// Field map for research_data_query. Keep in sync with the n8n Data Analyst tool
// description (scripts/patch_stage4_add_data_analyst_tool.py SCHEMA_HINT).
const DATA_SCHEMA_HINT =
  "FIELD MAP (all unqualified; search_path = entity, dict, bridge, stage, datamarts). " +
  "Hierarchy & join keys: builders.builder_id -> blocks.builder_id; blocks.block_id -> " +
  "buildings.block_id -> sections.building_id -> sub_sections.section_id; apartments carry " +
  "block_id/building_id/section_id/sub_section_id. Geo is denormalized on entity.blocks " +
  "(city_id/city_name, district_id/district_name, region_registration_id/name, lat/long) -- " +
  "use it (dict.cities is NOT granted). " +
  "GEO CHEAT-SHEET (match EXACT values, never guess with ILIKE): blocks.city_name has only 10 coarse " +
  "market values -- 'Санкт-Петербург', 'Москва', 'Краснодарский край', 'ОАЭ', 'Екатеринбург', " +
  "'Новосибирск', 'Ростов-на-Дону', 'Казань', 'Уфа', 'Крым'. It mixes city/region/country; 'ОАЭ' is " +
  "the only foreign market (no city-level split inside it -- Dubai/Abu Dhabi are not separated here). " +
  "For finer geo use district_name (filled for ~all blocks). region_registration_name is mostly NULL -- " +
  "don't filter on it. To filter a market: city_name IN ('Москва', ...); to list options: " +
  "SELECT city_name, count(*) FROM blocks GROUP BY 1 ORDER BY 2 DESC. " +
  "entity.blocks (ЖК, ~16k; PK block_id): block_name, builder_id(+builder_short_name), " +
  "city_id/city_name, district_id/district_name, buildings_qty, max_deadline_dt, block_class_id, " +
  "status_id/block_status_name, marketing_rating, has_newbuild/parking/commercial/cottages_*_to_sale, " +
  "is_exclusive, created_at/updated_at. " +
  "entity.builders (Застройщики, ~2.5k; PK builder_id): builder_name/builder_short_name, priority, " +
  "city_1_id/city_name, organization_id, fixation_level_id/name, is_fixation_disabled, " +
  "has_newbuild_objects_to_sale, black_list_agency_qty/white_list_agency_qty. " +
  "buildings (Корпуса, ~51k; PK building_id, FK block_id): building_name, queue, contracts_qty, " +
  "has_escrow/is_escrow/escrow_banks, building_living_type_id->dict.building_living_types, deadline_dt, " +
  "deadline_key_dt/deadline_key_type->dict.deadline_key_types, sales_start_dt, building_class_id/" +
  "exact_building_class_id, facade_type_id->dict.facade_types, " +
  "elevator_type_id->dict.elevator_types, secondary_type_id->dict.secondary_types, sections_qty, " +
  "mortgages_qty/installments_qty, address_street/house/housing, built_year, is_with_pool/garden. " +
  "sections (Секции, ~78k; PK section_id): section_name, floors_min/floors_max, floor_plans_qty, " +
  "sub_sections_qty. sub_sections (Стояки, ~380k; PK sub_section_id): sub_section_name, " +
  "window_view_type_qty, cardinals_qty. floor_plans (PK floor_plan_id): floor_from/floor_to, " +
  "north_angle, geometry_type. " +
  "apartments (Квартиры, ~3.7M; PK apartment_id; FK block_id/building_id/section_id/sub_section_id): " +
  "apartment_number, apartment_kind_id->dict.apartment_kind (первичка/вторичка), " +
  "apartment_status_id->dict.apartment_status, object_type_id (комнатность; dict.object_types NOT " +
  "granted), apartment_floor, is_apartment (апартаменты vs квартира), is_penthouse, " +
  "price/price_m2/price_base/price_base_m2/has_individual_price, area_whole/area_total/area_rooms/" +
  "area_kitchen, apartment_height, wc_qty/area_wc, balconies_qty/area_balconies, " +
  "main_finishing_type_id->dict.finishing_types, finishing_rules_qty, parking_place_qty, " +
  "is_with_pool/gym/concierge/maid/cabinet, created_at/updated_at/actualized_at. " +
  "Prices can be 0/NULL when not public -- filter price>0 for real pricing. " +
  "PROPERTY CLASS: there is NO accessible class-name dictionary (dict.building_classes is NOT granted, " +
  "no dict.block_classes exists) -- do NOT search for one. Class is available only as ids: " +
  "blocks.block_class_id (integer, values 0-4, often NULL) and buildings.building_class_id (a hash, " +
  "4 distinct values) / exact_building_class_id. Report class breakdowns BY ID and state plainly that " +
  "human class labels (эконом/комфорт/бизнес/премиум) are unavailable until the class dictionary is granted. " +
  "dict.* (granted; each = id+name, join *_id to it): apartment_kind, apartment_status, balcony_types, " +
  "block_statuses, building_living_types, building_wall_materials, contract_types, deadline_key_types, " +
  "elevator_types, facade_types, finishing_types (+finishing_rule/discount/price/mortgage_pay_types), " +
  "fixation_levels, mortgage_program_types, parking_types, pool_position_types, safety_types, " +
  "secondary_types, view_places, wc_types, window_types, window_view_types. " +
  "bridge.* (granted; many-to-many, bridge.A__B links A.id to B.id): apartment__{balcony,contract_type," +
  "finishing_rules,view_places,wc,window_type}, block__{finishing_type,locations,similar_block,subway}, " +
  "building__{contract_type,parking_type,pool_position_type,safety_type,installment_program}, " +
  "buildings__mortgage_program, mortgage_program__{apartment_status,city,contract_type}, " +
  "sub_section__window_view_type, installment_program__{down_payment,object_type}, " +
  "items__ta_users(__blocks), builder_organization_lists_bridge. " +
  "Other granted stage.*: block_advantages, block_progress (ход строительства), finishing_items, " +
  "finishing_rules, mortgage_programs, districts, locations, subways, subway_lines, " +
  "region_registrations, \"Зd_tours\" (leading char is Cyrillic З -- quote it). " +
  "datamarts.ta_user_dt_events_agg (~13.9M; grain = 1 TA agent per day; daily t-1 full refresh; " +
  "only agents in entity.ta_users; agency_id = MAX per day): dt(date), agent_id, agency_id, " +
  "not_banned_agents_qty (active accounts in the agency that day), last_deal_signed_dt/" +
  "last_real_deal_signed_dt (running last-deal date per agent). Event-side metrics from metricas: " +
  "page_loads_main/content_total/complex/object (each +_web/_android/_ios), added_to_presentation " +
  "(+platforms), presentations_sent_qty/items_in_sent_presentations_qty, presentations_downloaded_qty/" +
  "items_in_downloaded_presentations_qty, added_to_compare(+platforms)/comparisons_sent_qty/" +
  "items_in_sent_comparisons_qty, fixation_request(+platforms), reservations(+platforms), " +
  "deal_signed(+platforms). CRM-confirmed counts (use for the real funnel): real_deal_request_qty, " +
  "real_reservation_qty, real_till_reservation_qty, real_deal_signed_qty. The plain " +
  "deal_signed/reservations/fixation_request are client-event-side and can differ from real_*.";

if (!GATEWAY_TOKEN) {
  console.error("FATAL: RAG_GATEWAY_TOKEN is not set");
  process.exit(1);
}
if (!API_KEY) {
  console.error("FATAL: N8N_API_KEY is not set");
  process.exit(1);
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function callGateway(payload) {
  const res = await fetch(GATEWAY_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-RAG-Gateway-Token": GATEWAY_TOKEN,
    },
    body: JSON.stringify(payload),
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`gateway POST ${res.status}: ${text.slice(0, 500)}`);
  }
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    throw new Error(`gateway returned non-JSON: ${text.slice(0, 500)}`);
  }
  if (!json.execution_id) {
    throw new Error(`gateway response missing execution_id: ${text.slice(0, 500)}`);
  }
  return json.execution_id;
}

async function getExecution(id, includeData) {
  const url = `${API_BASE}/executions/${id}${
    includeData ? "?includeData=true" : ""
  }`;
  const res = await fetch(url, {
    headers: { "X-N8N-API-KEY": API_KEY, Accept: "application/json" },
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`executions GET ${res.status}: ${text.slice(0, 500)}`);
  }
  return JSON.parse(text);
}

function isTerminalStatus(s) {
  return s && s !== "running" && s !== "new" && s !== "waiting";
}

async function pollExecution(id, budgetMs) {
  const deadline = Date.now() + budgetMs;
  while (Date.now() < deadline) {
    const exec = await getExecution(id, false);
    if (isTerminalStatus(exec.status)) return exec.status;
    const remaining = deadline - Date.now();
    if (remaining <= 0) break;
    await sleep(Math.min(POLL_INTERVAL_MS, remaining));
  }
  return null;
}

function extractStageResult(exec, runNodeName) {
  const runData = exec?.data?.resultData?.runData || {};
  const node = runData[runNodeName];
  if (!node || !node[0]) {
    throw new Error(
      `execution finished but node "${runNodeName}" produced no data`
    );
  }
  const items = node[0]?.data?.main?.[0];
  if (!items || !items[0]) {
    throw new Error(`node "${runNodeName}" returned no items`);
  }
  return items[0].json;
}

function execUrl(id) {
  return `https://trendagent.app.n8n.cloud/workflow/yWqqUZwjgszjtvdk/executions/${id}`;
}

function pendingResponse(executionId, tool) {
  const toolName = TOOL_TO_NAME[tool] || tool;
  return {
    status: "pending",
    execution_id: executionId,
    tool,
    message:
      `Execution ${executionId} is still running. Call research_get_result ` +
      `with {execution_id:"${executionId}"} after ~30-60s to fetch the result. ` +
      `Stage 3 (exploratory_slice) typically takes 4-5 min, Stage 2 (confirm_hypothesis) 1-3 min.`,
    inspect_url: execUrl(executionId),
    source_tool: toolName,
  };
}

async function finalize(executionId, tool) {
  const exec = await getExecution(executionId, true);
  if (!isTerminalStatus(exec.status)) {
    return pendingResponse(executionId, tool);
  }
  if (exec.status !== "success") {
    throw new Error(
      `gateway execution ${executionId} finished with status "${exec.status}". Inspect: ${execUrl(executionId)}`
    );
  }
  const node = TOOL_TO_NODE[tool];
  if (!node) {
    throw new Error(`unknown tool "${tool}" — cannot extract result node`);
  }
  const result = extractStageResult(exec, node);
  return { status: "done", execution_id: executionId, ...result };
}

async function startTool(tool, payload) {
  const executionId = await callGateway({ tool, ...payload });
  const budget = Math.max(0, CALL_BUDGET_MS - 5000);
  const status = await pollExecution(executionId, budget);
  if (status === null) return pendingResponse(executionId, tool);
  return finalize(executionId, tool);
}

async function getResult(executionId, toolHint) {
  let exec = await getExecution(executionId, false);
  let tool = toolHint;
  if (!tool) tool = inferToolFromRunData(exec?.data?.resultData?.runData);
  if (!isTerminalStatus(exec.status)) {
    const budget = Math.max(0, CALL_BUDGET_MS - 5000);
    const status = await pollExecution(executionId, budget);
    if (status === null) return pendingResponse(executionId, tool || "unknown");
  }
  if (!tool) {
    exec = await getExecution(executionId, true);
    tool = inferToolFromRunData(exec?.data?.resultData?.runData);
    if (!tool) {
      throw new Error(
        `execution ${executionId} finished but no known stage produced data (looked for Run Stage 2, Run Stage 3, Run Search). Inspect: ${execUrl(executionId)}`
      );
    }
  }
  return finalize(executionId, tool);
}

function inferToolFromRunData(runData) {
  if (!runData) return null;
  if (runData["Run Data Analysis"]) return "data_query";
  if (runData["Run Search"]) return "search_evidence";
  if (runData["Run Stage 3"]) return "exploratory_slice";
  if (runData["Run Stage 2"]) return "confirm_hypothesis";
  return null;
}

const TOOLS = [
  {
    name: "research_confirm_hypothesis",
    description:
      "Confirmatory RAG query against the TrendTech research evidence index. " +
      "Give it a product hypothesis in natural language (Russian works best); it " +
      "retrieves relevant user-research evidence from Qdrant, classifies each piece " +
      "as supporting/contradicting/mixed/neutral, and returns a verdict with summary, " +
      "key patterns, counterpoints, gaps, and the underlying evidence list. " +
      "Use when you need to check whether a specific claim is backed by research. " +
      "Runs 1-3 min. If the result is not ready within the MCP client timeout, the tool " +
      "returns {status:\"pending\", execution_id, ...}; in that case keep calling " +
      "research_get_result with that execution_id every ~30-60s until status is \"done\".",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description:
            "The hypothesis or claim to verify, in natural language. " +
            "Example: 'пользователям не хватает актуального контента по ипотеке'.",
        },
        max_evidence: {
          type: "integer",
          description: "Max evidence pieces to classify (1-250, default 250).",
        },
        top_k_per_query: {
          type: "integer",
          description: "Vector hits per retrieval query (1-50, default 50).",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "research_exploratory_slice",
    description:
      "Exploratory RAG query against the TrendTech research evidence index. " +
      "Give it a broad research topic or scope (Russian works best); it retrieves " +
      "evidence from Qdrant, clusters it, and returns thematic clusters each with a " +
      "summary and example evidence, plus an overall summary. " +
      "Use when you want to explore what research says about an area rather than " +
      "verify one claim. Runs 4-5 min, so almost always returns " +
      "{status:\"pending\", execution_id, ...} first — then call research_get_result " +
      "with that execution_id every ~30-60s until status is \"done\".",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description:
            "The topic or scope to explore, in natural language. " +
            "Example: 'основные боли пользователей по ипотеке'.",
        },
        top_clusters: {
          type: "integer",
          description: "Number of clusters to return (1-10, default 5).",
        },
        max_examples_per_cluster: {
          type: "integer",
          description: "Example evidence pieces per cluster (1-5, default 3).",
        },
      },
      required: ["query"],
    },
  },
  {
    name: "research_search_evidence",
    description:
      "Low-level evidence retrieval directly against the TrendTech Qdrant index. " +
      "Returns the raw matching evidence pieces (with full metadata: page_id, " +
      "notion_url, source, source_date, status, owner, region, importance, created/updated " +
      "time, and the parsed sections: short_name, context, quote, why_important) " +
      "plus diagnostics (qdrant_filter actually applied, score min/max/mean, logs). " +
      "Optional metadata filters (source_values, status_values, owner_names, region_values, date " +
      "ranges, importance bounds) translate to a Qdrant filter; rejected/in-UPRS " +
      "evidence is always excluded. " +
      "NOT RECOMMENDED as the default — research_confirm_hypothesis and " +
      "research_exploratory_slice produce more deliberate, LLM-validated answers. " +
      "Use this tool only when you explicitly want to browse raw evidence yourself " +
      "(e.g. pull citations for a quote, scan owners/sources, or feed pieces into " +
      "your own analysis loop). Runs ~5-15s; usually returns the result on the " +
      "first call (no polling needed), but follows the same pending/get_result " +
      "pattern if Qdrant is slow.",
    inputSchema: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description:
            "Free-form retrieval query (Russian works best). Embedded with " +
            "text-embedding-3-large (1024 dims) and matched against the evidence " +
            "collection.",
        },
        top_k: {
          type: "integer",
          description: "How many matches to retrieve (1-250, default 50).",
        },
        include_full_text: {
          type: "boolean",
          description:
            "If true, also include the raw concatenated chunk text in each " +
            "evidence item under `full_text`. Defaults to false to keep " +
            "responses compact.",
        },
        filters: {
          type: "object",
          description:
            "Optional Qdrant payload filters. All array filters are OR-within-key " +
            "and AND-across-keys. Date bounds accept either YYYY-MM-DD " +
            "(auto-expanded to start/end of day for created/updated_time) or full " +
            "ISO 8601. source_date is a plain date string. Status values " +
            "'Отклонено' and 'В УПРС' are excluded automatically — do not pass " +
            "them.",
          properties: {
            source_values: {
              type: "array",
              items: { type: "string" },
              description:
                "Match metadata.source. Examples: 'Результат исследования', " +
                "'Звонок', 'Чат поддержки', 'Usedesk', 'Pachka'.",
            },
            status_values: {
              type: "array",
              items: { type: "string" },
              description:
                "Match metadata.status. Examples: 'Беклог', 'В работе', " +
                "'Сделано', 'Архив'.",
            },
            owner_names: {
              type: "array",
              items: { type: "string" },
              description:
                "Match metadata.owner (research author / page owner).",
            },
            region_values: {
              type: "array",
              items: { type: "string" },
              description:
                "Match metadata.region from the Evidence database text field.",
            },
            min_importance: {
              type: "number",
              description: "Lower bound on metadata.importance (integer 1-5).",
            },
            max_importance: {
              type: "number",
              description: "Upper bound on metadata.importance (integer 1-5).",
            },
            created_time_from: {
              type: "string",
              description: "Lower bound on metadata.created_time (YYYY-MM-DD or ISO 8601).",
            },
            created_time_to: {
              type: "string",
              description: "Upper bound on metadata.created_time (YYYY-MM-DD or ISO 8601).",
            },
            updated_time_from: {
              type: "string",
              description: "Lower bound on metadata.updated_time.",
            },
            updated_time_to: {
              type: "string",
              description: "Upper bound on metadata.updated_time.",
            },
            source_date_from: {
              type: "string",
              description: "Lower bound on metadata.source_date (YYYY-MM-DD).",
            },
            source_date_to: {
              type: "string",
              description: "Upper bound on metadata.source_date (YYYY-MM-DD).",
            },
          },
          additionalProperties: false,
        },
      },
      required: ["query"],
    },
  },
  {
    name: "research_data_query",
    description:
      "Run a read-only SQL query against the TrendTech real-estate warehouse " +
      "(Postgres database `mongosync`) and get the result rows back. Use this for " +
      "QUANTITATIVE questions about the property catalog — counts, sums, averages, " +
      "distributions, top-N, ratios, group-by breakdowns over residential complexes " +
      "(ЖК), buildings (корпуса), sections (секции), risers (стояки), floor plans, " +
      "finishings, mortgage/installment programs and their dictionaries/bridges. " +
      "Counterpart to the evidence tools: those return qualitative research evidence, " +
      "this returns hard numbers from the catalog. " +
      "Pass ONE valid PostgreSQL SELECT (or WITH ... SELECT) statement; " +
      "INSERT/UPDATE/DELETE/DDL and multiple statements are rejected. " +
      "search_path is preset to `entity, stage, dict, bridge, datamarts`, so reference tables " +
      "unqualified (e.g. `buildings`). Statement timeout 30s; result capped at 500 rows " +
      "(response carries row_count + truncated), so aggregate or LIMIT in SQL. " +
      "Access is granted on a subset of tables — if a query hits a permission error, that table " +
      "isn't readable; choose a granted one. When unsure, introspect: readable tables via " +
      "SELECT table_schema, table_name FROM information_schema.role_table_grants " +
      "WHERE grantee=current_user AND privilege_type='SELECT' ORDER BY 1,2; columns via " +
      "SELECT column_name, data_type FROM information_schema.columns WHERE " +
      "table_name='<table>' ORDER BY ordinal_position. " +
      "Runs in seconds; usually returns the result on the first call, but " +
      "follows the same pending/research_get_result pattern if the DB is slow. " +
      DATA_SCHEMA_HINT,
    inputSchema: {
      type: "object",
      properties: {
        sql: {
          type: "string",
          description:
            "A single read-only PostgreSQL SELECT/WITH statement against the " +
            "`mongosync` real-estate warehouse. Tables resolve against the " +
            "stage/entity/dict/bridge schemas (no schema prefix needed).",
        },
      },
      required: ["sql"],
    },
  },
  {
    name: "research_get_result",
    description:
      "Fetch the result of a previously started RAG run by execution id. " +
      "Use this whenever research_confirm_hypothesis or research_exploratory_slice " +
      "returns {status:\"pending\", execution_id}. Returns either the same " +
      "pending shape (still running) or {status:\"done\", ...} with the full " +
      "stage result. Safe to call repeatedly; wait ~30-60s between calls.",
    inputSchema: {
      type: "object",
      properties: {
        execution_id: {
          type: "string",
          description: "Execution id returned by the previous tool call.",
        },
        tool: {
          type: "string",
          enum: ["confirm_hypothesis", "exploratory_slice", "search_evidence", "data_query"],
          description:
            "Optional hint of which stage was started. If omitted, the server " +
            "infers it from the execution's run data.",
        },
      },
      required: ["execution_id"],
    },
  },
];

const server = new Server(
  { name: "mcp-rag-gateway", version: "1.0.0" },
  { capabilities: { tools: {} } }
);

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: TOOLS,
}));

server.setRequestHandler(CallToolRequestSchema, async (req) => {
  const { name, arguments: args = {} } = req.params;
  try {
    let result;
    if (name === "research_confirm_hypothesis") {
      const payload = { query: args.query };
      if (args.max_evidence != null) payload.maxEvidence = args.max_evidence;
      if (args.top_k_per_query != null)
        payload.topKPerQuery = args.top_k_per_query;
      result = await startTool("confirm_hypothesis", payload);
    } else if (name === "research_exploratory_slice") {
      const payload = { query: args.query };
      if (args.top_clusters != null) payload.topClusters = args.top_clusters;
      if (args.max_examples_per_cluster != null)
        payload.maxExamplesPerCluster = args.max_examples_per_cluster;
      result = await startTool("exploratory_slice", payload);
    } else if (name === "research_search_evidence") {
      const payload = { query: args.query };
      if (args.top_k != null) payload.top_k = args.top_k;
      if (args.include_full_text != null)
        payload.include_full_text = args.include_full_text;
      if (args.filters != null) payload.filters = args.filters;
      result = await startTool("search_evidence", payload);
    } else if (name === "research_data_query") {
      if (!args.sql) throw new Error("sql is required");
      result = await startTool("data_query", { sql: String(args.sql) });
    } else if (name === "research_get_result") {
      if (!args.execution_id) throw new Error("execution_id is required");
      result = await getResult(String(args.execution_id), args.tool);
    } else {
      throw new Error(`unknown tool: ${name}`);
    }
    return {
      content: [{ type: "text", text: JSON.stringify(result, null, 2) }],
    };
  } catch (err) {
    return {
      isError: true,
      content: [{ type: "text", text: `Error: ${err.message}` }],
    };
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("mcp-rag-gateway: ready on stdio");
