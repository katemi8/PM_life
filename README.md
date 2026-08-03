# PM-Live / TA-agent-system

Этот репозиторий (`katemi8/PM_life`, PM-Live) содержит развёрнутый `TA-agent-system`
из `TrendPM/AI-Skills` (v0.1.0): skills, contracts, project-local MCP servers, docs и checks.

`TA-agent-system` - общий слой для работы продуктовой команды TrendAgent с агентом.

Upstream: `TrendPM/AI-Skills` (`https://github.com/TrendPM/AI-Skills`).

Для Cursor в этом repo уже лежит project MCP config: [`.cursor/mcp.json`](.cursor/mcp.json).  
Как подключить Notion MCP в Cursor: [`docs/notion-mcp-cursor.md`](docs/notion-mcp-cursor.md).

Проект нужен, чтобы PM в разных продуктовых направлениях использовали агента одинаково:
с одними skills, правилами безопасности, правилами записи в Notion и понятным процессом улучшений.

Этот repo хранит не продуктовую документацию, а правила и навыки агента:

- какие skills доступны команде;
- как агент читает Notion и KTalk;
- какие MCP-серверы нужны агенту и где лежит project-local код;
- когда агент может писать в Notion;
- как оформлять и проверять изменения skills;
- как PM могут предлагать улучшения через pull request;
- какие проверки должны проходить перед merge/release.

## С чем работает система

Система работает с тремя основными зонами:

- Notion - продуктовая документация, актуальные шаблоны, user stories, требования, аналитическая схема.
- KTalk / Контур.Толк - встречи, записи, транскрипты и обсуждения, которые агент использует как raw source для summary и review packet.
- `TrendPM/AI-Skills` - правила работы агента, skills, contracts, project-local MCP servers, examples и checks.

GitHub не должен становиться вторым хранилищем продуктовой правды.

Для чтения Notion в текущем v0 единственный поддерживаемый путь - официальный hosted Notion MCP.

Для структурных баз и view, например `Метрики ver_10`, агент должен читать schema через `notion_fetch`,
строки view через `notion_query_database_view`, а `notion_search` + `notion_fetch` использовать только как partial fallback.

## Быстрый старт

1. Склонировать repo:

```powershell
git clone https://github.com/TrendPM/AI-Skills.git
```

2. Открыть папку repo агенту.
3. Отправить агенту установочный запрос:

```text
Я склонировал TrendPM/AI-Skills. Используй skills/agent-system-install/SKILL.md и настрой этот проект для моей работы.
```

4. Дождаться install report со статусом:
   - `ready` - можно работать;
   - `partial` - базовые проверки прошли, но часть доступов не проверена или не нужна сейчас;
   - `blocked` - есть конкретный отсутствующий доступ, файл или настройка.

## Доступы и MCP

PM не должен вручную настраивать все детали без агента. Установочный skill ведет через проверку доступов и локальных MCP-настроек.

- Notion подключается через официальный hosted Notion MCP и OAuth аккаунта PM.
- KTalk MCP server лежит в repo: `.mcp/ktalk-readonly`.
- RAG Gateway MCP server лежит в repo: `.mcp/rag-gateway` — research-база знаний (Qdrant + LLM) и read-only SQL по каталогу недвижимости (`mongosync`). Токены `RAG_GATEWAY_TOKEN` и `N8N_API_KEY` нужно запросить у **Александра Фенина** (@afenin). Подробности в `docs/mcp-servers.md`.
- Локальный MCP config создается из `.mcp.example.json`.
- Реальный KTalk config хранится только локально: `.claude/local/ktalk-session.json`.
- `sessionToken`, browser cookies, `.mcp.json`, `.claude/local/*`, raw transcripts и `.env` нельзя отправлять в чат и нельзя коммитить.
- Перед KTalk-задачами агент должен проверить доступ и вернуть `ready / partial / blocked`.

## Как PM использует проект

PM не обязан читать все файлы вручную. Базовый сценарий: PM ставит задачу агенту, а агент использует правила и skills из этого проекта.

Что PM может делать с помощью этого проекта и агента:

### Установить проект после clone

Когда PM впервые подключает общий repo к своему workspace.

PM клонирует `TrendPM/AI-Skills`, открывает его агенту и запускает установочный skill.

Агент проверяет структуру repo, запускает локальные проверки, помогает подключить официальный Notion MCP и настраивает project-local KTalk MCP server из `.mcp/ktalk-readonly`.

Где описано: `skills/agent-system-install/SKILL.md`.

Пример запроса:

```text
Я склонировал TrendPM/AI-Skills. Используй skills/agent-system-install/SKILL.md и настрой этот проект для моей работы.
```

### Собрать продуктовый контекст перед задачей

Когда нужно быстро понять, что уже известно по фиче, сценарию, бизнес-правилу или спорному вопросу.

Агент читает Notion, при необходимости использует KTalk, отделяет подтвержденные факты от предположений, показывает противоречия, gaps и open questions.

Где описано: `skills/product-context-search/SKILL.md`.

Пример запроса:

```text
Собери контекст по premium_status перед продуктовой задачей.
```

### Подготовить продуктовую разметку метрик

Когда нужно описать события, параметры, страницы, категории или изменения в аналитической схеме.

Агент сверяется с живой схемой аналитики в Notion, переиспользует существующие сущности, предлагает новые только при необходимости и показывает batch preview перед записью.

Где описано: `skills/metrics-markup/SKILL.md`.

Пример запроса:

```text
Подготовь разметку метрик для нового экрана оплаты.
```

### Разобрать встречу из KTalk

Когда на встрече с бизнесом, разработкой или другой командой обсуждали продуктовый контекст, который нужно не потерять.

