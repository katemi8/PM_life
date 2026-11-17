# Recruiter Telegram OSINT

Поиск **живого** @ рекрутера по **названию компании** — **только терминал**, без чата. Сценарии: [docs/WORKFLOW-RU.md](docs/WORKFLOW-RU.md).

## Процесс (под одну вакансию)

1. Нашли вакансию (HireHi, Telegram, LinkedIn, что угодно).
2. Скопировали **название компании** как в вакансии.
3. В терминале:

```bash
cd recruiter-telegram-osint
bash scripts/recruiter-osint.sh "Название компании"
```

4. В терминале три строки: **@ник**, **имя, должность**, **t.me/…** → пишете в Telegram. Полный JSON: `--json`.

### Если `contacts` пустой

| Шаг | Действие |
|-----|----------|
| A | На **HireHi** откройте вакансию — часто @ только в браузере. Сохраните в seed (ниже). |
| B | В посте/вакансии есть `Tg: @…` — сохраните HTML → `bash scripts/recruiter-osint.sh "Компания" --url 'file:///path/post.html'` |
| C | Один раз допишите `data/company-seeds.json` — дальше снова одна команда. |

Проверка ника: `bash scripts/verify-telegram.sh username`

## Что делает CLI (коротко)

1. **`company-seeds.json`** (проверенные рекрутеры)  
2. **`network-contacts.json`** (Нетворк + ProductCamp)  
3. **HR-каналы в Telegram** (`hrhubvacancy` и др.): поиск постов с «резюме в ЛС @…» — сценарий как для **KION**  
4. DDG: **hirehi**, **linkedin**, **t.me**  
5. Страница **HireHi** `/companies/{slug}`  
6. `verify-telegram.sh`

Обновить таблицы из xlsx:

```bash
python3 scripts/import_network_xlsx.py
# или пути к своим файлам:
python3 scripts/import_network_xlsx.py /path/network.xlsx /path/productcamp.xlsx
```

Исходники по умолчанию: `data/sources/network-career.xlsx`, `data/sources/productcamp-spring-2024.xlsx`.

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