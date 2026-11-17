# Recruiter Telegram OSINT

Одна команда → **живой** Telegram рекрутера (без LLM, без Cursor-чата).

```bash
cd recruiter-telegram-osint
chmod +x scripts/*.sh
bash scripts/recruiter-osint.sh "TutorOnline"
```

Порядок поиска:

1. **`data/company-seeds.json`** — проверенные `@ники` + ссылка-источник (для TutorOnline уже есть).
2. **DuckDuckGo HTML** — запросы вида «Компания рекрутер telegram» (фильтр ботов/каналов).
3. **hh.ru** — только если `export RECRUITER_USE_HH=1` (по умолчанию **выключено**: TG в вакансиях редко).

В ответе смотрите **`best_contact`** (лучший) и **`contacts`** (до 2 живых). Каждый контакт с `source_url` и проверкой через `t.me`.

### Если компании нет в seeds и поиск пустой

Добавьте запись в `data/company-seeds.json` (username + `source_url`) или один раз:

```bash
bash scripts/recruiter-osint.sh "Компания" --url 'file:///path/page.html'
```

Проверка ника:

```bash
bash scripts/verify-telegram.sh username
```

Кэш: `data/recruiter-cache.json` (не коммитится; пустые результаты не кэшируются).