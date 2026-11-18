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

4. В терминале **список контактов**: @ник (**★** — рекомендуемый), имя, должность, **тип**, **источник** (откуда найден), ссылка t.me. Полный JSON: `--json` (в каждом контакте `match_reason`, `source_url`).

### Если `contacts` пустой

| Шаг | Действие |
|-----|----------|
| A | На **HireHi** откройте вакансию — часто @ только в браузере. Сохраните в seed (ниже). |
| B | В посте/вакансии есть `Tg: @…` — сохраните HTML → `bash scripts/recruiter-osint.sh "Компания" --url 'file:///path/post.html'` |
| C | Один раз допишите `data/company-seeds.json` — дальше снова одна команда. |

Проверка ника: `bash scripts/verify-telegram.sh username`

## Что делает CLI (коротко)

Порядок в `discover.py` (ранжирование: **сначала рекрутер, иначе сотрудник**, каналы — в последнюю очередь):

1. **`network-contacts.json`** (Нетворк + ProductCamp, строгий матч компании)  
2. **`company-seeds.json`** (проверенные рекрутеры)  
3. **`--url`** (сохранённый HTML поста/вакансии)  
4. **HR-каналы** (`hrhubvacancy`, `work4writers`, …) и DDG → посты `t.me/s/`  
5. DDG: recruiter / резюме / hirehi / linkedin  
6. `verify-telegram.sh` + тип контакта в stdout

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