# Owners

Этот документ описывает ownership model для `TA-agent-system`.

Основной читатель: агент и reviewer.

## Status

Active v0 process.

## Rule

У каждого значимого блока есть owner.

Owner отвечает за:

- review изменений;
- сохранение качества и границ блока;
- решение, нужен ли version bump;
- проверку, что examples и smoke expectations обновлены при изменении поведения.

## Initial Owner

Initial owner - тот, кто создал и впервые запушил блок в `TrendPM/AI-Skills`.

Для текущего initial publication owner/reviewer всех блоков - `iakovlevi`.

## Owner Change

Owner может быть изменен только по договоренности команды.

Agent rules:

- не назначать нового owner самостоятельно;
- не менять owner только потому, что кто-то изменил файл;
- если owner должен поменяться, подготовить proposal и запросить явное решение PM/team.

## Current Registry

В v0 все блоки имеют owner `iakovlevi` в `manifest.json`.

После первого push команда может заменить owner на другого конкретного owner отдельным PR.

Initial owned blocks:

- `skills/agent-system-install`;
- `skills/metrics-markup`;
- `skills/product-context-search`;
- `skills/meeting-context-review`;
- `contracts/`;
- `.mcp/`;
- `notion-template-contracts/`;
- `examples/`;
- `docs/`;
- `scripts/`;
- `AGENTS.md`;
- `README.md`;
- `manifest.json`.
