# PM-Live (`pm_life`)

Рабочий репозиторий PM для живых продуктовых задач с агентом.

Notion — source of truth для продуктовой документации.  
Этот repo хранит локальные заметки, метрики-заготовки и инструкции по tooling,
а не вторую копию продуктовой правды.

## Быстрый старт

1. Откройте `pm_life` в **Cursor Desktop**.
2. Подключите Notion MCP — см. [`docs/notion-mcp.md`](docs/notion-mcp.md).
3. В новом Agent chat проверьте доступ:

```text
Проверь Notion MCP и найди в Notion страницу по слову «метрики».
```

## Notion MCP

Project config лежит в [`.cursor/mcp.json`](.cursor/mcp.json)  
(официальный hosted server: `https://mcp.notion.com/mcp`).

Подробная инструкция: **[docs/notion-mcp.md](docs/notion-mcp.md)**

## Связанные системы

- Командные skills и contracts: `TrendPM/AI-Skills` (TA-agent-system)
- Продуктовая документация: Notion (через официальный Notion MCP)
