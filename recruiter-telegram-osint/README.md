# Recruiter Telegram OSINT

Поиск **живого** @ рекрутера по **названию компании** из вашей вакансии. Без LLM, без чата.

## Процесс (под одну вакансию)

1. Нашли вакансию (HireHi, Telegram, LinkedIn, что угодно).
2. Скопировали **название компании** как в вакансии.
3. В терминале:

```bash
cd recruiter-telegram-osint
bash scripts/recruiter-osint.sh "Название компании"
```

4. Смотрите **`best_contact`** → пишете в Telegram с резюме и сопроводительным.

### Если `contacts` пустой

| Шаг | Действие |
|-----|----------|
| A | На **HireHi** откройте вакансию — часто @ только в браузере. Сохраните в seed (ниже). |
| B | В посте/вакансии есть `Tg: @…` — сохраните HTML → `bash scripts/recruiter-osint.sh "Компания" --url 'file:///path/post.html'` |
| C | Один раз допишите `data/company-seeds.json` — дальше снова одна команда. |

Проверка ника: `bash scripts/verify-telegram.sh username`

## Что делает CLI (коротко)

1. `company-seeds.json` + кэш  
2. DDG: **hirehi.ru**, **linkedin.com**, **t.me** (только сниппеты)  
3. Одна страница **HireHi** `/companies/{slug}`  
4. `verify-telegram.sh`

**Отключено** (низкая отдача): hh.ru, Hirify, обход 10+ сайтов, случайные `t.me` из выдачи.

## Seed (память на компанию)

```json
"my-company": {
  "leads": [{
    "username": "recruiter_nick",
    "source_url": "https://hirehi.ru/...",
    "source_note": "вакансия PM, дата"
  }]
}
```

Кэш: `data/recruiter-cache.json` (пустое не кэшируется). `--refresh` — перепроверить.