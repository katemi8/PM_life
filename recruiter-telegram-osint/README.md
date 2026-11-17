# Recruiter Telegram OSINT

Поиск **живого** Telegram-контакта рекрутера по названию компании — без чата и без LLM.

## Быстрый старт

```bash
cd recruiter-telegram-osint
chmod +x scripts/recruiter-osint.sh scripts/verify-telegram.sh
bash scripts/recruiter-osint.sh "Название компании"
```

Если в ответе `contacts` пустой — найдите страницу с явным `@ником` (пост, вакансия) и:

```bash
bash scripts/recruiter-osint.sh "Компания" --url 'file:///path/page.html'
```

Проверка одного ника:

```bash
bash scripts/verify-telegram.sh username
```

Кэш: `data/recruiter-cache.json` (не коммитится).

Опционально: `export HH_USER_AGENT='App/1.0 (you@email.com)'` для hh.ru.