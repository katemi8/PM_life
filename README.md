# PM_life

## Поиск рекрутера в Telegram (без чата / LLM)

```bash
chmod +x scripts/recruiter-osint.sh scripts/verify-telegram.sh
bash scripts/recruiter-osint.sh "Название компании"
```

Если `contacts` пустой — страница с явным `@ником`:

```bash
bash scripts/recruiter-osint.sh "Компания" --url 'file:///path/page.html'
```

Проверка ника: `bash scripts/verify-telegram.sh username`

Кэш: `data/recruiter-cache.json` (в git не попадает).