Агент выделяет договоренности, гипотезы, вопросы, риски и follow-ups, затем показывает summary/review packet без записи в Notion.

Где описано: `skills/meeting-context-review/SKILL.md`.

Пример запроса:

```text
Разбери последнюю встречу из KTalk по тарифам и покажи, что требует решения PM.
```

### Проверить противоречия перед изменением

Когда есть риск, что новая идея или требование конфликтует с текущей документацией или предыдущими договоренностями.

Агент сравнивает запрос с official Notion docs и доступным контекстом, затем показывает conflicts, assumptions и что нужно подтвердить.

Где описано: `skills/product-context-search/SKILL.md`, `skills/meeting-context-review/SKILL.md`.

Пример запроса:

```text
Проверь, не противоречит ли новая логика текущим требованиям.
```

### Безопасно обновить Notion-документ

Когда PM хочет, чтобы агент внес изменение в существующую user story, требования или аналитику.

Агент сначала показывает preview. Для существующего документа preview должен быть diff. После explicit approval агент записывает изменение и делает readback.

Где описано: `contracts/notion-write-contract.md`.

Пример запроса:

```text
Обнови это требование, но сначала покажи diff.
```

### Улучшить общий skill или правило агента

Когда PM видит повторяющуюся ошибку агента или хочет стандартизировать новый процесс для всей команды.

Агент помогает описать проблему, ожидаемое поведение, affected files и proposal для PR в `TrendPM/AI-Skills`.

Где описано: `docs/contribution.md`, `docs/skill-lifecycle.md`, `docs/release-process.md`.

Пример запроса:

```text
Предложи улучшение skill, чтобы агент всегда проверял этот кейс перед разметкой.
```

### Понять, как агент будет выполнять задачу

Когда PM хочет не сразу получить артефакт, а сначала понять процесс, источники и ограничения.

Агент объясняет, какие skills и contracts применит, какие источники прочитает и где нужен approval.

Где описано: `AGENTS.md`, `manifest.json`, `docs/pm-workflow.md`.

Пример запроса:

```text
Объясни, как ты будешь делать эту задачу и какие правила применишь.
```

## Структура

```text
TA-agent-system/
  AGENTS.md                     # готовые инструкции для агента
  manifest.json                  # release manifest опубликованной v0 версии
  manifest.example.json          # пример release manifest
  .mcp.example.json              # пример локальной MCP-конфигурации
  .mcp/                          # project-local MCP servers без credentials
                                 #   ktalk-readonly/  - KTalk read + guarded write
                                 #   rag-gateway/     - research RAG база + SQL по каталогу недвижимости
  skills/                        # исполняемые workflows агента
  notion-template-contracts/      # правила работы с Notion-шаблонами
  examples/                      # примеры хорошего результата
  contracts/                     # общие правила системы
  docs/                          # процессные спецификации для агента и команды
  scripts/                       # проверки и служебные утилиты
```

## Как читать репозиторий

Если нужно понять проект целиком, начните с этого файла.

Если агенту нужно работать в продуктовом workspace, используйте `AGENTS.md`.

Если нужно понять конкретный процесс, смотрите `docs/`:

- `pm-workflow.md` - как агент работает с задачами PM;
- `mcp-servers.md` - какие MCP-серверы входят в проект и как их подключать;
- `notion-mcp.md` - рабочий read-flow через официальный Notion MCP;
- `ktalk-access.md` - как подключать project-local KTalk MCP server без хранения credentials в repo;
- `install.md` - как подключать систему в продуктовый workspace;
- `update.md` - как обновлять skills;
- `skill-lifecycle.md` - как создавать и улучшать skills;
- `owners.md` - как работает ownership и owner review;
- `release-process.md` - как проходят PR, review, merge и release;
- `troubleshooting.md` - типовые проблемы.

## Как улучшать проект

Если PM видит повторяющуюся ошибку агента или хочет добавить общий workflow:

1. PM описывает проблему или ожидаемое поведение.
2. Агент определяет affected files и owner.
3. Изменение готовится в branch.
4. Создается pull request.
5. Owner ревьюит изменение.
6. Запускаются required checks.
7. После review и checks изменение попадает в merge/release.

Initial publication может идти прямым push в `main` после финального approval. После initial publication все изменения идут через PR.

## Что входит в v0

Первая часть системы: подготовить содержимое для `TrendPM/AI-Skills`, которое позволит команде одинаково использовать агента.

Опубликованная v0 версия должна находиться в `TrendPM/AI-Skills` на `main` и иметь release tag `v0.1.0`.

В эту часть входят:

- установочный skill для первого запуска после clone;
- базовые skills;
- единые инструкции для агента;
- project-local KTalk MCP server;
- contracts для Notion writes, approval и quality gates;
- правила работы с Notion-шаблонами;
- рабочий read-flow через официальный Notion MCP;
- примеры хороших результатов;
- минимальные проверки качества;
- процесс улучшений skills через PR, owner review и release checks после initial publication.

Границы текущей версии:

- хранение продуктовой документации в GitHub вместо Notion;
- хранение credentials, browser cookies, raw transcripts или локальных MCP-конфигов в repo;
- запись KTalk-derived контекста в Notion без отдельного explicit approval;
- копирование raw KTalk transcripts в GitHub.

Статус examples:

- `metrics-good-example.md` показывает хороший пример разметки метрик;
- `meeting-review-packet-example.md` показывает хороший пример read-only разбора встречи.

Secret scanner сканирует `.env` / `.env.*`, поддерживает дополнительные текстовые форматы и расширенный allowlist placeholder-значений.

Перед публикацией его нужно запускать вместе с остальными локальными проверками.
