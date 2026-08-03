# Notion MCP — подключение для PM-Live

Этот документ описывает, как подключить официальный Notion MCP к Cursor,
чтобы агент в `PM_life` (PM-Live) мог читать (и при approval — писать) продуктовые
материалы в Notion.

Официальный сервер: `https://mcp.notion.com/mcp`  
Документация Notion: [Connecting to Notion MCP](https://developers.notion.com/guides/mcp/get-started-with-mcp)  
Agent read-flow (общий): [`notion-mcp.md`](notion-mcp.md)

## Что получите после подключения

Агент сможет вызывать Notion tools, например:

- `notion-fetch` / `notion_fetch` — страница, база, схема;
- `notion-search` / `notion_search` — поиск по workspace;
- `notion-query-database-view` / `notion_query_database_view` — строки view.

Доступ идёт через **ваш** Notion-аккаунт (OAuth). Shared service account в v0 не используем.

## Быстрый старт в Cursor (рекомендуется)

### Вариант A — project config (для команды)

В корне `pm_life` уже есть шаблон `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "notion": {
      "url": "https://mcp.notion.com/mcp"
    }
  }
}
```

1. Откройте репозиторий `pm_life` в Cursor Desktop.
2. Cursor Settings → **MCP** — убедитесь, что сервер `notion` виден.
3. Если статус **Needs login** / не авторизован — нажмите Connect / Login.
4. В браузере завершите OAuth своим Notion-аккаунтом и разрешите доступ к нужному workspace.
5. **Перезапустите Cursor** или начните новый Agent chat.
6. Проверьте: попросите агента «прочитай страницу Notion по ссылке …» или «найди в Notion …».

### Вариант B — global config

1. Cursor Settings → **MCP** → **Add new global MCP server**.
2. Вставьте:

```json
{
  "mcpServers": {
    "notion": {
      "url": "https://mcp.notion.com/mcp"
    }
  }
}
```

3. Save → restart Cursor → OAuth при первом использовании Notion tool.

Global config удобен для личной машины; для командного onboarding предпочтительнее project `.cursor/mcp.json`.

## Проверка, что всё работает

В новом Agent chat:

```text
Проверь, доступен ли Notion MCP. Если да — найди в Notion одну страницу
по слову «метрики» и кратко опиши, что нашёл.
```

Ожидаемое поведение:

- агент видит Notion MCP tools;
- поиск/fetch проходит без ошибки auth;
- если страницы нет в доступе — агент явно пишет, что нет permission, а не выдумывает контент.

## Правила для PM-Live

- Notion — source of truth для продуктовой документации.
- Агент **не пишет** в официальные Notion-документы без явного approval на конкретное изменение (preview/diff → approve → write → readback).
- Не вставляйте Notion integration tokens / cookies в чат.
- Cloud Agent (фон в cursor.com) часто **не** имеет вашего Notion OAuth: полноценный Notion MCP — в Cursor Desktop / локальной сессии.

## Troubleshooting

| Симптом | Что сделать |
|---|---|
| Сервер есть в Settings, но Agent пишет «MCP server does not exist: notion» | Settings → MCP: выключите и снова включите `notion`, откройте список MCP, затем новый chat |
| Needs login / unauthorized | Повторите OAuth; при необходимости Disconnect / Clear authentication и залогиньтесь снова |
| Tools не появились после добавления config | Restart Cursor; убедитесь, что открыт именно project с `.cursor/mcp.json` |
| Страница/база не читается | Проверьте, что ваш Notion-аккаунт имеет доступ к странице; дайте агенту прямую ссылку |
| Cloud Agent не видит Notion | Это ожидаемо без интерактивного OAuth — подключайте MCP в Desktop |

## Codex (если работаете и там)

```powershell
codex mcp add notion --url https://mcp.notion.com/mcp
codex mcp login notion
codex mcp list
codex mcp get notion
```

Ожидание: server `notion` enabled, streamable HTTP, OAuth.

## Связь с TA-agent-system

Командный слой skills/contracts живёт в `TrendPM/AI-Skills`.  
PM-Live (`pm_life`) — рабочий workspace PM. Notion MCP подключается одинаково: официальный hosted endpoint + личный OAuth.

После подключения Notion можно запускать типовые сценарии:

- собрать продуктовый контекст по фиче;
- подготовить разметку метрик по живой схеме в Notion;
- проверить конфликты перед изменением требований.
