# Новый сценарий в алгоритм

Когда ручной OSINT нашёл паттерн (пример: KION → HR[хаб], Flowwow → вакансия в `work4writers`):

1. Добавить **логику** в `scripts/discover.py` (не @ в JSON).
2. Имя в `reason`: `сценарий: …`
3. Проверка: `bash scripts/recruiter-osint.sh "Компания" --refresh`
4. Строку в `docs/WORKFLOW-RU.md` (список сценариев).

Не добавлять компании в `company-seeds.json` без явной необходимости.

**Аэрофлот:** официальные `@aeroflot_*` — не рекрутеры; IT — `TME_HR_PROFILE_PROBE` + `ovchinnikovoleg_hr` (АФЛТ-Системc), проверка `t.me`.