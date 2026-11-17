# Только терминал

```bash
bash scripts/recruiter-osint.sh "Компания"
```

Никакого чата. Один вызов → 3 строки (@, имя, роль) или «не найден».

Уже писали первому найденному → следующий кандидат:

```bash
bash scripts/recruiter-osint.sh "Домклик" --refresh --skip @ник
```

Список запасных: `--json` → поле `alternates`.

## Сценарии в `discover.py` (порядок)

1. Таблицы `network-contacts.json`
2. `company-seeds.json` (опционально, **ваши** записи)
3. `--url` (сохранённый HTML)
4. HR-ленты TG: `hrhubvacancy`, `hrhubvacancy300`, `hrhubjunior`, `work4writers`
5. DDG: `{компания} recruiter telegram` (+ резюме / присылайте резюме)
6. DDG → скачать посты `t.me/s/…` рядом с компанией
7. HireHi + linkedin + t.me (сниппеты)
8. Ранжирование по `t.me` (Recruiter + компания; не `*_corp`)

## Если сценарий не нашёл контакт

- HireHi в браузере → `--url file:///…` с поста/вакансии
- Или дописать шаг в `discover.py` (см. `docs/ADDING-SCENARIOS.md`)

`company-seeds.json` — не для автозаливки, только то, что вы сами проверили.